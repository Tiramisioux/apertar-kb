<!-- Dual sensor, claim check (2026-11-03/04): seven read-only agents re-read the code behind the load-bearing claims of r1-r5 and tried to refute each. Refs: Core 31d5418, UI c153c33, libcamera 6b0b49f3 (Pi base 7e9fef0b), driver cd548ef (Pi) and e5b74d3, Cinemate d6cc93e / cinepi-raw 63a08d5 / handbook c99ff77, KB working tree. No Pi access, no kernel source on the Mac: kernel behaviour is flagged where used. Frozen: corrections go in design-dual-sensor.md. -->

# Dual sensor: claim check of the reader reports r1-r5

82 claims: 56 CONFIRMED, 24 PARTLY (true with a correction), 1 REFUTED, 1 UNVERIFIED; plus 50 new findings. Verdict words are the checkers'; "CONFIRMED" means read in code at the ref, not tried on the Pi.

| Batch | Claims | CONFIRMED | PARTLY | REFUTED | UNVERIFIED | New findings |
| --- | --- | --- | --- | --- | --- | --- |
| libcamera with two cameras in two processes (r4 Q1-Q3) | 6 | 4 | 2 | 0 | 0 | 8 |
| The imx585 driver with two sensors (r4 Q4) | 11 | 4 | 5 | 1 | 1 | 4 |
| Core as one of two processes (r2 Q1, Q2) | 11 | 8 | 3 | 0 | 0 | 7 |
| Core record start, settings protocol, phase lock (r2 Q3-Q5, Q8) | 9 | 3 | 6 | 0 | 0 | 7 |
| Touch UI, HDMI window, WebUI (r3) | 12 | 7 | 5 | 0 | 0 | 7 |
| How Cinemate does dual (r1) | 12 | 11 | 1 | 0 | 0 | 12 |
| Where the reports disagree, and stale KB pages | 21 | 19 | 2 | 0 | 0 | 5 |

## libcamera with two cameras in two processes (r4 Q1-Q3)

### L1 · PARTLY · r4 Q1

- **Claim.** PiSP match() pairs the cameras of one rp1-cfe with one pispbe per call. pipelineFactoryMatch keeps making handlers until match() fails, so each CFE gets its own handler and its own (CFE, BE). acquire lockf()s only that handler's devices, so two processes can hold cam0 (CFE0+BE0) and cam1 (CFE1+BE1) at once.
- **Evidence.** camera_manager.cpp:159-162@6b0b49f3 "if (!pipe->match(enumerator_.get())) break;". pisp.cpp:1163-1236@6b0b49f3: each pass acquires a CFE (:1168) and a BE (:1184) and returns only on "if (numCameras) return true;" (:1234-1235). pipeline_handler.cpp:146, 173-178: every entry in mediaDevices_ is locked. media_device.cpp:149 "lockf(fd_.get(), F_TLOCK, 0)". camera.cpp:1019-1023: a failed lock returns -EBUSY. The pairing comes from search() taking the first free match in devices_ (device_enumerator.cpp:350-358), and devices_ fills in udev scan order as each media device's last node arrives (device_enumerator_udev.cpp:165-199, 343-347). The Pi's base has the same match() at pisp.cpp:969-1055@7e9fef0b.
- **Correction.** This holds when every CFE yields a camera. The exception: if a pass registers no camera, its CFE and BE stay acquired and the next pair goes into the same handler, so that camera's acquire locks all four devices. The pairing is the k-th free CFE with the k-th free BE in the enumerator's list. Port and camera id play no part. Both processes on one boot see the same list, so they get the same pairs (r5: cam0 got media0 + media2; pisp.cpp:1471 logs each pair). If the device set changed between the two starts and B's cam1 lands on the BE that A holds, B's Camera::acquire() returns -EBUSY with "Pipeline handler in use by another process". A is not affected.
- **For the port.** Two Cores can each own one pipeline. Select the camera by id (i2c@88000 / i2c@70000) and check that both journals show the same "Registered camera ... ISP device" lines. The secondary must register cam0 without errors (new finding 1).

### L2 · CONFIRMED · r4 Q1

- **Claim.** Every CameraManager::start() builds a CameraSensor for every sensor any handler matches, acquired or not, and its init writes V4L2 controls on the sensor subdev.
- **Evidence.** Sensors are built at match time, before any acquire: pisp.cpp:1198-1226, pipeline_base.cpp:851@6b0b49f3. Writes in camera_sensor_legacy.cpp@6b0b49f3: (1) HFLIP=0 and VFLIP=0 in one call, result ignored (:213-218). (2) "ctrl.set(V4L2_CID_HBLANK, static_cast<int32_t>(hblankInfo->minimum));", where an error fails init (:288-296). (3) TEST_PATTERN = Off (index 0) (:298, :1015-1036), written only because the fork's imx585 entry lists test patterns (camera_sensor_properties.cpp:384-388). There are no other writes: the driver checks and property reads only read, platformRegister only opens nodes (pisp.cpp:1417-1418, 1444), and links and formats are set at configure (pisp.cpp:2686-2705). The IMX585 gets the Legacy class. Raw (priority 0) is tried first but needs 1-2 internal sink pads (camera_sensor_raw.cpp:212-217), and the driver has one source pad (imx585.c:4732-4734@cd548ef), so Legacy (priority -100, :1048) takes it. What reaches a sensor another process is streaming: HBLANK does. It is not grabbed, and the driver writes HMAX whenever the sensor is powered (imx585.c:3473-3475, 3525-3543@cd548ef). Its minimum is 0 (:3392), so HMAX drops to min_hmax. The flips do not: they are grabbed at stream-on (:4207-4208), so the write gets EBUSY, which is logged and ignored. TEST_PATTERN=0 only writes the TPG-off registers (:2873-2878).
- **For the port.** Any manager start in either Core, or any rpicam tool, resets the other sensor's line length to the minimum. Either block restarts while the other camera records, or patch init to skip these writes when HFLIP reports GRABBED (idea, untested). Core sets no flips (grep: none), so the flip clear does not matter for Apertar.

### L3 · PARTLY · r4 Q1

- **Claim.** The RPi IPA re-sends HBLANK (and VBLANK) in every frame's sensor control list, and DelayedControls writes a pushed control even when its value did not change, so a foreign HBLANK write on a streaming sensor is overwritten within the HBLANK delay.
- **Evidence.** ipa_base.cpp:1847, 1874-1875@6b0b49f3: VBLANK is always sent, and HBLANK when the mode's min and max line length differ (true for imx585). The list is pushed from processStats on every frame with agc.status (:557-563), skipped frames included because their metadata is merged from the last run (:487-490). delayed_controls.h:51 "Info(const ControlValue &v, bool updated_ = true)". delayed_controls.cpp:253-288 writes every updated entry, and pipeline_base.cpp:1431-1437 runs that at every frame start. The delays come from sensorDelays() (pipeline_base.cpp:884-891), set for imx585 in camera_sensor_properties.cpp:389-394: exposure 2, gain 2, vblank 2, hblank 2. cam_helper_imx585.cpp:21-40 has no delay code.
- **Correction.** A restores its value at its next frame start, not "within the HBLANK delay". The delay (2 frames, from the sensor database, not the helper) only decides which frame shows the error. Predicted: 1 frame at HMAX = min_hmax, not 1-3. It is 0 if A already runs at HBLANK 0, and 2 only if A's next push arrives after the next frame start. Whether the kernel skips unchanged values is kernel behavior and was not checked here.
- **For the port.** Each foreign manager start gives the other camera one shorter, darker frame (by min_hmax/HMAX) and a lasting phase step of VMAX x dHMAX / 74.25 MHz. FramePhaseLock removes that step at 150 us per frame at most (FramePhaseLock.hpp:36-39). Computed for 4K at 891 MHz: 0 ms at 25 fps untrimmed, 5.0 ms at 24 fps, up to about 7.5 ms under phase-lock trims.

### L4 · CONFIRMED · r4 Q2

- **Claim.** The tuning file is chosen per CameraManager start from env LIBCAMERA_RPI_TUNING_FILE (for every camera that manager registers), else <model>.json, so two processes can run two tuning files.
- **Evidence.** pipeline_base.cpp:875, 1216-1219@6b0b49f3: each registered camera loads its IPA with model (+"_mono") + ".json". ipa_proxy.cpp:41-48 builds "LIBCAMERA_" + RPI + "_TUNING_FILE" from the module name rpi/pisp and reads it with secure_getenv at that call. Otherwise it searches ipa.config_paths (:54-61; env LIBCAMERA_IPA_CONFIG_PATH, global_configuration.cpp:101-102), then the install dirs (:84-89).
- **For the port.** Two Cores can run two tuning files, set per unit through the env or LIBCAMERA_IPA_CONFIG_PATH. Each process also loads its own file for the other camera, which it never uses. The fork's HDR16 SW stats ignore both settings and always read /usr/local/share/libcamera/ipa/rpi/pisp/<model>.json (tuning_helpers.cpp:18-21). Core rewrites the env on each start (CameraController.cpp:1424-1430, 7328@31d5418).

### L5 · CONFIRMED · r4 Q3

- **Claim.** rpi.sync uses UDP multicast 239.255.255.250:10000 with no IP_MULTICAST_IF/LOOP/TTL set. Only the client adjusts, by a one-frame frameDurationOffset when |offset| >= min_adjustment (50 us). Without the tuning block, SyncMode is accepted and ignored.
- **Evidence.** sync.cpp@6b0b49f3: the defaults are 239.255.255.250 and 10000 (:49-50, 56-57). Socket setup sets only O_NONBLOCK, SO_REUSEADDR, IP_ADD_MEMBERSHIP(INADDR_ANY) and bind, all on the client (:81-104), and the server socket is bare. The correction exists only in the client branch and is zeroed below min_adjustment (:262-264, 274). It is signed and applied for one frame (ipa_base.cpp:549, 560, 1836-1837). SyncMode does nothing without the algorithm (ipa_base.cpp:1501-1516). A failed sendto only logs "Send error! " (:225-226), and the server still reports ready at ready_frame (:229-233). The client is ready only after clientSeenPacket_ (:278-281). Without a packet it reports SyncReady false every frame and no SyncTimer. A failed IP_ADD_MEMBERSHIP closes the socket, retries every frame and gives no sync metadata at all (:95-110, 145-149).
- **For the port.** Nothing to port for the phase-lock plan. If rpi.sync were ever used, it would need a route for 239.255.255.250 (r5: lo has no MULTICAST, and only eth0 has a default route). The server reports ready even when nothing was sent. SyncMode is advertised even without the tuning block (ipa_base.cpp:88-92), so Core cannot tell that it does nothing.

### L6 · CONFIRMED · r4 Q1, Q2

- **Claim.** One CameraManager per process (camera_manager.cpp:309-311), so two cameras in one Core would need a shared manager; reconfigure in Core restarts the manager.
- **Evidence.** camera_manager.cpp:309-311@6b0b49f3 logs "Multiple CameraManager objects are not allowed" at Fatal, which aborts (log.cpp:873-876). CameraController.cpp@31d5418: reconfigure is "stop(); ... return start(settings, error);" (:7452-7458). stop() destroys the manager (:7445-7448). start() creates a new one (:7247) and may restart it up to 3 times while resolving the tuning (:7246-7336). A process's first start also runs the probe, with two temporary managers (:7048-7060, once per process :7151-7158).
- **For the port.** One Core with both cameras would stop both cameras on every reconfigure. Two Cores avoid that, but every manager start in either one re-runs sensor init on the other camera (L2, L3): up to 5 at a Core's first start and 1-3 per reconfigure.

### New findings

1. **If the first CFE's camera fails to register in a process, the handler for the next camera holds both pipelines.** Evidence: pisp.cpp:1163-1236@6b0b49f3: a pass that registers no camera keeps its CFE and BE in mediaDevices_ (pipeline_handler.cpp:146), and the loop acquires the next pair into the same handler. acquire() then locks all four (:173-178). Any failure counts: a sensor-init write error (camera_sensor_legacy.cpp:293-295), an IPA load error or a pipeline-config error. For the port: The secondary registers cam0 first, if csi@110000 enumerates first (likely, not checked). If cam0 fails to register in the secondary, its cam1 acquire also tries to lock CFE0+BE0 and fails with EBUSY against the primary. Keep cam0 registerable in both processes, and never let the driver grab HBLANK or TEST_PATTERN.
2. **At 4K 25 fps on 891 MHz the HBLANK reset does nothing, so r4's M2 test at 25 fps would wrongly read 'harmless'.** Evidence: imx585.c:288-294@cd548ef: the 4K 12-bit min HMAX at 891 MHz is 550, and the Clear HDR floor is also 550 (:121, 3313-3314). cam_helper_imx585.cpp:160-208@6b0b49f3 snaps 25 fps to 2,970,000 ticks = 550 x 5400, so HBLANK is 0. Replaying the helper's search: 41,666 us (24 fps) gives HMAX 625, 40,001 us gives 581, 39,950 us gives 676. For the port: Run M2 at 24 fps or with fps_phase_lock on, and read horizontal_blanking on the streaming sensor first. The hazard is real exactly when the plan turns the phase lock on.
3. **Phase-lock trims make the IMX585 helper re-pick HMAX, up to 1.5x the minimum, so two locked cameras run different line lengths.** Evidence: FramePhaseLock.hpp:127-138@31d5418 pushes whole-us FrameDurationLimits {d, d}. cam_helper_imx585.cpp:129-132, 185-208@6b0b49f3 runs the lattice search whenever min == max and prefers an exact point (cap at :143-144). Replayed: 39,995-40,150 us give HMAX 551-581, and 39,950 us gives 676. For the port: While trimmed, the two cameras have different rolling-shutter skew and line time. For dual, consider trimming VMAX only with a fixed HMAX, or capping the HMAX stretch.
4. **Core writes WDR on the first subdev named imx585 in readdir order, on every start, even in SDR. On a streaming sensor that write gets EBUSY, and the start aborts.** Evidence: CameraController.cpp:6875-6892@31d5418 picks the first /sys/class/video4linux entry naming imx585. setSensorWideDynamicRange always does S_CTRL, retries 4 x 50 ms (:6925-6952), and start() returns false on failure (:7239-7240). The HDR ext controls go to the same subdev (:6960+). The driver grabs hdr_mode while streaming (imx585.c:4207-4209@cd548ef). The probe and start() also take the first non-USB camera (:7062-7068, :7262-7265). EBUSY for an unchanged value on a grabbed control is kernel behavior, not checked here. For the port: Whichever Core starts second fails while the other streams, if the other's sensor is listed first. If it is not, it still takes cam0. Pass a camera id, and resolve the subdev from it before any WDR or HDR write.
5. **Core's derived log-preview tuning file sits at one shared path per profile.** Evidence: ProresIspProfile.cpp:228-234@31d5418: $HOME/.cache/apertar-prores/<profile>.json, written with atomicWrite. libcamera reads it at the next manager start through setenv (CameraController.cpp:7328). For the port: Two Cores with different source tunings and the same profile overwrite each other's file, and the last writer wins. Put the camera id or an instance name in the path.
6. **libcamera user space shares nothing between processes. What is shared is kernel-side: the sensor subdev controls, the driver's mode table, the one BE engine, and RAM for buffers.** Evidence: The FE/BE config objects are private memfds (pisp.cpp:1215-1218, memfd.cpp:86@6b0b49f3), and the PiSP handler has no dma-heap allocator (only vc4.cpp:91). Core allocates raw and ProRes buffers from /dev/dma_heap/vidbuf_cached, then linux,cma (CameraController.cpp:8682@31d5418). The KB (clearhdr-design.md:87, 101) records that vidbuf_cached maps to the system heap here and that CMA is 64 MB. The driver's mode table is file-scope and rewritten on every mode select (imx585.c:1064, 3316-3317, 3375@cd548ef). For the port: Budget two buffer pools against the 4 GB of RAM, not against CMA. Use the same link frequency and lane count on both overlays, and avoid mode selects in different Clear HDR states at the same moment.
7. **Cinemate's libcamera makes the same sensor-init writes, so its dual rigs carry the same HBLANK reset, and there is no filter to borrow.** Evidence: camera_sensor_legacy.cpp:214, 291, 297@bfe0b76a0 (Cinemate libcamera). Its imx585 entry has testPatternModes = {} (camera_sensor_properties.cpp:297). For the port: Any fix, such as skipping the init writes when HFLIP reports GRABBED, would have to be an Apertar fork patch.
8. **The cross-process lock is a POSIX lockf on the media node. A process loses it if it closes any fd on that node. Core never opens /dev/media*.** Evidence: media_device.cpp:144-153@6b0b49f3 "lockf(fd_.get(), F_TLOCK, 0)". git grep for '/dev/media' and 'MEDIA_IOC' in Core src@31d5418: no hits. The drop-on-close rule is POSIX behavior, not checked here. For the port: Do not run media-ctl or /dev/mediaN probes inside a Core that holds a camera. Run them as separate processes.

Checker's note: Nothing could be checked on the kernel side (no kernel tree on this Mac). That covers: EBUSY for a grabbed control even when the value is unchanged, s_ctrl being skipped for unchanged values, the GRABBED flag showing in queryctrl, the default multicast LOOP and TTL, and the error codes. libudev's scan order is also not checked.  The HMAX figures are replays of cam_helper_imx585.cpp and the driver tables in Python. They are not measurements, and they assume 4 lanes (the overlay default).  Line numbers on the Pi's base 7e9fef0b differ only in pisp.cpp: match() is at 969 and the "Registered camera" log at 1287. The fork changes only pisp.cpp and raw_stats.  r4 cites driver lines at e5b74d3. On the Pi's cd548ef, the grabs are at 4207-4209 and the pads at 4732-4734.  No files were written, no ssh was used, and no checkout was touched.

## The imx585 driver with two sensors (r4 Q4)

### D1a · PARTLY · r4 Q4 (multi-instance safety)

- **Claim.** supported_modes[] is a non-const file-scope array shared by every imx585 instance, rewritten by imx585_update_hmax() from the caller's link frequency, lanes and Clear HDR state on every set_fmt and WDR change; the HBLANK-to-HMAX conversion reads it on every HBLANK write (libcamera triggers it every frame).
- **Evidence.** imx585.c:1064@cd548ef "static struct imx585_mode supported_modes[] = {"; :3316 "supported_modes[i].min_hmax = h;"; :3531 "num = (u64)mode->min_hmax * (width + hblank);". The writer (:3271-3352) uses link_freq_idx, lane_count and clear_hdr (:3273-3274, 3281). Its only callers are :3459 (WDR, under the value-change test at :3428) and :4018-4019 (ACTIVE format only). e5b74d3: :794, :1485-1506, :1593, :2116-2117, :1665.
- **Correction.** It runs only on an ACTIVE set_fmt (init_state's TRY call at :4339-4349 never rewrites) and only when WDR actually changes. The HBLANK conversion runs whenever s_ctrl runs: at every stream start (__v4l2_ctrl_handler_setup, :4186) and on an HBLANK value change. libcamera does push HBLANK every frame (ipa_base.cpp:558-562 and 1874-1875@7e9fef0b), but the V4L2 core skips unchanged values (kernel code, not on this Mac). Line fix: the function spans D2:3271-3352. cd548ef also rewrites a second table, supported_10bit_modes[] (:2093). The driver's 'process-wide' really means module-wide.
- **For the port.** Two Core processes do not isolate this table: it is kernel-module state that both sensors share.

### D1b · PARTLY · r4 Q4 + Feasibility 5

- **Claim.** Both sensors must use the same link-frequency, lanes and Clear HDR state, or one sensor's line length is computed from the other's table.
- **Evidence.** imx585.c:3281-3282@cd548ef "u32 h = supported_modes[i].hmax_table[imx585->link_freq_idx] * lane_scale / supported_modes[i].hmax_div;"; :3313-3314 "h = max_t(u32, h, IMX585_HMAX_MIN_CLEARHDR * lane_scale);". :121 sets the floor to 550 and :294 gives 550 at 891 MHz. min_vmax is read only in the caller's own set_framing_limits (:3377, 3396-3399).
- **Correction.** Link frequency and lane count must match: they set min_hmax, and the other sensor's HBLANK path reads it. Clear HDR may differ at 891 MHz or below on cd548ef: the 550 floor equals the table value there and binds only at 1039/1188 MHz. e5b74d3 has no floor at all (:1487-1501). Clear HDR only doubles min_vmax, which the other instance can pick up only in a microsecond race if both configure at the same instant. Modes may differ, because every entry is rewritten from (link, lanes, HDR) plus its own static fields.
- **For the port.** Put both overlays on one link-frequency (891 or 720 MHz, never mixed) and 4 lanes. Different modes and SDR/HDR per sensor are safe at 891 MHz. Relay configures one after the other to rule out the min_vmax race.

### D1c · PARTLY · r4 Q4 (task: find other mutable file-scope state)

- **Claim.** supported_modes[] is the mutable shared state in imx585.c; list every other mutable file-scope variable.
- **Evidence.** imx585.c:1039-1040@cd548ef "static bool clearhdr_windowed_binning;" "module_param(clearhdr_windowed_binning, bool, 0444);"; :2093 "static struct imx585_mode supported_10bit_modes[] = {". Also :4794 imx585_i2c_driver. At e5b74d3 there are only :794 supported_modes[] and :2691 imx585_i2c_driver. Neither ref has function-local statics or non-static globals.
- **Correction.** cd548ef has two more: supported_10bit_modes[], rewritten by the same update_hmax (:3323-3351), and the module param clearhdr_windowed_binning. The param is 0444 and the driver never writes it (read at :3090, :4678), so both sensors get one value. Nothing else is mutable and shared.
- **For the port.** For dual, only the two mode tables matter. The module param is a deliberately module-wide test gate and is off by default.

### D2a · CONFIRMED · r4 Q1/Q4 (EBUSY, D:2288-2291)

- **Claim.** While streaming, HFLIP, VFLIP and the WDR (Clear HDR) control are grabbed (EBUSY); HBLANK, VBLANK and exposure stay writable.
- **Evidence.** imx585.c:4206-4209@cd548ef "/* vflip, hflip and HDR cannot change during streaming */" "__v4l2_ctrl_grab(imx585->vflip, true);" "__v4l2_ctrl_grab(imx585->hdr_mode, true);". They are released at :4235-4237, and the file has no other grab. e5b74d3: :2289-2291 and :2311-2313.
- **Correction.** These also stay writable while streaming: gain, HCG, black level, the HDR threshold/blend/gradient/gain controls, test pattern, and the raw VMAX/HMAX/SHR custom controls (:3571-3586). The raw controls write unrounded and bypass the driver's own vmax/hmax state. GRABBED->EBUSY is kernel core behaviour that is not on this Mac; Core's retry comment (CameraController.cpp:6939@31d5418) matches it.
- **For the port.** Changing flips or Clear HDR needs a stream stop on that sensor. All timing and HDR-tuning controls can be written live, including by a process that opened the wrong subdev.

### D2b · UNVERIFIED · task D2 (timing of live writes)

- **Claim.** An HBLANK or VBLANK write while streaming takes effect at the next frame; which registers, any group hold.
- **Evidence.** imx585.c:3510@cd548ef "imx585->vmax = (mode->height + ctrl->val) & ~1U;"; :3520 "cci_write(imx585->regmap, IMX585_REG_VMAX, imx585->vmax, NULL);". VMAX is 0x3028 (24-bit, :117), HMAX is 0x302C (16-bit, :124, written at :3540), SHR is 0x3050 (:135). Neither ref writes REGHOLD/0x3001. camera_sensor_properties.cpp:389-394@7e9fef0b sets all four delays (exposure, gain, vblank, hblank) to 2.
- **Correction.** The driver writes the register over I2C at once, one write per control, with no group hold. libcamera sends VBLANK in its own ioctl before HBLANK, exposure and gain (priority write: pipeline_base.cpp:885-891, delayed_controls.cpp:254-261@7e9fef0b). The stack assumes 2 frames, not the next frame. The sensor's latch point is not in the code; it needs the datasheet or a test.
- **For the port.** The phase lock must model a 2-frame actuator delay. A VMAX+HMAX pair is not atomic and can split across a frame boundary.

### D2c · PARTLY · task D2 (VBLANK-only actuator, foreign HBLANK)

- **Claim.** A VBLANK-only phase actuator is possible, and a foreign HBLANK write (another process's CameraManager start) lands as a line-length change on a streaming sensor.
- **Evidence.** imx585.c:3506-3523@cd548ef: the VBLANK case writes VMAX only. :3525-3543: HBLANK is not grabbed, and the handler writes HMAX from the shared min_hmax at once. camera_sensor_legacy.cpp:292@7e9fef0b "ctrl.set(V4L2_CID_HBLANK, static_cast<int32_t>(hblankInfo->minimum));" runs for every enumerated sensor; the flip write's error is ignored (:218). Core pins {d,d} (CameraController.cpp:8948@31d5418), which makes the helper re-pick HMAX (cam_helper_imx585.cpp:129-132, 210-217@7e9fef0b).
- **Correction.** On the driver side, yes: VBLANK writes VMAX and touches neither HMAX nor SHR. But today's lock is not VBLANK-only: pinned {d,d} limits make libcamera's helper move HBLANK when it nudges. The minimum is 0 (:3392). With HBLANK already 0, a foreign write is a no-op, because V4L2 skips unchanged values (kernel, not on this Mac). With a stretched HMAX, it drops HMAX to min_hmax at once until the owner's IPA re-pushes it (1+ frames).
- **For the port.** For dual, keep HBLANK at 0: either use non-pinned {d, d+e} limits, where the default helper path is VBLANK-only, or change the helper. Foreign init writes then do nothing, and the shared table is read only at stream start.

### D3 · CONFIRMED · r4 Q4 (sync modes)

- **Claim.** sony,sync-mode defaults to internal-leader; two sensors both in leader mode free-run on their own clocks with no conflict; registers per mode as in r4's table.
- **Evidence.** imx585.c:4649@cd548ef "imx585->sync_mode = SYNC_INT_LEADER;"; only the strings 'internal-follower' and 'external' change it (:4650-4655). Registers at :4089-4108: leader EXTMODE 0x30ce=0x00, XXS_DRV 0x30a6=0x00, XXS_OUTSEL 0x30a4=0x0A; internal-follower 0x01/0x03/0x08; external 0x0F/0x00 with EXTMODE untouched. XMSTA 0x3002 is set to 0 unless external (:4192-4196); common_regs :403 sets it to 0x01 first. Each instance has its own cam clock: cam1_clk by default, cam0_clk with the cam0 param (overlay :60-63, 131-133), INCK_SEL 0x04 for 24 MHz (:332).
- **Correction.** Any other string, typos included, silently means leader. The driver's two comments disagree on what 0x30a6=0x00 means: 'Hi-Z' at :408, 'XHS/XVS out' at :4100. The pin direction is unverified without the datasheet. 'No conflict' holds only while XVS/XHS stay unwired. e5b74d3 has the same registers but ignores write errors (:2184-2195, 2277-2278).
- **For the port.** Leave both sensors at internal-leader for software sync. They run on separate crystals and drift apart, so the phase lock must track all the time. Never wire XVS/XHS between two leaders.

### D3b · PARTLY · r4 Q4 (dmesg labels, D:327-337)

- **Claim.** dmesg prints the menu string by enum index, so internal-follower reads 'External Sync Leader Mode' and external reads 'Follower Mode'.
- **Evidence.** imx585.c:366-370@cd548ef "Internal Sync Leader Mode", "Internal Sync Follower Mode", "External Sync Mode"; printed at :4656. e5b74d3:333-337 has "External Sync Leader Mode" and "Follower Mode".
- **Correction.** The mislabel exists only on e5b74d3. cd548ef, which the Pi runs, prints the correct names. Line fix: the enum is e5b74d3:327-331 and the menu is :333-337.
- **For the port.** On the Pi, the dmesg sync-mode line can be trusted as a check of each sensor's mode.

### D4 · CONFIRMED · r4 Q4 (overlay) + r5

- **Claim.** cam1 is the default port (no port word). The cam0 param retargets i2c, csi, clk, the always-on fragment and vana-supply but not reg_frag, which is harmless because cam0_reg and cam1_reg are one node on this CM5. 891000000 is in the link-frequency table on cd548ef.
- **Evidence.** imx585-overlay.dts@cd548ef: the defaults target &cam1_reg (:37, 44, 69), &i2c_csi_dsi (:51), &cam1_clk (:60, 108) and &csi1 (:87). :129 "cam0 = <&i2c_frag>, \"target:0=\",<&i2c_csi_dsi0>," and :129-135 also retarget csi_frag, clk_frag, clocks, assigned-clocks, reg_alwayson_frag and vana-supply; reg_frag (:36-41) is not listed. imx585.c:282@cd548ef "[IMX585_LINK_FREQ_891MHZ] = 891000000ULL," with HMAX 550 at :294 and :311. r5 confirms one regulator node.
- **Correction.** fragment@102 (&i2c0if) and @104 (&i2c0mux) are not retargeted either. Both instances enable the same nodes, which is idempotent. The overlay is identical on e5b74d3 apart from the new ccmp param (:138). The 300 ms startup delay lands on the one shared regulator, and the driver waits a further 500 ms at power-on (:65, :4269-4271).
- **For the port.** The second sensor needs dtoverlay=imx585,link-frequency=891000000 (cam1 by default) next to the cam0 line. One regulator powers both, so neither sensor can be power-cycled alone.

### D5a · CONFIRMED · task D5 (units and line time)

- **Claim.** VMAX/HMAX units and the line time at 891 MHz for 4K SDR and Clear HDR.
- **Evidence.** imx585.c:221@cd548ef "#define IMX585_PIXEL_RATE               74250000U"; :294 "[IMX585_LINK_FREQ_891MHZ]  = 550,". The Clear HDR floor is 550 (:121), VMAX_DEFAULT is 2250 (:119) and hdr_scale is 2 (:3274). cam_helper_imx585.cpp:100,135@7e9fef0b: period = VMAX*HMAX at 74.25 MHz. README.md:117,121@cd548ef: 60 fps, Clear HDR half.
- **Correction.** One HMAX tick is 13.468 ns; VMAX counts lines. At 891 MHz with 4 lanes, a line is 550/74.25 MHz = 7.407 us for 4K SDR (12- and 10-bit) and for Clear HDR (2 lanes: 1100 ticks = 14.815 us). Minimum frame: SDR VMAX 2250 = 16.667 ms (60 fps); Clear HDR VMAX 4500 = 33.333 ms (30 fps). e5b74d3 gives the same numbers (:211, :284, :111). At 720 MHz HMAX is 660, so a line is 8.889 us.
- **For the port.** At HMAX 550, 25/30/50/60 fps are exact even line counts (5400/4500/2700/2250). 24 fps needs 5625 lines, which is odd, so VBLANK alone cannot hit it. The helper reaches it with HMAX 625 x VMAX 4950 (my arithmetic).

### D5b · REFUTED · task D5 (smallest VBLANK step)

- **Claim.** The smallest frame-period step VBLANK alone can make is one line.
- **Evidence.** imx585.c:3510@cd548ef "imx585->vmax = (mode->height + ctrl->val) & ~1U;"; e5b74d3:1644 is the same. cam_helper_imx585.cpp:101@7e9fef0b "the driver rounding VMAX even".
- **Correction.** The step is two lines, because VMAX is forced even: 2 x 7.407 = 14.815 us at 891 MHz with 4 lanes (17.78 us at 720 MHz). An odd VBLANK request is silently floored by one line, so libcamera can believe a period 7.4 us longer than the real one.
- **For the port.** A VBLANK-only sigma-delta alternates between VMAX values 14.8 us apart and should request even VMAX only. Finer steps need HMAX, through HBLANK and the shared table.

### New findings

1. **The VBLANK handler writes VMAX but never rewrites SHR, and the driver computes SHR as VMAX minus exposure. If the exposure value does not change, V4L2 skips the exposure s_ctrl, so the real integration time moves by the VMAX change. After a large VMAX drop with a very short exposure, SHR can even exceed VMAX. Both refs behave this way.** Evidence: imx585.c:3479@cd548ef "u32 shr = (imx585->vmax - ctrl->val) & ~1U;". The VBLANK case (:3506-3523) only re-ranges exposure and writes VMAX. e5b74d3: :1613, :1640-1658. The skip-on-unchanged rule is kernel behaviour, not on this Mac. For the port: A VBLANK-only phase actuator would change exposure by the size of each nudge (14.8 us per 2-line step). Before relying on it, fix the driver to rewrite SHR in the VBLANK case.
2. **Core's direct WDR and HDR-knob writes open the first imx585 subdev in /sys/class/video4linux order, not the one its camera uses. With two sensors, the secondary's WDR write gets EBUSY if that sensor is streaming, or silently flips the primary's Clear HDR state if it is stopped. The HDR threshold, blend and gain controls are not grabbed, so they land live on the other sensor.** Evidence: CameraController.cpp:6887-6889@31d5418 "if (name.find(\"imx585\") == std::string::npos)" ... "return ::open((\"/dev/\" + node).c_str(), O_RDWR | O_CLOEXEC);". It is used at :6925-6952 and :6960-6993. imx585.c:4207-4209@cd548ef grabs only the flips and WDR. resetStoppedSensorTiming already matches by of_node (:8124-8130). For the port: Before dual, every direct V4L2 write in Core must pick the subdev by of_node (camera id), the way resetStoppedSensorTiming already does.
3. **Core's phase lock pins FrameDurationLimits to {d,d}. With min equal to max, libcamera's IMX585 helper searches the (even VMAX, HMAX) lattice and sets HMAX through HBLANK, so nudges usually move HBLANK. Its nominal-rate snap also maps any request within 1 us of an integer rate's exact period to that period: at 24 fps, both 41666 and 41667 us give exactly 24.000 fps.** Evidence: CameraController.cpp:8948@31d5418 "const int64_t range[2] = { *phaseLockDurationUs_, *phaseLockDurationUs_ };". cam_helper_imx585.cpp:129-132 (pinned path), :160-167 (snap), :185-217 (lattice, HBLANK)@7e9fef0b. For the port: Today every nudge reaches the shared min_hmax (fine while link and lanes match) and leaves HBLANK non-zero, so foreign HBLANK=min writes do land. Near 24 fps the snap absorbs the lock's two nearest integer requests.
4. **The driver does not refuse an ACTIVE set_fmt while streaming. It reruns set_framing_limits, which resets HBLANK to 0 and VBLANK to the mode minimum through s_ctrl and so writes live VMAX/HMAX. libcamera only sets the sensor format in configure() of the camera it owns, never at enumeration.** Evidence: imx585.c:3996-4033@cd548ef has no streaming check; :3392-3399 "__v4l2_ctrl_s_ctrl(imx585->hblank, 0);". pipeline_base.cpp:539@7e9fef0b "ret = data->sensor_->setFormat(sensorFormat," sits inside configure() (:515). For the port: Enumeration by the other process is safe for formats. No tool or process other than the owner may set the format on a sensor's subdev during a take.

Checker's note: I read the driver with git show at cd548ef (what the Pi runs) and e5b74d3. Where a claim depended on them, I also read libcamera at 7e9fef0b (the Pi's base) and Core at 31d5418. There is no kernel source on this Mac. Three kernel behaviours are taken from knowledge and flagged where used: GRABBED returns EBUSY, the V4L2 core skips s_ctrl when a value is unchanged, and modify_range clamps. The sensor's register latch point and the XVS/XHS pin direction need the IMX585 datasheet. Bottom line for the two-Core plan: the shared mode tables are harmless if both overlays use the same link-frequency and lane count. Today's phase lock moves HBLANK through libcamera's helper. A VBLANK-only actuator needs non-pinned limits and a driver fix to rewrite SHR. Core's first-imx585-subdev lookup must be fixed before dual. No files written, no ssh, no web.

## Core as one of two processes (r2 Q1, Q2)

### C1 · CONFIRMED · r2 Q1 Control socket; Must be per-instance 1

- **Claim.** ControlServer unlinks then binds the socket path (ControlServer.cpp:124) and unlinks it in stop() (:170); a second Core on the same path steals it and orphans the first.
- **Evidence.** src/ipc/ControlServer.cpp:124@31d5418 `::unlink(socketPath_.c_str());` then :126 `if (::bind(listenFd_, ...`; stop() :169-170 `if (!socketPath_.empty()) { ::unlink(socketPath_.c_str());` (only when running_, :148). Default path App.hpp:39.
- **For the port.** Secondary gets its own --socket. The steal only starts once the secondary opens a different camera: App::start opens the camera (App:8034) before it binds the socket (App:8056).

### C2 · CONFIRMED · r2 Q1 Web port; corrections bullet 2; Must be per-instance 2

- **Claim.** A web-port bind failure aborts start() with exit 1 after the camera was opened and the socket bound; --web-port exists in main.cpp; the start script forwards only --socket and --media.
- **Evidence.** src/ApertarCoreApp.cpp:8067-8077@31d5418 on webServer_.start failure `controlServer_.stop();` then camera_.stop(), return false; main.cpp:108-111 returns 1; main.cpp:35 `--web-port PORT     Web control port, 0 disables it (default: 8000)`; scripts/start-apertar-core.sh:44 `--socket "$SOCKET_PATH" --media "$MEDIA_ROOT"`. Port 0 skips the MJPEG thread (App:8024) and the web server (App:8067).
- **For the port.** Secondary: --web-port 8001 or 0 (0 = no /preview.mjpeg and no /api for cam1), so its unit runs the binary directly or the script gets a web-port env. A port clash gives a Restart=on-failure loop that re-opens the camera, re-runs the probe and rewrites settings every time.

### C3 · CONFIRMED · r2 Q1 Camera pick; Q2

- **Claim.** The first non-/usb camera is chosen at session start (CC:7262-7265) and in the probe (CC:7063-7066); no option selects a camera.
- **Evidence.** CC:7263@31d5418 `return camera && camera->id().find("/usb") == std::string::npos;`; CC:7265 `camera_ = selected != cameras.end() ? *selected : cameras.front();`; probe CC:7063-7067 same test, fallback `cameras.empty() ? nullptr : cameras.front();`. These are the only cameras() calls; main.cpp:46-87 has no camera option.
- **For the port.** Today a second Core takes cam0 and exits 1 (WDR write CC:7239 or acquire CC:7346). Add a camera key used at both sites in both Cores, with no front() fallback: with two sensors even the primary's 'first' camera follows libcamera's enumeration order, not the port.

### C4 · CONFIRMED · r2 Q1 IMX585 subdev, probe; Q2

- **Claim.** openImx585Subdev picks the first subdev named imx585 (CC:6875), used by WDR (CC:6925), ext control writes (CC:6960) and the probe (CC:7039); only resetStoppedSensorTiming (CC:8114-8150) matches the subdev by of_node to the camera id.
- **Evidence.** CC:6878-6889@31d5418 walks /sys/class/video4linux in directory order: `if (name.find("imx585") == std::string::npos)` else `return ::open(("/dev/" + node).c_str(), O_RDWR | O_CLOEXEC);`. Callers CC:6927, 6962, 7043/7052, 6896. CC:8125 `ofNode.string() == "/sys/firmware/devicetree" + cameraId`.
- **Correction.** Line fix only: resetStoppedSensorTiming is CC:8114-8154; the of_node match is CC:8124-8130.
- **For the port.** Blocker for two IMX585 (see the WDR-grab finding): add the of_node match at CC:6875 and use it for WDR, the HDR knobs and the probe.

### C5 · PARTLY · r2 Q1 camera_settings.conf, UI.conf and HardwareConfigStore rows; Must be per-instance 4

- **Claim.** XDG_CONFIG_HOME decides where camera_settings.conf, mode_ladder.conf, UI.conf and the HardwareConfigStore files live (CC:414-425, App:517-524, HardwareConfigStore.cpp:118-131).
- **Evidence.** CC:418@31d5418 `/ "apertar-core" / "camera_settings.conf";` (mode ladder CC:401-412, UI.conf App:517-524 under CinePi/); HardwareConfigStore.cpp:122 `return "/home/pi/apertar-hardware.conf";` after the APERTAR_HARDWARE_CONFIG test; :357 `atomicWrite(file_.string() + ".bak", current)`.
- **Correction.** True for camera_settings.conf, mode_ladder.conf (CC:401-412, not 414-425), UI.conf and the store's notes (hardware-state.conf, hardware-last-written.conf, hardware-history/; HardwareConfigStore.cpp:125-132). Not for the hardware file and its .bak (APERTAR_HARDWARE_CONFIG or /home/pi; :118-123, :357), presets (XDG_DATA_HOME or HOME, App:6085-6129) or the ProRes cache (HOME, ProresIspProfile.cpp:228-230).
- **For the port.** Secondary needs its own XDG_CONFIG_HOME and APERTAR_HARDWARE_CONFIG. It writes camera_settings.conf already at camera start (CC:10442), so a shared dir is overwritten on every secondary start.

### C6 · CONFIRMED · r2 Q1 hardware conf readers; Q6; Must be per-instance 5

- **Claim.** APERTAR_HARDWARE_CONFIG is read first; PCF8574, GPIO, NeoRotary4 and Grove fall through to the next candidate when their section is absent; trigger and tally stop at the first existing file; a secondary needs its own file with explicit enabled=false, or a role flag.
- **Evidence.** Pcf8574Input.cpp:65-70@31d5418 env first, then /home/pi, /boot/firmware, /boot; :256 `config.enabled = true;` on the section header; :307 `if (config.configured)` else next file (same in GpioInput.cpp:295-298/456, NeoRotary4Input.cpp:293-296/354, GroveAnalogInput.cpp:262-265/334). TriggerOutput.cpp:349 and RecordingIndicatorOutput.cpp:388 `return config;` after the first opened file.
- **For the port.** Secondary file: [pcf8574], [neorotary4], [grove_analog] with enabled=false (the header turns them on); a bare [gpio_buttons] is enough; trigger and tally default off. [ina219] and [imu] also read only the first file but default on (App:4898, Mpu6050RecordingSession.hpp:36): add enabled=false.

### C7 · PARTLY · r2 Q1 Storage pre-roll and Media watcher/trim rows; Q6

- **Claim.** APERTAR_STORAGE_PREROLL=0 and APERTAR_MEDIA_TRIM=0 exist and switch off the pre-roll and the trim thread; the pre-roll thread starts regardless (App:8008-8011).
- **Evidence.** App:6380@31d5418 `return !(env && env[0] == '0');` (APERTAR_MEDIA_TRIM); App:11113 `if (!manual && !storagepreroll::automaticEnabled(std::getenv("APERTAR_STORAGE_PREROLL"), conf)) {`; App:14160 `requestStoragePreroll(storagepreroll::Trigger::Manual, seconds);`. App:8004-8011 start both threads unconditionally.
- **Correction.** Both variables exist. PREROLL=0 stops only the automatic runs (start, insert, format); the storage_preroll command still runs one (App:14148-14161). TRIM=0 stops every trim request and wait (App:11402, 11422, 11583), but the trim thread is also started regardless (App:8004-8007) and just idles.
- **For the port.** Set both on the secondary and never relay storage_preroll. The primary's own trim and pre-roll gates see only its own takes (see new finding).

### C8 · PARTLY · r2 Q1 Power button, standby row; Q6 Disabling inputs

- **Claim.** The power button (StandbyPowerButtonInput), idle standby and the controls worker cannot be switched off by config.
- **Evidence.** App:8093@31d5418 `standbyPowerButton_.start();` (only under !simulateCamera); App:8124-8125 controls thread always started; App:8269 `const int timeout = readSharedUiSettings().standbyTimeoutSeconds;` then :8275 `timeout > 0`; App:1910 `int standbyTimeoutSeconds = 0;`.
- **Correction.** Power button and controls worker: right (only --simulate, which also skips the camera; the worker only watches its own hardware file). Idle standby: wrong; it is off when the instance's own UI.conf has standbyTimeoutSeconds=0, which is also the default with no UI.conf. Also not switchable: the low-power restore at every start and stop (App:7985-7997, 8163-8172).
- **For the port.** Own UI.conf keeps the secondary's idle timer off. A role flag is still needed: the power button is read without a grab (StandbyPowerButtonInput.cpp:44-45), so a double press puts both Cores in standby (App:10249-10258).

### C9 · CONFIRMED · r2 Q1 Audio

- **Claim.** Audio capture opens hw: exclusively (TimestampedAudioCapture.cpp:126,192); audio can be switched off per take by an option.
- **Evidence.** App:2970@31d5418 `return "plughw:" + deviceId.substr(3);` (device ids); TimestampedAudioCapture.cpp:72 `if (device.rfind("plughw:", 0) == 0) device.erase(0, 4);` so :126 and :192 snd_pcm_open hw:X,Y (EBUSY expected at :130); App:14231 `if (const auto audioEnabled = command.string("audio_enabled")) {`.
- **For the port.** Relay record_start with audio_enabled=false and sound_only=false (sound_only defaults to UI.conf soundRecorderEnabled, App:14225). A busy PCM fails the whole take, not only the audio (CC:7578-7582). With its own UI.conf, audio is off by default (App:1892).

### C10 · CONFIRMED · r2 Q1 Clip name; Q7

- **Claim.** {cam} is hard-wired to cam0 (CC:1148); the template {format}_{date}_cam1_{clip} is valid today (ClipName.hpp:211-283); the next clip number is the lowest free number by exists(), not exclusive.
- **Evidence.** CC:1148@31d5418 `v.cam = "cam0";   // one camera per Apertar`; ClipName.hpp:255-256 keeps any [A-Za-z0-9._-] literal, so _cam1_ parses; ClipName.hpp:291 `if (!exists(expand(parsed, values, clip)))`; CC:7544 `std::filesystem::create_directories(clipFolder);` (not exclusive).
- **For the port.** A cam1 literal works now if the template is stored per instance. Numbers are per template, so the C#### drift after one-sided refusals or deletes (pass the number from the primary). A relayed preset overwrites the template (App:13885-13889).

### C11 · CONFIRMED · r2 Q2 get_state today

- **Claim.** get_state carries no camera id or port.
- **Evidence.** App:12498-12531@31d5418 body: state, recording, media, `<< ",\"sensor\":\"" << escapeJson(camera_.sensorName())`, binning, sensor_mono, settingsBody. git grep finds no camera_id or port field; the id is printed only in the acquire error (CC:7347).
- **For the port.** Add camera_id (camera->id()) and camera_port to get_state and the settings event, so the relay and the UI can check which camera each socket drives.

### New findings

1. **With two IMX585, the Core whose sensor is not first in /sys/class/video4linux order fails every start and reconfigure while the other camera streams. The WDR write runs at each session start (CC:7239), not only in the probe, and the driver grabs WDR while streaming.** Evidence: CC:7239@31d5418 `if (!setSensorWideDynamicRange(settings.clearHdr, error))` (4 tries, then error, CC:6938-6950); CC:6939 `// EBUSY while the previous stream is still winding down.`; imx585.c:4209@cd548ef `__v4l2_ctrl_grab(imx585->hdr_mode, true);`, released only at stream stop (:4237). The HDR knobs (CC:6996-7003) are not grabbed and land on the wrong sensor. For the port: The of_node match is needed before a second Core can run. APERTAR_SENSOR_PROBE=0 (CC:7159) skips only the probe's two WDR toggles. Even one Core with two sensors attached can send Clear HDR to the wrong sensor.
2. **Standby is machine-wide, but each Core checks only its own camera. An idle Core runs the low-power helper while the other camera records if it gets a power-button double press, reaches its own idle timeout or receives a relayed enter_standby.** Evidence: CC:10476@31d5418 `if (recording_ || timelapseActive() || state_ != CameraState::Ready) {`; App:12271 `const auto result = standbyLowPower("all");`; Apertar-UI src/StandbyLowPower.cpp:50,63@c153c33 set every CPU policy to powersave and NVMe power/control to auto. Only the Core's own commands (App:12229-12235) and own takes (App:8270-8273) reset its idle clock. Every Core start and stop also restores (App:7985-7991, 8163-8167). For the port: Only the primary may enter standby, and only when both cameras are idle. The secondary needs a role flag (no power button, no restore) and standbyTimeoutSeconds=0.
3. **Every take stop runs syncfs on the recording volume. That flushes the whole exFAT filesystem, so one Core's stop waits for, and competes with, the other Core's frames that are still being written.** Evidence: CC:4744@31d5418 `const int result = ::syncfs(fd);` in syncToMedium, called after each stop at CC:7714-7715; CC:4316-4317 comment: `here waited for every page in flight and stalled the writers: 782 queue`. For the port: Stop both takes together, or have the secondary fsync its own files instead of calling syncfs; measure the stall with two writers [P].
4. **Every CameraManager start (each Core start, standby wake and reconfigure) runs libcamera's sensor init on every sensor it registers, including the one streaming in the other process: flips set to 0, HBLANK set to its minimum, test pattern off.** Evidence: libcamera src/libcamera/sensor/camera_sensor_legacy.cpp:292-293@6b0b49f3 `ctrl.set(V4L2_CID_HBLANK, static_cast<int32_t>(hblankInfo->minimum));` / `ret = subdev_->setControls(&ctrl);` (flips :213-218, result ignored), reached from registerCamera (pipeline_base.cpp:851). imx585.c:3540@cd548ef writes HMAX at once when powered; its stream grab (:4207-4209) does not cover HBLANK. Core recreates its manager (CC:7445-7448, then CC:7247). For the port: Normally does nothing, because HBLANK is already at its minimum and V4L2 skips unchanged values [P]. If one camera is reconfigured while the other runs a very long exposure (the IPA widens HBLANK, ipa_base.cpp:1867-1875), the other camera's line length changes [P].
5. **Both Cores share one preset store, and presets carry the clip-name template and the phase-lock switch.** Evidence: App:6088-6097@31d5418 preset folders: XDG_DATA_HOME/Apertar-UI/presets, then HOME/.local/share/Apertar-UI/presets and HOME/.config/CinePi/UI/presets (never XDG_CONFIG_HOME); App:13885 `if (const auto value = command.string("cameraClipNameTemplate")) {`; App:13889 `presetSettings.clipNameTemplate = parsed.normalized;` (fpsPhaseLock at App:13891). For the port: When relaying a preset, drop cameraClipNameTemplate so cam1 keeps its literal, and set fpsPhaseLock per camera.
6. **The primary's media gates see only the primary's own takes. Its trim worker and storage pre-roll can run during a take on cam1 alone, and a restarted primary requests a start pre-roll on its first watcher cycle.** Evidence: App:11432@31d5418 `if (camera_.isRecording() || soundRecordingActive() || camera_.timelapseActive() || camera_.mediaWritesPending() ||`; App:11086 `in.recording = camera_.isRecording();`; StoragePreroll.hpp:191-192 return Trigger::Start on the first mounted cycle. For the port: Pass 'any camera recording' into mediaTrimMayRun, storagePrerollGuard and the eject/format gates, or never let cam1 record alone.
7. **The opt-in kernel media tuning runs in every Core. Each media watcher calls the root helper with apply or restore (block queue, vm.dirty_*) when the mount changes.** Evidence: App:10903 and 10923@31d5418 call applyMediaTuning(profile, true/false); App:11361 `if (const char *env = std::getenv("APERTAR_MEDIA_TUNE"); env) {`, then `if (env[0] != '1')` returns; App:11382 calls the helper with apply or restore. For the port: Set APERTAR_MEDIA_TUNE=0 on the secondary so only the primary changes these system-wide settings.

Checker's note: All code read at the stated refs: Core 31d5418, UI c153c33, libcamera 6b0b49f3, driver cd548ef. Nothing was run. Result: 7 claims confirmed (C4 with a line fix), 4 partly (C5, C7, C8 and C2's script detail is fine). No second sensor is attached yet (r5), so every two-sensor effect here comes from code only. Two kernel behaviours are known V4L2 framework rules, not read here: a grabbed control returns EBUSY, and an unchanged value is not written. The most serious items for the plan: one IMX585 Core fails while the other camera streams (WDR grab), and standby, trim and pre-roll each check only their own process.

## Core record start, settings protocol, phase lock (r2 Q3-Q5, Q8)

### R1 · CONFIRMED · r2 Q3

- **Claim.** record_start (App:14216): with audio on, a prepare_recording broadcast and a 220 ms sleep (App:14298-14299); clip folder and name fixed at command time (CC:7543); recordingStartBootUs_ = BOOTTIME now, set after the writers start (CC:7631/7649).
- **Evidence.** App:14299@31d5418 `std::this_thread::sleep_for(std::chrono::milliseconds(220));` (inside `if (audioOptions.enabled)`, 14297). CC:5135@31d5418, reached from CC:7543: `return root / nextClipFolderName(root, settings, sensor, std::chrono::system_clock::now());`. CC:7649@31d5418 `recordingStartBootUs_ = clockMicroseconds(CLOCK_BOOTTIME); waitingForRecordingCadence_ = true; recordingFramesEnabled_ = true;` (7631 is the same line in the H.264/ProRes branch; both come after the writers start).
- **For the port.** T must lead the slowest path. That covers the primary's 220 ms, the folder scan, the ALSA open and the writer start. It also covers a wait of up to ~3.5 s for a running trim (App:12226-12228, 11590-11601) and a full reconfigure when a photo stream override is set (CC:7514). Names with {time} or {tc} come from each process's own now().

### R2 · CONFIRMED · r2 Q3

- **Claim.** The first recorded frame is the first completed request with SensorTimestamp/1000 >= recordingStartBootUs_ and FrameDuration within max(500 us, 2 %) of nominal; earlier ones are requeued (CC:9064-9084). Start at T = pass T in and use it instead of now.
- **Evidence.** CC:9072-9073@31d5418 `ready = (!timestamp || *timestamp / 1000 >= recordingStartBootUs_) &&` / `(!duration || std::abs(normalizeFrameDurationToUs(*duration, settings_.fps) - expected) <= std::max<int64_t>(500, expected / 50));`. CC:9082 `requeueRequest(request);`. The only callers are App:14302, CC:11847, CC:11947 (pre-roll) and CameraController.hpp:140.
- **For the port.** About 20-40 lines. Parse start_us as a string at App:14216, pass an optional through CC:11815, hpp:140 and CC:7507, use it at CC:7631/7649, and skip the 220 ms on the secondary. Also needed: refuse or flag a T that has already passed when the gate opens (today the take quietly starts late), report the first frame's time, and put T mid-period on the shared grid.

### R3 · PARTLY · r2 Q3

- **Claim.** FreeRun TC = time of day of RecordingClock.wallTime(SensorTimestamp), so two processes give simultaneous frames the same TC.
- **Evidence.** RecordingClock.hpp:40@31d5418 `offsetUs_ = wall - (before + clockMicroseconds(CLOCK_BOOTTIME)) / 2;`, built once per take at CC:7520 `recordingClock_ = RecordingClock();`. CdngEncoder.cpp:409@31d5418 `const int frame = static_cast<int>(((timestampUs % 1000000ull) * safeFps) / 1000000.0);`. Frame wall time comes from CC:9261-9265.
- **Correction.** The offset (REALTIME minus BOOTTIME) is the same in both processes to a few us. It differs only if the clock steps between the two samples, or a thread is preempted mid-sample (there is no retry). Equal TC per frame is not guaranteed, because each frame takes its TC from its own SensorTimestamp. Without a shared phase the frames can be up to a frame apart, and even on a shared grid a frame near a TC bin edge can land one frame off. ProRes and H.264 sample their own clocks (ProresEncoder.cpp:156, LibavH264EncoderPlugin.cpp:453).
- **For the port.** Put the shared grid in the middle of a FreeRun TC bin (at integer fps), or have the primary pass its offset or frame-0 TC. Do not pair frames by TC computed separately in each process.

### R4 · PARTLY · r2 Q4

- **Claim.** Control-only changes (fps, ISO, shutter, WB, EV) go through applyControls. Resolution, bit depth, format class, Clear HDR, colour profile and tuning reconfigure = stop(); start(), with a full CameraManager restart (CC:7452-7457).
- **Evidence.** CC:7457@31d5418 `return start(settings, error);` after `stop();`, where stop() does CC:7447 `cameraManager_.reset();` and start() makes a new manager at CC:7247. CC:10655@31d5418 `const bool applied = applySettingsLocked(next, rung != nullptr, commit);`. ISO, shutter, WB, EV and AF all call applySettingsLocked(next, false) (CC:11021-11183).
- **Correction.** fps also reconfigures when the mode ladder picks another rung (CC:10590, 10637-10655). A format change reconfigures only for H.264/ProRes or a resolution/bit-depth change (CC:11259-11263), and it loads that format's saved profile (CC:11216-11246). Colour profile reconfigures only when the active ISP profile changes (CC:12558). Tuning reconfigures directly (CC:11418-11419). Any fps change, phase-lock toggle or photo toggle releases the phase lock (CC:7490-7493).
- **For the port.** Mirror the resulting state, not the command: the same set_fps or set_record_format can give different modes in the two processes, because each has its own mode_ladder.conf and per-format profiles. Every reconfigure or fps change re-arms the lock, so the shared grid must be re-applied.

### R5 · PARTLY · r2 Q4

- **Claim.** Four settings serialisations: settingsBody App:298, settingsEvent CC:161, buildWebStateJson App:9264, buildCurrentPresetPayload App:7674 (applied by apply_preset App:13721). Can one apply_preset resync the secondary?
- **Evidence.** All five sites are at the stated lines @31d5418, and each has its own field list. Diffing the keys of App:7674-7867 against App:13721-14090: every emitted key is read; the HDR knobs are read at App:13914 `if (!readHdrKnob("cameraHdrThresholdHigh", presetSettings.hdrThresholdHigh, 4095) ||`. App:13760 `CaptureSettings presetSettings = camera_.settings();` reads flat fields. CC:12487 `if (recording_ || timelapseActive() || state_ != CameraState::Ready) {`.
- **Correction.** Every key is covered, but the payload cannot go as it is. Its keys sit under a nested settings object (App:7685), which the flat parser cannot take, so they must be flattened (as WebControlPage.cpp:18615-18620 does). apply_preset is refused while recording. The preset lacks the mode ladder and buffer mode. It carries keys the secondary must not take: cameraClipNameTemplate, recordAudioEnabled, soundRecorderEnabled, recordGyroEnabled and the audio devices. Auto ISO, WB and shutter travel as Auto.
- **For the port.** Yes, outside a take: the primary builds one flat apply_preset, drops the per-camera keys and sends set_mode_ladder separately. It may reconfigure, which re-arms the phase lock.

### R6 · PARTLY · r2 Q4

- **Claim.** The socket protocol is flat: fields map<string,string>, no nested objects or arrays (ControlProtocol.cpp:120-135, 164-247). A reply is one ok line plus the events raised meanwhile. Core has no outbound client (no connect()).
- **Evidence.** ControlProtocol.hpp:12@31d5418 `std::map<std::string, std::string> fields;`. ControlProtocol.cpp:124 `while (pos < text.size() && text[pos] != ',' && text[pos] != '}')`. App:14442@31d5418 `controlServer_.broadcast(eventJson);` for settings, recording, media, buffer, controls and standby events. git grep finds no connect( in src or include; the only sockets are the listeners at ControlServer.cpp:108 (AF_UNIX) and WebServer.cpp:197 (AF_INET).
- **Correction.** parseControlCommand is 164-233. Nested values are not refused: an object's inner keys leak into the map and parsing ends at the first }. Settings, recording, media, buffer, controls and standby events are broadcast by the setter before the ok line goes out (App:14428-14443, ControlServer.cpp:255-257). Only other events follow the ok line, collected under one process-wide flag (App:8293-8307, 14446-14451). HTTP /api/command returns no events (App:8317-8323).
- **For the port.** The relay must read line by line, skip event lines, match the ok line by id, send big numbers as strings, and never wait on the secondary while holding commandMutex_.

### R7 · PARTLY · r2 Q4

- **Claim.** Does every socket client get every event, including per-frame preview_frame with fds, or only subscribers (preview_subscribe App:14395)? What would a relay client have to drain or close?
- **Evidence.** ControlServer.cpp:179@31d5418 `if (client->closed || !sendLine(client->fd, line))`, inside a loop over every client. ControlServer.cpp:28 `const ssize_t written = ::send(fd, data, remaining, MSG_NOSIGNAL | MSG_DONTWAIT);`. App:14545@31d5418 `controlServer_.broadcast(out.str());` sends preview_frame; registrations go through broadcastWithFds (14543).
- **Correction.** Every client gets every broadcast; there is no subscriber list. preview_subscribe only re-sends the buffer registrations, to all clients (App:14396, 8226-8243). preview_frame is plain text with no fds; only preview_buffer carries SCM_RIGHTS dmabuf fds. Sends never block (ControlServer.cpp:28, 76), so a client that falls behind is dropped and its reply is lost.
- **For the port.** The relay connection to the secondary must read all the time (preview_frame at frame rate, audio_level, settings). It must close any fds it receives with recvmsg (with plain recv the kernel discards them) and reconnect if dropped.

### R8 · PARTLY · r2 Q5

- **Claim.** FramePhaseLock: PI servo on SensorTimestamp; originNs = first frame after (re)arm; pins FrameDurationLimits {d,d} within +-150 us; kp 0.06, ki 0.0015, deadband 6 us; stepped per frame by stepFramePhaseLock (CC:8773-8861) when fpsPhaseLock is on (default off), set by set_fps_phase_lock (App:12759). Can a shared originNs put both cameras on one grid?
- **Evidence.** FramePhaseLock.hpp:108@31d5418 `const double errorUs = (static_cast<double>(referenceNs - originNs) - static_cast<double>(frames) * periodNs) * 1e-3;`. :149-150 `originNs = referenceNs;` `frames = 0;`. Gains at :36-39, the pin at CC:8947-8950, the default at Types.hpp:138 and the command at App:12759 all match.
- **Correction.** The facts hold, but k is a frame counter since arm (:106; gaps are counted only while recording, :101-105), not taken from time. Passing originNs alone gives an error of (now - origin). The secondary must snap its first frame to the nearest slot (origin + round((ref - origin)/period) x period) and start the count at 0. The lock re-arms on its own grid (:95, :112-117) and is released by stop or reconfigure (CC:7403) and by fps, lock or photo changes (CC:7490-7493).
- **For the port.** Feasible, because both processes stamp frames with one kernel clock. Store a grid in FramePhaseLock and snap to it in arm() every time (about 20-40 lines plus a command). In an idealized model a half-period offset took about 250 frames (10 s at 24 fps) to stay within 50 us, with ~1.8 ms overshoot from integral windup. This needs fps headroom below the mode maximum.

### R9 · CONFIRMED · r2 Q8

- **Claim.** One process with two cameras is a large refactor (camera_ ~310 times in App; one CameraSession owns manager, camera and recorders); two processes is the smaller change.
- **Evidence.** App.hpp:145@31d5418 `CameraController camera_;`, which appears on 310 lines (330 tokens) of App. CC:10190@31d5418 `std::unique_ptr<libcamera::CameraManager> cameraManager_;`, with the camera at CC:10193 and the recorders at CC:10253-10263 (session_ is on 120 lines of CC). libcamera camera_manager.cpp:311@6b0b49f3 `<< "Multiple CameraManager objects are not allowed";` (Fatal).
- **For the port.** Two processes keep the single-camera path. In one process, any mode change would tear down the shared manager (CC:7445-7447), and both cameras would share one tuning, set as process env (CC:1421-1431).

### New findings

1. **Stopping at a time T is more than the mirror of the start test.** Evidence: CC:7671@31d5418 `{ std::lock_guard lock(recordingFrameMutex_); recordingFramesEnabled_ = false; }` is the first thing stopRecording does, then it finalises. For the port: A timed stop needs a gate that records only ts < T_stop, plus a wait until a frame past T_stop has completed before finalising. Without it, the two takes end one relay latency apart.
2. **Nothing outside Core says when or where a take started.** Evidence: The reply (App:14305-14307) has only recording and drop counts. The recording event (CC:12719-12723) has active, drops, error and fault. firstFrameTimestampUs_ (CC:4641) stays internal. For the port: Add first_frame_boot_us and the folder to the reply or event, so the primary can check alignment and pair the clips.
3. **In one camera, frame 0 can land one slot later.** Evidence: Once the gate opens (CC:9074), recordRawFrame can return before nextFrameIndex: missing WB (CC:9271-9276) or an unmapped buffer (CC:9296-9298). That frame is requeued, and the next one sets firstFrameTimestampUs_ (CC:4641). For the port: Check pairs by first-frame timestamps, not by frame index alone.
4. **A fixed shared grid needs no originNs exchange.** Evidence: FramePhaseLock.hpp:21-24 uses only differences of the reference clock, and both processes read SensorTimestamp from the same kernel clock. For the port: Each process can snap to k x period from an agreed epoch (for example one aligned to the TC grid), given the same fps string. This survives a restart of either process.
5. **The time zone and clock steps are per process.** Evidence: TC uses localtime_r (CdngEncoder.cpp:403-405, RecordingClock.hpp:56). git grep finds no tzset or TZ in Core. apply_time_zone runs timedatectl set-timezone and set-ntp true (App:3931, 3939). For the port: glibc localtime_r keeps the zone from its first call [P]. A secondary restarted after a zone change would then write TCs hours off from the primary's, and an NTP step between the two takes' samples shifts one offset. Restart both Cores after a date or zone change, or have the primary pass its offset.
6. **Each process pairs CFE and pispbe in the same order and locks only the pair it uses.** Evidence: pisp.cpp:1163-1189@6b0b49f3: each match() takes the next free rp1-cfe and the next free pispbe. pipeline_handler.cpp:174-175@6b0b49f3 `for (std::shared_ptr<MediaDevice> &media : mediaDevices_) {` / `if (!media->lock()) {` at acquire. For the port: Two processes take separate CFE+BE pairs if both enumerate in the same order [P]. Check on the Pi once cam1 is enabled.
7. **Slow commands on the primary swallow other events.** Evidence: App:8293-8307 sets one process-wide collect flag for each command, and App:14446-14451 diverts non-key events into that command's reply. For the port: While a relayed command waits, audio_level, camera_state and hardware_action events miss the UI. Run the relay on its own thread and answer the UI first.

Checker's note: I read only with git show and git grep at the given refs (Core 31d5418, libcamera 6b0b49f3), and nothing on the Pi. The phase-lock numbers come from a Python model fed on stdin. It assumes integer-us requests, a 2-frame delay, no line quantisation and no jitter, so treat them as order of magnitude only. Three statements rest on general Linux and glibc knowledge, not on code read here: REALTIME minus BOOTTIME stays constant under NTP slew; fds sent with SCM_RIGHTS are discarded on a plain recv; localtime_r keeps its first zone. I did not compare the Pi's libcamera 7e9fef0b.

## Touch UI, HDMI window, WebUI (r3)

### U1 · CONFIRMED · r3 Q1 (preview client path, control bridge path)

- **Claim.** Only ApertarPreviewSocketClient hard-codes /tmp/apertar-core.sock (as a default argument) and it ignores APERTAR_CONTROL_SOCKET. ApertarControlBridge (commands :1168, event socket :1805), MediaStatusBridge:23, AudioDeviceBridge:347 and SystemActionBridge:71 read APERTAR_CONTROL_SOCKET at each use, with the same fallback.
- **Evidence.** src/ApertarPreviewSocketClient.hpp:31@c153c33 `Q_INVOKABLE bool connectToCore(const QString &socketPath = QStringLiteral("/tmp/apertar-core.sock"));`. src/ApertarControlBridge.cpp:1168@c153c33 `const QString socketPath = qEnvironmentVariable("APERTAR_CONTROL_SOCKET", QStringLiteral("/tmp/apertar-core.sock"));`; the same call is at :1805, src/MediaStatusBridge.cpp:23, src/AudioDeviceBridge.cpp:347 and src/SystemActionBridge.cpp:71. Grepping connectToServer and sockaddr_un finds no other Core socket client. Core's default is the same path (src/main.cpp:32@31d5418, scripts/start-apertar-core.sh:6).
- **For the port.** The env var applies to the whole process, so it cannot point one object at cam1. Leave these five on the primary; a cam1 client needs its own path argument.

### U2 · CONFIRMED · r3 Q1 (preview client path, trap)

- **Claim.** connectToCore(path) takes a path, stores it in m_socketPath and reuses it for the 1 s single-shot reconnect. Every caller calls it with no argument (Main.qml:207, ExternalMonitorWindow.qml:328, main.cpp:228 and :348), so a copied second client would connect to cam0's socket.
- **Evidence.** src/ApertarPreviewSocketClient.cpp:54@c153c33 `m_socketPath = socketPath;`. At :16-22 the 1000 ms single-shot timer calls connectToCore(m_socketPath). At :105, disconnectFromCore() runs `m_socketPath.clear();`. The no-argument calls are at qml/Main.qml:207, qml/ExternalMonitorWindow.qml:328 (`apertarPreviewBridge.connectToCore()`), src/main.cpp:228 and :348@c153c33.
- **For the port.** Pass cam1's path explicitly everywhere cam1's client connects. The proposed fix of making connectToCore() default to the last path needs a new member, because disconnectFromCore() clears m_socketPath on every standby (main.cpp:346, EMW:326).

### U3 · CONFIRMED · r3 Q1 parsing; Q2 frames and dma-buf

- **Claim.** How frames arrive: the client sends preview_subscribe and receives two kinds of line. preview_buffer lines bring dma-buf fds over SCM_RIGHTS; preview_frame lines bring a slot number. It parses them by substring scan and emits previewFrameReady. The renderer then schedules a window update, and render() reads currentPreviewFrame(). Each buffer is imported once as an EGLImage (YUV420, BT.709 narrow, GL_TEXTURE_EXTERNAL_OES) and cached by fstat dev/ino.
- **Evidence.** src/ApertarPreviewSocketClient.cpp:165@c153c33 `{"cmd":"preview_subscribe","id":0}`. SCM_RIGHTS at :220-227; only preview_buffer and preview_frame are handled (:342-369); substring scan at :615-655. src/PreviewWindowRenderer.cpp:434-436 connects previewFrameReady to scheduleWindowUpdate; :2405 calls currentPreviewFrameFromBridge(); dev/ino key at :462-474; :1720-1765 makes three dup'd fds with `EGL_LINUX_DRM_FOURCC_EXT, DRM_FORMAT_YUV420` and `EGL_YUV_COLOR_SPACE_HINT_EXT, EGL_ITU_REC709_EXT`; the cache is wiped at :1630-1639. Core sends registrations with fds and frames without them (src/ApertarCoreApp.cpp:14542-14546@31d5418).
- **For the port.** A cam1 picture needs only a second client instance on cam1's socket path. Nothing in the chain is limited to one per process.

### U4 · CONFIRMED · r3 Q2 Singletons; Q8 two textures

- **Claim.** The preview client, preview item and renderer have no singletons and no shared static state. Two renderers can share one window's GL context, and the code shows no limit on that.
- **Evidence.** src/main.cpp:274@c153c33 is the only QML type registration, and grep finds no singletons. In src/PreviewWindowRenderer.cpp the statics are function-local GLSL strings (:681-927); EGL entry points and the display are looked up on each call (:1703-1710); the cache, FBO and textures are members (.hpp:236-272). The client has only `static constexpr int kOwnedFdProcId = -4242;` (.hpp:49) and one local constexpr (.cpp:188). Nothing clears the whole window: the direct path sets `glViewport(dstLeft, dstBottom, targetSize.width(), targetSize.height());` (:2267) and the FBO path clears only its own FBO (:2030-2038). The item itself draws nothing: `setFlag(ItemHasContents, false);` (src/CameraPreviewItem.cpp:9).
- **For the port.** A second client, item and renderer need no class changes. All of it (two socket readers, two imports, two draws) runs on the GUI thread under the basic render loop (main.cpp:254-256).

### U5 · CONFIRMED · r3 finding 3; Q2 traps (a), (b)

- **Claim.** PreviewWindowRenderer::render() ignores whether its item is visible; only scheduleWindowUpdate checks that. Two renderers on one window draw in the order they were connected, and that order decides which picture is on top in PiP.
- **Evidence.** src/PreviewWindowRenderer.cpp:347@c153c33 `if (!m_item->isVisible() || m_item->width() <= 0 || m_item->height() <= 0)` appears only in scheduleWindowUpdate. render() (:2388-2466) checks only m_window and m_item, and falls back to m_lastRenderableFrame (:2410-2412). :405-407 connects beforeRenderPassRecording to render with `Qt::DirectConnection`; this happens inside setPreviewItem (:380). An item of size 0 stops at r.isEmpty() (:2436-2440).
- **For the port.** Create the inset's renderer after the main one. To hide a pane, set its size to 0 (works today: it draws nothing and requests no redraws), or add an isVisible() check to render().

### U6 · PARTLY · r3 finding 1; Q8 display config

- **Claim.** On the rig the HDMI picture is ExternalMonitorWindow.qml, not CameraPage, because DisplayConfigBridge defaults hdmi_external_only=true, which hides the main window.
- **Evidence.** src/DisplayConfigBridge.cpp:294@c153c33 `m_hdmiExternalOnly = true;`; :354-357 also reads the key with default true. src/main.cpp:432-433 hides the main window when hdmiExternalOnly is set; :518 passes the flag to ExternalMonitorManager, whose externalScreen() picks the HDMI screen (src/ExternalMonitorManager.cpp:130-141). For the rig, KB working/drop-frames/night-2026-11-01.md:242 says hdmi_external_only=true; r5 does not cover this setting.
- **Correction.** The code part is right. The rig value comes from the KB note of 2026-11-01 and the code default, not from a read on the Pi tonight; the UI's startup journal line (main.cpp:281) would settle it. In this mode EMW and its renderer are destroyed on standby and rebuilt on wake (ExternalMonitorManager.cpp:113-114, 169-171, 264-278).
- **For the port.** Build the dual display modes in EMW first, and create the second renderer inside ensureWindow (ExternalMonitorManager.cpp:231-238) so it comes back after every wake.

### U7 · PARTLY · r3 Q3 EMW

- **Claim.** In EMW, monitorSurface holds one CameraPreviewItem that fills it, with the HUD layer above it (margin 36, z 20), so a second picture or a PiP inset goes into monitorSurface. The HUD uses apertarControlBridge 53 times.
- **Evidence.** qml/ExternalMonitorWindow.qml:389-396@c153c33 is monitorSurface, which rotates with the orientation setting. :404-428 is the CameraPreviewItem, `objectName: "externalPreviewItem"`, anchors.fill. :819-823 is the HUD Item, `anchors.margins: 36`, z 20. The HUD already fills all three bottom zones: resolution line on the left (:916-917), audio meter, status pill and timecode in the centre (:981), REMAINING on the right (:1218-1221). apertarControlBridge appears on 53 lines (85 uses) in the whole file.
- **Correction.** The 53 is lines in the whole file (85 uses), not the HUD alone. C++ finds the item by objectName (ExternalMonitorManager.cpp:231, main.cpp:176-177), so an inset needs its own objectName and its own findChild.
- **For the port.** Add the inset inside monitorSurface with its own objectName and its own displayRotation binding. The GL pictures draw under all QML, so a lower-right inset (Cinemate's default) would sit under the REMAINING text; pick another corner or trim the HUD.

### U8 · PARTLY · r3 Q3 closest pattern; storage and sync; Q7

- **Claim.** The externalMonitorMode setting is the model for a previewSource setting. It has four ends: a UI.conf key with a SettingsBridge property; Core's normaliser, reader and command; the state field ui.external_monitor_mode; and a WebUI select. The ends stay in sync through UI.conf: Core re-reads it on each /api/state, and the UI sees Core's writes through a file watch with a 10 s fallback poll. The report says the edit list is exactly this setting's sites.
- **Evidence.** UI@c153c33: SettingsBridge.hpp:48; SettingsBridge.cpp:361-362 load, :548 poll, :1079-1092 setter, :2166 and :2258 preset save and apply, :418-436 file watch plus `m_externalSettingsPollTimer.setInterval(10000);`; SettingsPage.qml:2450-2491; consumer EMW:48-50. Core@31d5418: normaliser :863-869, snapshot :1871, reader :2042-2043, preset :7768-7769, apply_preset :14027, state :9617 inside buildWebStateJson (served only as /api/state, :8396-8399; reads UI.conf at :9293), command :13267-13278, help list :12496, writer :2217-2301 (Qt lock, atomic write). WebUI: select :5272, options :6444 and :15502, value :15560, change handler :20328-20329 calling applySelectCommand :18897, optimistic patch :14129-14130, favorites :10889-10890, preset allow-list :18646.
- **Correction.** The report's list misses Core apply_preset :14027 and WebUI :6444, :15502, :15560, :10889-10890 and :18646. Core's command is strict: `if (trimAscii(*value) != normalized)` replies 'Unsupported external monitor mode.' (:13273-13274). Core's normaliser also drops the UI's 'Overlay Feed' alias (:863-869 vs SettingsBridge.cpp:1081-1084).
- **For the port.** Copy every site, and fix one set of canonical values first: a copied strict check refuses Cinemate tokens unless they are the canonical values. The primary writes UI.conf and the UI follows; no socket event is needed.

### U9 · PARTLY · r3 Q1 control bridge path

- **Claim.** A second ApertarControlBridge needs only a socketPath constructor argument (about 6 lines). Every instance writes the camera/* placeholder keys to UI.conf on each apply (:1019-1146), so a cam1 bridge would overwrite cam0's cached values.
- **Evidence.** src/ApertarControlBridge.cpp:120-122@c153c33: the constructor builds `m_settings(QStringLiteral("CinePi"), QStringLiteral("UI"))`, then calls `loadPersistedCameraSettings();`. :1019-1106 is the load and :1108-1146 the save. The save is called only from the apply setters and from preset apply (:286-843, :1298), never from event or state handling (:1318-1413, :1437+). The socket path is read at :1168 and :1805.
- **Correction.** The keys are written only when that bridge's own apply setters run. A cam1 bridge used only for status never writes them, but its constructor shows cam0's cached camera/* values until its first get_state reply.
- **For the port.** Under the relay plan the UI sends no commands to cam1, so no key prefix is needed. A second control bridge may not be needed at all (new finding 1).

### U10 · PARTLY · r3 finding 2; Q6 CORS

- **Claim.** Core answers 403 to any request whose Origin differs from http://<Host>, so a cross-port fetch from the :8000 page to :8001 is refused by Core itself. Core sends no CORS headers, and OPTIONS returns a bare 204.
- **Evidence.** src/web/WebServer.cpp:159-173@31d5418: `if (site != request.headers.end() && toLower(site->second) == "cross-site") return false;`, then `if (origin == request.headers.end()) return true;`, then `return expected == "http://" + authority;`. This runs for every request before the handler (:373-376). Response headers are built at :130-157; no Access-Control-* header exists anywhere in src. OPTIONS 204 at src/ApertarCoreApp.cpp:8327-8332.
- **Correction.** Core also answers 403 when Sec-Fetch-Site is cross-site, and when Origin is set but Host is missing or malformed; a ':80' suffix is ignored. The check runs before routing, so a cross-origin preflight gets 403, not the 204.
- **For the port.** The :8000 page can neither read nor command cam1's API. Under the relay plan the primary can put cam1's status into its own /api/state, so no CORS change and no proxy are needed.

### U11 · CONFIRMED · r3 finding 2; Q6 aids and least intrusive option

- **Claim.** An <img> on the :8000 page can load http://<host>:8001/preview.mjpeg from a second Core, because an image request sends no Origin. The WebUI's viewing aids cannot process that image (canvas taint), so cam1 shows unprocessed.
- **Evidence.** src/ApertarCoreApp.cpp:8341@31d5418 `if (request.method == "GET" && request.path == "/preview.mjpeg") {` with no further check. src/web/WebServer.cpp:164 lets a request with no Origin through. Hosts that differ only in port count as same-site, so the cross-site test never fires. Core encodes only while someone is viewing (:9735), at most 640x360, quality 75, 30 fps (:79-82), and serves at most 32 web clients (WebServer.cpp:274). The aids read the image through texImage2D (WebControlPage.cpp:13473) and getImageData (:13564); there is no crossorigin attribute anywhere. The browser side follows the Fetch rules but was not tried.
- **For the port.** Add a second <img> at location.hostname plus the peer port, with no crossorigin attribute and aids off. cam1's Core must keep its web server on: with --web-port 0 it serves no MJPEG.

### U12 · CONFIRMED · r3 Q5 per-camera status

- **Claim.** Time left uses one data rate: MediaStatusBridge multiplies a single frameSizeMB by fps, both set by CameraPage, and its mount path is fixed at /media/RAW.
- **Evidence.** src/MediaStatusBridge.cpp:383@c153c33 `const double mbPerSecond = m_frameSizeMB * m_fps;`. src/MediaStatusBridge.hpp:142 `QString m_mountPath = QStringLiteral("/media/RAW");`, and the property is CONSTANT (:16). CameraPage sets fps at qml/CameraPage.qml:325-327 and :335 and frameSizeMB at :1059; these are property handlers, so they run while the window is hidden. The HDMI REMAINING readout uses it (qml/ExternalMonitorWindow.qml:150-153, :1218).
- **For the port.** With both cameras writing to one drive, the HDMI REMAINING reads about twice too long. Add cam1's data rate in recalculateRemaining.

### New findings

1. **Core sends every event to every control-socket client, with no subscription filter. That includes recording, buffer (which carries the dropped-frame count), standby, media and every preview line. A client that does not keep reading its socket is dropped.** Evidence: src/ipc/ControlServer.cpp:175-182@31d5418 `if (client->closed || !sendLine(client->fd, line)) removeClient(client);`; sendLine sends with `MSG_NOSIGNAL | MSG_DONTWAIT` (:28). Broadcasts at src/ApertarCoreApp.cpp:14430-14442 and :14542-14546. preview_subscribe only re-sends the buffer registrations (:14395-14397). In the UI, the preview client throws away non-preview events (src/ApertarPreviewSocketClient.cpp:363-368@c153c33), and the dropped count arrives on the buffer event (src/ApertarControlBridge.cpp:1345-1348). For the port: cam1's preview socket already carries cam1's REC state, dropped count and standby. A CAM1 tag can therefore come from a few lines in the preview client's handleMessage, with no second control bridge and no status relay. The primary's relay link to cam1 must read all the time (or open one socket per command, as sendCoreCommand does), or cam1 drops it.
2. **Every preview frame carries timestamp_us, taken from libcamera's SensorTimestamp, and each Core numbers its frames with its own counter. The UI client ignores the timestamp.** Evidence: src/camera/CameraController.cpp:9957@31d5418 `if (auto ts = request->metadata().get(libcamera::controls::SensorTimestamp))`; the timestamp is set at :10049 and the frame counter at :10041. src/ApertarCoreApp.cpp:14513 writes timestamp_us into the message. handlePreviewFrame never reads it (src/ApertarPreviewSocketClient.cpp:471-613@c153c33). For the port: From data it already receives, the UI could show the cam0-cam1 phase offset (a live check on FramePhaseLock) and run a stale-frame watchdog. This works only if both Cores' sensor timestamps come from the same kernel clock (PROBABLE, not tried).
3. **A second Core started by start-apertar-core.sh would not come up. The script passes no --web-port, so the second Core tries to bind 8000, and a failed web bind stops Core's start.** Evidence: scripts/start-apertar-core.sh:44@31d5418 `exec ... "$CORE_BIN" --socket "$SOCKET_PATH" --media "$MEDIA_ROOT"`. The default port is 8000 (src/main.cpp:35). src/ApertarCoreApp.cpp:8067-8077 stops and returns false when webServer_.start fails. r5 shows the unit runs /home/pi/start-apertar-core.sh. For the port: Add a web-port variable to the start script for the secondary (for example 8001), and keep it non-zero, because the WebUI's cam1 picture depends on it. :8001 then also serves cam1's full WebUI and /api/command, and anything sent there bypasses the primary's relay.
4. **The UI sends user_activity to its one control bridge only. Each Core runs its own idle-to-standby timer, using the shared standbyTimeoutSeconds, and resets it only on user_activity, wake, set_*, record_* and timelapse_* commands.** Evidence: src/main.cpp:332-333@c153c33 connects SleepManager::userActivity to the one bridge; src/ApertarControlBridge.cpp:1312-1316 sends it. src/ApertarCoreApp.cpp:8269-8281@31d5418 sends enter_standby when the idle time runs out; :12229-12235 is the list of commands that reset the timer. For the port: The primary must forward user_activity, enter_standby and wake to cam1, or cam1 drops into standby on its own. With that forwarding the UI needs no change here, and the cam1 preview client can follow bridge 0's standby (main.cpp:343-349, EMW:321-330).
5. **Time left is computed in two places, each with one data rate: the UI's MediaStatusBridge, and Core's record_time_left_minutes for the WebUI.** Evidence: src/ApertarCoreApp.cpp:9376-9385@31d5418 `const uint64_t estimatedBytesPerSecond = estimatedRawBytesPerSecond(settings);` feeds record_time_left_minutes (:9553), which exists only in buildWebStateJson. For the port: With the relay in place, the primary can add cam1's bytes per second in Core for the WebUI. The HDMI REMAINING still needs the MediaStatusBridge change.
6. **A cam1 inset can take its aspect ratio from the frame itself. previewAspectRatio defaults to 0, and the renderer then uses capture_width and capture_height, which Core sends with each buffer registration.** Evidence: src/CameraPreviewItem.hpp:152@c153c33 `float m_previewAspectRatio = 0.0f;`. src/PreviewWindowRenderer.cpp:1859-1864 uses captureWidth/captureHeight unless previewAspectRatio is above 0.01. Core sends the capture size at src/ApertarCoreApp.cpp:14520-14521@31d5418. For the port: The inset needs no cam1 control bridge to get its aspect right: leave previewAspectRatio unbound on it.
7. **Swapping a bridge between fixed main and inset items (r3's PiP plan) does not reset the renderer. syncState only reconnects signals, and when the new bridge has no frame yet, render() keeps drawing the old camera's last frame.** Evidence: src/PreviewWindowRenderer.cpp:410-426@c153c33: syncState swaps m_bridge without any reset. :2410-2412 `latestFrame = m_lastRenderableFrame;`. The cache is wiped only on a layout, sequence or capture-size change (:1630-1639). cleanupImportedBuffers zeroes m_currentTexture and m_lastRenderableFrame (:1281, :1290), and m_resetPreviewState triggers it (:2398-2403). For the port: After a swap to a camera with no frame, the pane shows the other camera's last picture instead of black, which defeats r3's hasFrame fallback. Setting m_resetPreviewState in syncState when the bridge changes (one line) fixes it.

Checker's note: All 12 claims were read at the given refs (UI c153c33, Core 31d5418) with git show/grep only. The checkouts' HEADs had moved (UI ea44bd7, Core a40112a), so every read used the explicit refs. No files were written. The browser side (no Origin on an image request, canvas taint) follows the Fetch/HTML rules but was not tried. The rig's hdmi_external_only comes from the KB note of 2026-11-01, not from a read on the Pi. Small slips in r3 outside the 12 claims: the touch-window renderer is at main.cpp:514-515 (not 511-515); EMW 'top info row :201-207' is the data array, while the row item is at :825-830; the img src is set in loadPreviewStream (:13656-13661), which installPreviewStream calls. Under the relay plan the UI may need only a second preview client, item and renderer pointed at cam1, plus the previewSource setting. It may not need a second control bridge, because cam1's status already arrives on cam1's preview socket (new finding 1).

## How Cinemate does dual (r1)

### M1 · CONFIRMED · r1 Q1

- **Claim.** One cinepi-raw per sensor, started with --camera <libcamera index> and --cam-port camN. Cameras come from `cinepi-raw --list-cameras` (retried for 10 s, ClearHDR repeat de-duplicated). The port comes from the DT path (i2c@88000 = cam0; i2c@80000 or i2c@70000 = cam1; anything else = cam0). The list is sorted by port, so cam0 is primary. Starts are 0.5 s apart, and the 2.0 s ready wait only warns.
- **Evidence.** src/module/cinepi_multi.py:185-191,209-247,682-683,793,1007,1053,1060,1063-1075@d6cc93e. core/rpicam_app.hpp:186@63a08d5: the index order is the camera id sorted descending, so i2c@88000 gets index 0. Quotes: `if 'i2c@80000' in self.path or 'i2c@70000' in self.path:` | `cams.sort(key=lambda c: c.port)` | `primary=(i == 0),`
- **For the port.** Apertar Core opens the first non-USB camera (CameraController.cpp:7262-7265@31d5418). The secondary Core needs an explicit selector by camera id, or both Cores open cam0. On this CM5 the id's i2c@88000 or i2c@70000 names the port.

### M2 · CONFIRMED · r1 Q2

- **Claim.** Both processes subscribe to one Redis channel, cp_controls, and apply every key published on it: iso, awb, cg_rb, shutter, fps, mode and sizes, lores, zoom, HDR knobs, fps_phase_lock, pll_*, is_recording, cam_init. There are no per-camera control keys. Only outputs are per camera: cinepi_ready_camN, timestamp_camN, tc_camN, cameraPort in cp_stats, last_dng_camN, log_encode_camN. Per-camera launch flags (tuning, flips, name, log) come from sensors.camN.
- **Evidence.** cinepi/cinepi_controller.cpp:1158-1166,1188@63a08d5. src/module/redis_controller.py:367-368 and src/module/cinepi_multi.py:288-291,656-658,868-875@d6cc93e. Quotes: `auto r = redis_->get(msg);` | `sub.subscribe(CHANNEL_CONTROLS);` | `self.r.publish("cp_controls", key_name)`
- **For the port.** The primary must relay every shared setting to the secondary, in the same order: exposure, WB, fps, mode, HDR, phase lock, record edges and cam_init. Cinemate never sets a value for one camera only.

### M3 · CONFIRMED · r1 Q4

- **Claim.** The secondary copies its lores I420 frame into SysV shm key 0x43494E44 ('CIND'), with a seq counter and no lock. The primary owns DRM and composites both, cam0, cam1, pip_cam0 or pip_cam1, reading hdmi_preview_source every 15 frames. PiP defaults are 0.28, lower_right and 0.03. cam1 and PiP fall back to cam0 until a same-size secondary frame exists.
- **Evidence.** cinepi/dualHdmiPreviewStage.cpp:66,71,75,178,461-465,477-488,539-549@63a08d5. Defaults: same file :118-120,167-169; src/module/cinepi_multi.py:393-395 and config_loader.py:788-791@d6cc93e. Quotes: `constexpr key_t kShareKey = 0x43494E44;` | `share_ && share_->seq != 0 && share_->width == pane_w && share_->height == pane_h;` | `if (mode == PreviewMode::Cam1 && !have_secondary)`
- **For the port.** Usable for an HDMI view the primary owns, with three additions. A frame time or heartbeat, because a dead secondary leaves a frozen pane. A seqlock, because torn frames are possible. Scaling, because any lores size mismatch means cam0 forever, and in 'both' the right half stays black.

### M4 · CONFIRMED · r1 Q3

- **Claim.** cinemate writes record_cams before is_recording=1. The target is chosen in this order: a rec override (cam0, cam1, both or dual); else both if the preview is 'both' or sensors.record_policy is always_both; else the preview's main sensor (follow_preview, the default). Each cinepi-raw reads record_cams on the start edge (empty or 'both' means record), and a sensor that sits out keeps previewing. Folders are named CINEPI_<date>_<HHMMSS>_F<ff>_C<n>_<camN>. The shipped default_hdmi_source 'cam0' makes a dual rig record cam0 only.
- **Evidence.** src/module/cinepi_controller.py:2264-2282,2355-2358, src/module/cli_commands.py:356-360 and settings.jsonc:464@d6cc93e. cinepi/cinepi_controller.hpp:201-208,225-229 and cinepi/utils.cpp:84-86@63a08d5. Quotes: `if preview == "both" or lock_dual:` | `return sel.find(port) != std::string::npos;` | `"default_hdmi_source": "cam0",`
- **For the port.** Keep the choice of target in the primary, but send the secondary an explicit start that carries one take name and one start slot. Cinemate names each folder from that process's own next frame, so cam0 and cam1 names and TCs can differ.

### M5 · CONFIRMED · r1 Q3

- **Claim.** Every recording process starts its own cinepi-audio-capture writing <folder>/<folder>.wav, with no gating by camera port. The installer's ALSA devices (mic_24bit, mic_16bit) are plug over dsnoop, so one mic gives one WAV in each camera's folder.
- **Evidence.** cinepi/cinepi_sound.cpp:835,855-862,1720-1731@63a08d5 and cinemate-install.sh:1322-1353@d6cc93e. Quotes: `oss << options_->mediaDest << '/' << options_->folder << '/' << options_->folder << ".wav";` | `type dsnoop` | `pcm.mic_24bit { type plug; slave.pcm "mic_dsnoop_24" }`
- **For the port.** With two Cores, record audio in the primary only (one WAV per take), or first prove that two dsnoop readers work. Cinemate never logged two captures at once. Its start() pkill of '--discard-output' helpers also kills the other process's VU monitor (cinepi_sound.cpp:619,761,1119).

### M6 · CONFIRMED · r1 Q5

- **Claim.** --sync only picks which process runs the phase lock: off and server run it, client turns it off. SyncMode is sent only by core RPiCamEncoder, which CinePIRecorder does not use, and nothing waits for SyncReady. No Cinemate tuning has rpi.sync, and neither do the libcamera fork's imx585, imx585_mono and imx283 tunings. So cam1 free-runs, each process starts a take on its own next frame, and there is no frame alignment.
- **Evidence.** cinepi/cinepi_controller.cpp:1237, cinepi/phase_lock_core.hpp:75, core/rpicam_encoder.hpp:37-42, cinepi/cinepi_recorder.hpp:30,39-44 and cinepi/cinepi_raw.cpp:411-430@63a08d5. src/ipa/rpi/common/ipa_base.cpp:1363-1376@bfe0b76a0. grep rpi.sync: 0 hits in cinemate resources/tuning_files and in pisp imx585, imx585_mono and imx283.json. Quotes: `const bool roleClient = (options_->sync == 2);` | `class CinePIRecorder : public RPiCamApp` | `SyncAlgorithm *sync = dynamic_cast<SyncAlgorithm *>(controller_.getAlgorithm("sync"));`
- **For the port.** Cinemate has no working sync to copy. The plan, a phase lock in both Cores on one grid, is new work. rpi.sync is no fallback on this Pi: no tuning has the block, and lo has no multicast (r5).

### M7 · CONFIRMED · r1 Q3

- **Claim.** The mid-take join is dead code: the preview switches to 'both' during a cam0-only take and the sensor that sat out should open a fresh folder.
- **Evidence.** The cinemate side runs: src/module/cinepi_controller.py:2301-2321,4261-4262@d6cc93e. In cinepi-raw it can never fire. At the start edge the subscriber sets is_recording_ on every process (cinepi/cinepi_controller.cpp:786-792). The sensor that sits out returns without clearing it (cinepi/cinepi_controller.hpp:225-228). The join needs it false (hpp:318@63a08d5). Quotes: `is_recording_ = level;` | `if (rec_flag && baseline_flag_ && !is_recording_ && recordCamsIncludesSelf())`
- **For the port.** Do not port the join. A late join should be an explicit start from the primary. The branch does fire after a local stop (RAM pool full, cinepi_raw.cpp:450), and then it reopens a clip mid-take.

### M8 · CONFIRMED · r1 Q7, headline 4

- **Claim.** lessons/hardware-log.md has no dual-sensor entry. The record gate, PiP and join have no hardware report. Only commit messages show dual use on hardware: recording in 2025-06 and the preview on 2026-07-06.
- **Evidence.** lessons/hardware-log.md:430@c99ff77 is the only dual mention (`The rig had been rewired (dual → single)`). Line 1052's 'dual-probe' means mode enumeration. Hardware evidence is only in cinepi-raw commits 589b585 (2025-06-23) and cb4a30c, 7cc9c25, 94102f7 (2026-07-06). Commit 5072543 says 'Untested end-to-end'. c19e316 and 87e6fee (gate, PiP, join) make no hardware claim.
- **For the port.** Treat Cinemate's dual support as an untried prototype. Test every dual behaviour on this rig before the design relies on it.

### M9 · CONFIRMED · r1 Q5 (5b4b209), Q3

- **Claim.** Since 5b4b209 the phase lock and the time-of-day TC use the same clock in every process: FrameWallClock, or else a BOOTTIME-to-REALTIME offset cached once. Commit 94102f7 removed the per-process first-frame anchor that had put a fixed one-frame TC offset between cam0 and cam1.
- **Evidence.** cinepi/cinepi_controller.cpp:590-593,611-624,737@63a08d5, and the 94102f7 commit message. Quotes: `if (auto wc = completed_request->metadata.get(controls::FrameWallClock); wc)` | `boot_to_epoch_ns = real_now - boot_now;` | `updatePhaseLock(static_cast<int64_t>(epoch_ns), fps_user);`
- **For the port.** Put the shared grid on a clock every Core reads the same way. Apertar's FramePhaseLock already uses SensorTimestamp (BOOTTIME; CameraController.cpp:8775@31d5418). It is exact across processes and NTP steps do not move it. A REALTIME offset cached separately in each process can differ after an NTP step.

### M10 · PARTLY · r1 Q3

- **Claim.** DNG TC is the wall clock's HH:MM:SS plus llround(sub_us*fps/1e6) frames. It is anchored at the clip's first frame and then stepped by sensor-timestamp deltas, with no per-camera offset.
- **Evidence.** cinepi/dng_encoder.cpp:2094-2096,2109-2115,2127-2133@63a08d5. The value is set at cinepi/cinepi_controller.cpp:658. Quotes: `uint64_t origin_us = wallclock_ts_us_` | `? wallclock_ts_us_` | `uint64_t delta_us = static_cast<uint64_t>(encode_item.timestamp_us)`
- **Correction.** The origin is not the first frame's own stamp. It is a shared variable holding the newest wall clock process() has stored, read when the encode worker takes the clip's first frame. The two agree only while the encoder keeps up. Stepping by deltas and the missing per-camera offset are as stated.
- **For the port.** Carry each frame's own clock stamp, or its grid slot, with the frame, and derive TC and folder names from that. Then both Cores label the same slot the same way.

### M11 · CONFIRMED · r1 Q6

- **Claim.** With two candidate subdevs, the hint Camera::id() must equal the sysfs subdev name. The id is a DT path, so a rig with two imx585 is always AMBIGUOUS and falls back to binning derived from the size ratio. ClearHDR knobs open the first matching subdev. WDR is written to every subdev.
- **Evidence.** cinepi/subdev_binding.hpp:97-116, core/driver_mode_metadata.hpp:248,404,414, cinepi/cinepi_controller.cpp:81-89 and core/options.cpp:145-169@63a08d5. src/libcamera/sensor/camera_sensor_legacy.cpp:305 and camera_sensor_raw.cpp:564@bfe0b76a0. r5 shows the id is a DT path. Quotes: `if (c.second == camera_id_hint)` | `std::string path = "/sys/class/video4linux/v4l-subdev" + std::to_string(index) + "/name";` | `id_ = sysfs::firmwareNodePath(devPath);`
- **For the port.** Apertar has the same trap. openImx585Subdev() takes the first imx585 by name (CameraController.cpp:6875-6891@31d5418) and Clear HDR uses it (6925-6927), so a secondary Core would write to cam0's sensor. Bind by of_node == camera id, as resetStoppedSensorTiming already does (8118-8130).

### M12 · CONFIRMED · r1 Q1, headline 5

- **Claim.** Nothing supervises cinepi-raw: an exit is only logged and the 2.0 s ready wait only warns. Restarts happen only on operator or settings paths, and those stop and relaunch both processes.
- **Evidence.** src/module/cinepi_multi.py:317-318,972-974,1070,1073-1075@d6cc93e. grep finds no process liveness check in src/main.py or src/module/mediator.py. Quotes: `self.proc.wait()` | `logging.info('[%s] exited %s', self.cam, self.proc.returncode)` | `logging.info("All cinepi-raw encoders ready — starting supervisor.")` (the log line names a supervisor that does not exist)
- **For the port.** Someone must watch the secondary: the primary, or systemd (apertar-core already has Restart=on-failure, r5). The UI and WebUI must show it as down, and it must be re-synced after a restart. A take must not quietly become single-camera.

### New findings

1. **Dual broke silently for 8 months. On 2025-11-03 cinemate replaced --camera with --cam-port (8b58bcbb), so both processes opened camera 0 and the second exited with 'Device or resource busy'. --camera came back on 2026-07-06 (f2ddc33c).** Evidence: cinemate 8b58bcbb diff of src/module/cinepi_multi.py: `-            "--camera", str(self.cam.index),` and `+            "--cam-port", str(self.cam.port),`. Also the f2ddc33c commit message. For the port: The secondary Core must pick its camera explicitly and refuse to run if the camera it opened is not its port. A two-camera start test would catch a regression like this.
2. **The record gate leaks. During a take, is_recording_ is also true on the sensor that sits out. A record-through mode change (cam_init, the only mode-change path cinemate allows while recording) then makes that sensor create a folder and record DNGs and audio. Found by reading the code; not tried on hardware.** Evidence: cinepi/cinepi_raw.cpp:69-77,365-375@63a08d5: `bool resumeRecording = controller.isRecording();`. cinepi/cinepi_controller.cpp:792. src/module/cinepi_controller.py:2711,2782-2783@d6cc93e. For the port: Keep 'this camera records' separate from 'the rig records'. Only the primary's explicit start and stop should set the secondary's recording state.
3. **Neither phase lock has a shared grid. Cinemate and Apertar both set the reference point to the frame where the lock arms, so two locked processes keep the same rate at an arbitrary phase offset. In preview the lock re-arms when the error passes half a frame, and each step is clamped to 150 µs.** Evidence: cinepi/phase_lock_core.hpp:99-110,130,149@63a08d5. src/camera/FramePhaseLock.hpp:95-99,112,123@31d5418: `arm(fps, referenceNs);` For the port: Add a grid origin that both Cores share (slots at k x period on BOOTTIME, or the primary's origin relayed), and arm to the nearest slot. At the clamp, closing a half-frame offset at 24 fps takes about 140 frames, roughly 6 s.
4. **Fixed IPC names collide between instances. Both processes load sharedContext with ftok("/tmp", 0x43494E45), and the first to exit removes the segment. The CIND segment (mode 0600) is never removed. The MJPEG server on port 8000+index ends its process after 10 failed binds.** Evidence: cinepi/sharedContextStage.cpp:25,116,135,163, cinepi/dualHdmiPreviewStage.cpp:178 (no shmctl anywhere in the file) and cinepi/mjpegPreviewStage.cpp:251-277@63a08d5. src/module/cinepi_multi.py:389-390@d6cc93e. For the port: In a second Core, give every shm key, socket, port, lock and /run path a camera suffix, and clean them up on exit.
5. **Every launch writes wide_dynamic_range to all subdevs before opening its camera: 0 first, then 1 for --hdr sensor. The imx585 driver grabs that control while streaming, so a write to a sibling that is streaming fails. Cinemate kills any running cinepi-raw before its mode probe, because a grabbed control hides the ClearHDR modes.** Evidence: core/options.cpp:145-169,258,286@63a08d5. imx585.c:2108-2110@bd57617 and imx585.c:4209@cd548ef: `__v4l2_ctrl_grab(imx585->hdr_mode, true);`. src/module/sensor_detect.py:2673-2684,2743@d6cc93e. For the port: Each Core sets WDR only on its own sensor, before its CameraManager starts. Changing Clear HDR for the whole rig means stopping and restarting both Cores.
6. **Several shared output keys have two writers. Each process sets width and height from its own stream and writes lores_width and lores_height at launch. Both set and delete audio_vu. The cp_stats counters keep whichever process wrote last. cinepi-raw and the cinemate listener both write tc_camN, with different formulas.** Evidence: cinepi/cinepi_controller.hpp:127-128, cinepi/cinepi_sound.cpp:22,737,751 and cinepi/cinepi_controller.cpp:676,692-693@63a08d5. src/module/cinepi_multi.py:618-619 and src/module/redis_listener.py:852-882,911-921@d6cc93e. Commit 91975e88 fixed rec flicker caused by alternating frame counts. For the port: In Apertar's state API, key every per-camera value by camera and give each key one writer. The primary merges the secondary's state explicitly.
7. **Telemetry travels on the control channel. cinemate's set_value publishes every key it writes on cp_controls, per-frame keys included. Every cinepi-raw subscriber reads the key of every message before it looks for a handler, so the cost grows with each process.** Evidence: src/module/redis_controller.py:364-370,375@d6cc93e. cinepi/cinepi_controller.cpp:1158-1166@63a08d5. For the port: The relay from primary to secondary should carry only control changes, never per-frame values.
8. **The only hardware note on dual imx585 says it worked only without the overlay's link-frequency (2025-06-23). This Pi runs cam0 with link-frequency=891000000, and CFE already logs that data rate as out of range.** Evidence: cinepi-raw 589b585 commit message: 'dual sensors now work if imx585 link frequency is not used'. r5, config.txt line 42. For the port: Bring cam1 up first without link-frequency. Then try 891 MHz on both while watching CFE errors and dropped frames.
9. **Nothing is scaled for two sensors. Both processes get the same --max-pixel-rate, recorder worker profile and --buffer-count (about 25 MB of CMA per 4K buffer), the same CPUs 1-3 and the same chrt -f 70. Nothing was measured with two sensors.** Evidence: src/module/cinepi_multi.py:297-312,762-764,833,841-866@d6cc93e. For the port: Budget CMA, CPU, the shared RP1 link and the single NVMe for two Cores before relying on single-Core limits.
10. **The 2026-07-06 hardware run hit two canvas bugs. The cached dma-heap canvas showed static until writes were wrapped in DMA_BUF_IOCTL_SYNC. A single canvas buffer showed drifting black bands.** Evidence: cinepi-raw commits cb4a30c and 7cc9c25. cinepi/dualHdmiPreviewStage.cpp:499-504,576-580@63a08d5. For the port: Any compositor in the primary needs DMA_BUF_IOCTL_SYNC around CPU writes and double buffering from the start.
11. **Cinemate's docs describe sync and a mid-take join that the code does not do.** Evidence: docs/dual-sensors.md:3@d6cc93e: `Cameras are synchronized with cam0 being the server and cam1 being the client.` The join is described at line 41. For the port: In the Apertar design, cite Cinemate's code, not its docs.
12. **I2C bus numbers depend on the board. Cinemate's notes give CM5IO as cam0 = i2c-6 and cam1 = i2c-0, and its Pi 5 table hardcodes 6 and 4. This CM5 has cam0 on i2c-10 and cam1 on i2c-0 (r5).** Evidence: src/module/lens/cef168.py:546-551@d6cc93e. r5. For the port: Identify ports by DT path (i2c@88000, i2c@70000), never by bus number.

Checker's note: I read all 12 claims at the pinned refs with git show and git grep. Nothing was run on the Pi. Result: 11 CONFIRMED and 1 PARTLY (C10, where the TC origin comes from a shared variable). The code settles two items r1 left as probable: the join can never fire for a sensor that sat out (C7), and the subdev hint can never match (C11). Three things cannot be checked here: two audio captures at once on a rig, cam0/cam1 TC equality, and the composite on this Pi. I read Apertar refs only to judge design impact. Core opens the first camera and the first imx585 subdev. FramePhaseLock uses BOOTTIME and arms at the first frame it sees. The pisp pipeline pairs each CFE with its own back end (pisp.cpp:971-1000@7e9fef0b), and r5 shows two pispbe nodes. So two processes can each hold one camera, as Cinemate's two-process model assumes. r1 Q8's CM5 bus numbers (cam0 = i2c-6) do not match this CM5 (i2c-10).

## Where the reports disagree, and stale KB pages

### X1 · CONFIRMED · r4 Q6 + M0 vs r5 Facts (l.17, l.24)

- **Claim.** r4: cam1's I2C node is i2c@80000 (M0 predicts imx585 on i2c@88000 and i2c@80000). r5: on this CM5, cam1's I2C is rp1/i2c@70000 (/dev/i2c-0).
- **Evidence.** r5:17 (Pi DT, ground truth). src/module/lens/cef168.py:546-547@d6cc93e: 'the buses of a Compute Module 5 depend on' / 'the carrier board (CM5IO: cam0 i2c-6 / cam1 i2c-0; a Pi 5: 6 / 4)'. src/module/cinepi_multi.py:187@d6cc93e: 'if 'i2c@80000' in self.path or 'i2c@70000' in self.path:'. KB hardware-log.md:686: i2c-0 = 1f00070000.i2c.
- **Correction.** r5 is right for this rig: cam1 = rp1/i2c@70000 (i2c-0). i2c@80000 is the Pi 5 Model B's cam1 node. r4's M0 loop over /sys/class/i2c-adapter also fails on this kernel (hardware-log.md:687 says that directory does not exist; use /sys/bus/i2c/devices).
- **For the port.** The secondary picks its camera by the id substring i2c@70000 (also accept i2c@80000, as Cinemate does). Confirm the id from the 'Registered camera' journal line once cam1 is added.

### X2 · CONFIRMED · r4 Q6 (l.167) vs KB lessons/hardware-log.md:686 and r5 l.17-18

- **Claim.** r4: '11 = cam1' is only a label in a design note. KB: /dev/i2c-11 is a link to /dev/i2c-0. r5: there is no adapter i2c-11; i2c@70000 is alias i2c0 and i2c11.
- **Evidence.** hardware-log.md:686: '`/dev/i2c-6` and `-11` are links to `-10` and `-0`.' r5:17: 'the same controller as alias i2c0 (and i2c11)'.
- **Correction.** /dev/i2c-11 exists as a link to i2c-0, which is cam1's controller. /dev/i2c-6 links to i2c-10 (cam0). So '11 = cam1' is right as a device name. r5's 'no i2c-11' refers to adapters only.
- **For the port.** Bus numbers are aliases that change by board (Cinemate says cam0 = i2c-6 on the CM5IO). Key per-camera I2C devices on the DT node, never on a bus number.

### X3 · PARTLY · r4 Q6 (l.173-181) + verdict 5 vs r2 Q7 (l.90) and r5 l.54-55

- **Claim.** r4: use link-frequency=720000000 on both overlays for dual, because 891 MHz is above the RP1 D-PHY range. r2/r5: 891000000 on both.
- **Evidence.** imx585.c:1064@cd548ef: 'static struct imx585_mode supported_modes[] = {'. :4667-4668: 'supported_modes[]/supported_10bit_modes[], which are process-wide' / 'arrays shared by every imx585 instance the module binds.' imx585-overlay.dts:78@cd548ef default: '/bits/ 64 <720000000>;'. KB hardware-log.md:963: 891 MHz logs the DPHY warning but did not cause the losses. BootConfigText.hpp:159@31d5418 flags 891 as overRp1Spec.
- **Correction.** In code, the only dual rule is the same link-frequency and lane count on both overlays. 891 on both meets it and keeps cam0's tested modes: Clear HDR 4K reaches 30 fps at 891 and 25 at 720 (README.md:116-121@cd548ef). r4 is right that 891 is outside the D-PHY spec. Cinemate's driver README:243-251@bd57617 verified 891 on a CM5 with one sensor. cinepi-raw 589b585 (2025) reports dual working only without a link-frequency parameter, i.e. 720 on both. The overlay default is 720, so the cam1 line must name 891 explicitly.
- **For the port.** Write dtoverlay=imx585,link-frequency=891000000 for cam1 and watch cam1's CSI-2 error counters (track_csi2_errors=1 is already on). If cam1 shows errors, move BOTH overlays to 720. The Boot config card does not enforce equal link frequencies (BootConfigText.hpp:857-877).

### X4 · CONFIRMED · r4 Q6 (l.165, 168-171) + verdict 9 vs r5 l.13 and the carrier section

- **Claim.** r4: the carrier is never named; the CFexpress hat suggests a Pi-5-style carrier; check J6-type jumpers. r5: the carrier is a Waveshare CM5-IO-BASE-A (Mini Base Board (A)) and its docs mention no jumpers.
- **Evidence.** r5:12-13 (CM5 Lite c041a0, 4 GB; carrier named by Patrik, variant A PROBABLE). KB hardware-log.md:621: 'the Pi (CM5 + carrier)'. cinemate docs/raspberry-pi-models.md:11@d6cc93e gives only general advice to check carrier jumpers.
- **Correction.** The carrier is a Waveshare CM5-IO-BASE-A, and software cannot see it. J6 belongs to the official CM5 IO Board. Whether the Waveshare board needs no jumpers is UNVERIFIED here: r5 read its wiki, and this check had no web access.
- **For the port.** Drop the J6 step. Two hardware items stay open: which connector is MIPI1 (read the silkscreen), and whether cam1's I2C reaches that connector.

### X5 · CONFIRMED · KB architecture/overview.md:5 and hardware-log 'Tested: Pi 5 (4 GB)' entries (10-23 to 11-01) vs r5 l.12; r4 Q6 l.165

- **Claim.** KB: the hardware is a Pi 5 4 GB. r5: a Raspberry Pi Compute Module 5 Lite Rev 1.0, 4 GB.
- **Evidence.** r5:12: '/proc/device-tree/model' reads 'Compute Module 5 Lite Rev 1.0 (c041a0)'. hardware-log.md:621 ('CM5 + carrier') and :900 ('Tested: CM5') already disagree with the 'Pi 5' entries.
- **Correction.** Fix overview.md:5 to 'CM5 Lite 4 GB on a Waveshare CM5-IO-BASE-A'. The hardware log is append-only, so add a correction entry for the 'Pi 5' lines rather than editing them.
- **For the port.** Use CM5 facts throughout: cam1 I2C is i2c@70000 and both connectors share one regulator. BootConfigText already treats a CM5 as pi5 with two ports (BootConfigText.hpp:91, 127).

### X6 · CONFIRMED · r2 'Corrections' l.10 vs KB llm/README.md:94, :109-110; architecture/config.md:47; architecture/core.md:441

- **Claim.** KB: apertar-hardware.conf is read once at start, so restart Core after editing. r2: that is outdated; runControlsWorker polls the file every 2 s and live-restarts the driver groups that changed.
- **Evidence.** ApertarCoreApp.cpp:11882-11883@31d5418: 'It wakes on a save, and every 2 s looks for an edit made outside' / '(Config, ssh): no command handler waits for it, and it never applies during a take.' :11939-11969 restarts only the changed groups. KB fork-log.md:127 (dcf09ee, T39).
- **Correction.** Within 2 s, Core restarts only the changed groups: GPIO and PCF8574 (with tally and trigger), NeoRotary 4, Grove ADC, and a CFE-hat re-read. It never does this during its own take. The UI's [display] section and the automounter are still read once.
- **For the port.** If two Cores read one file, every save restarts drivers in both. The secondary needs its own APERTAR_HARDWARE_CONFIG or a role flag.

### X7 · CONFIRMED · r2 Q1 (tuning row) + open question 2 vs r4 Q1 'Cross-process hazard' + verdict 3

- **Claim.** r2: it is unknown [U] whether a second CameraManager disturbs the first camera. r4: every CameraManager start writes HBLANK=min, the flips and the test pattern on every sensor it enumerates, including one streaming in the other process, so do not reconfigure one Core while the other records.
- **Evidence.** camera_sensor_legacy.cpp:292@6b0b49f3 (identical at 7e9fef0b): 'ctrl.set(V4L2_CID_HBLANK, static_cast<int32_t>(hblankInfo->minimum));'. device_enumerator.cpp:351: 'if (media->busy())' (an in-process flag; lockf runs only in PipelineHandler::acquire, pipeline_handler.cpp:173-179). imx585.c:3540@cd548ef: 'ret = cci_write(imx585->regmap, IMX585_REG_HMAX, imx585->hmax, NULL);'. On the Pi's build the PiSP match is at pisp.cpp:969@7e9fef0b; r4's :1153 is the fork's line.
- **Correction.** The writes are confirmed in code; their size is untested (r4 M2). The HBLANK minimum is 0 (imx585.c:3392@cd548ef). The write is therefore a no-op while the other sensor sits at HBLANK 0 (4K Clear HDR 25 fps, hardware-log.md:250). At other lattice rates, or during phase-lock pushes, it shortens that sensor's line until its IPA rewrites HBLANK on the next frame (ipa_base.cpp:1874-1875). One Core start runs up to 2 probe managers plus 1-3 session managers (CC:7048-7057, 7246-7336@31d5418).
- **For the port.** Allow secondary (re)starts, and reconfigures of either Core, only while neither camera records. A crash-restart of the secondary mid-take would disturb the primary's frame period and phase lock.

### X8 · CONFIRMED · r2 Q5 'Alternatives' (l.77) and r4 Q3 'Imx585 tunings' (l.73) vs r1 Q5

- **Claim.** r2: Cinemate uses libcamera rpi::SyncMode (cinepi_multi.py:795-797). r4: Cinemate's cam0-server/cam1-client sync is a no-op only because the IMX585 tunings lack rpi.sync. r1: --sync never reaches libcamera at all.
- **Evidence.** core/rpicam_encoder.hpp:37-38@63a08d5 is the only place that sets SyncMode: 'if (options->sync == 0)' / 'cl.set(libcamera::controls::rpi::SyncMode, libcamera::controls::rpi::SyncModeOff);'. cinepi/cinepi_recorder.hpp:30: 'class CinePIRecorder : public RPiCamApp'. --sync only gates the phase lock (cinepi_controller.cpp:1237; phase_lock_core.hpp:75-80).
- **Correction.** r1 is right. Cinemate passes --sync, but cinepi-raw never sets SyncMode, so sync would stay off even with an rpi.sync tuning block. On the client the phase lock is released, so cam1 free-runs.
- **For the port.** Cinemate has no working sync to copy. Phase lock on a shared grid is new ground for Apertar and needs its own test: compare both cameras' SensorTimestamps, as in r4 M6.

### X9 · CONFIRMED · r2 Q5 (l.76) and the plan vs KB lessons/hardware-log.md:246-293 and architecture/core.md:596-597

- **Claim.** r2: FramePhaseLock can feasibly lock the secondary to the primary's phase (slew 150 us per frame). KB: on the Pi's libcamera the lock's pushes change HMAX, make the picture flicker and drop frames, so the lock stays off.
- **Evidence.** hardware-log.md:286-287: 'C0103 (on): 1478 frames, 10 holes' ... 'band step mean 0.53 %, p99 2.85 %, **max 8.9 %**'. cam_helper_imx585.cpp:105@7e9fef0b (the Pi's libcamera): 'When a single fixed frame rate is pinned we instead search the integer'.
- **Correction.** The lock math can align two sensors, since both use the CLOCK_BOOTTIME SensorTimestamp. As built, though, its pushes re-pick HMAX and damage takes. Nothing has changed since that test: FramePhaseLock.hpp was last touched in 80ddac1, stepFramePhaseLock only gained the ramp-grace gate (CC:8789-8790@31d5418), and the Pi still runs 7e9fef0b. r4's 'HMAX re-pick' [P] is CONFIRMED on the Pi (hardware-log.md:246-257).
- **For the port.** Fix this before any sync work. Either make lock pushes change VMAX only (skip the lattice for lock pins), or align in preview and return to the nominal pin before recording. Then redo the T27 take on one camera.

### X10 · CONFIRMED · r4 Q1 'Core single-camera assumptions' (l.42) vs r2 Q1 rows (pre-roll, trim, eject)

- **Claim.** r4: media actions (trim, pre-roll, format) are per process [U]. r2: they collide between two Cores [C].
- **Evidence.** ApertarCoreApp.cpp:11113@31d5418 runs automatic pre-roll unless APERTAR_STORAGE_PREROLL=0. :6379: 'const char *env = std::getenv("APERTAR_MEDIA_TRIM");'. :11397: 'APERTAR_MEDIA_TRIM=0 switches the whole feature off.'
- **Correction.** Each Core runs its own pre-roll and trim on the same drive. The secondary must set APERTAR_STORAGE_PREROLL=0 and APERTAR_MEDIA_TRIM=0, and eject and format stay primary-only.
- **For the port.** Otherwise the secondary's boot pre-roll and trim run on /media/RAW alongside the primary's.

### X11 · PARTLY · r3 Q7 'Owner' (l.135) vs r2 Q1 UI.conf row, 'Must be per-instance' 4 and the sample unit

- **Claim.** r3: both Cores and the UI share one UI.conf, and cam1's Core (:8001) reads the same values. r2: give the secondary its own XDG_CONFIG_HOME (/home/pi/.config-cam1).
- **Evidence.** ApertarCoreApp.cpp:519-520@31d5418: 'if (const char *xdgConfig = std::getenv("XDG_CONFIG_HOME"); xdgConfig && *xdgConfig)' / 'return std::filesystem::path(xdgConfig) / "CinePi" / "UI.conf";'. CameraController.cpp:418: '... / "apertar-core" / "camera_settings.conf";' (mode_ladder.conf at :405 follows the same variable).
- **Correction.** A single XDG_CONFIG_HOME moves UI.conf, camera_settings.conf, mode_ladder.conf and the hardware-state notes together. With r2's unit the secondary reads its own UI.conf, so the shared values r3 relies on never reach it.
- **For the port.** Pick one. Either share UI.conf and add a separate path for camera_settings and mode_ladder, or split XDG and have the primary relay timecodeMode, standbyTimeoutSeconds and photoModeEnabled. Otherwise timecode mode and standby will differ between the cameras.

### X12 · CONFIRMED · r2 Q6 'preview_source_cycle' (l.83) vs r3 Q1 'Trap' (l.17)

- **Claim.** r2: connectToCore is called without a path at Main.qml:207 and main.cpp:228. r3: there are four such calls (also ExternalMonitorWindow.qml:328 and main.cpp:348).
- **Evidence.** git grep at c153c33 finds 'apertarPreviewBridge.connectToCore()' at qml/ExternalMonitorWindow.qml:328, qml/Main.qml:207, src/main.cpp:228 and :348. ApertarPreviewSocketClient.hpp:31 defaults to '/tmp/apertar-core.sock'.
- **Correction.** There are four calls without a path, and the preview client ignores APERTAR_CONTROL_SOCKET. KB ui-map.md:499 lists them at old lines (EMW:290, main.cpp:346).
- **For the port.** A cam1 preview client must get the cam1 socket path at all four sites, or it attaches to cam0.

### X13 · CONFIRMED · r2 Q5 vs r4 Q4 vs r1 Q5 vs KB architecture/drivers.md:104

- **Claim.** Where the driver parses sony,sync-mode: r2 says imx585.c:2585-2593; r4 says e5b74d3:2566-2573 and cd548ef:4649-4656; r1 says 2379-2416@bd57617; the KB says 2335-2342.
- **Evidence.** imx585.c:2567@e5b74d3, :4650@cd548ef and :2410@bd57617 all read: 'if (!device_property_read_string(dev, "sony,sync-mode", &sync_mode)) {'.
- **Correction.** r4 is right. The Pi's driver has it at cd548ef:4650-4656, e5b74d3 at 2567-2573 and bd57617 at 2410-2416. r2's 2585-2593 matches no ref, and the KB's line is stale.
- **For the port.** None for software sync. It matters only if XVS wiring is tried later.

### K1 · CONFIRMED · KB architecture/drivers.md:118 vs r2 Q1 and r4 Q1

- **Claim.** KB: 'Core has no Clear HDR support. Nothing in Core writes WIDE_DYNAMIC_RANGE ... The only direct subdev write is resetStoppedSensorTiming()'. r2/r4: Core writes WDR and the IMX585 HDR controls on the first imx585 subdev.
- **Evidence.** CameraController.cpp:6925@31d5418: 'bool setSensorWideDynamicRange(bool enabled, std::string *error)'. :6935: 'ctrl.id = V4L2_CID_WIDE_DYNAMIC_RANGE;'. :6960: 'bool writeImx585ExtControl(uint32_t id, int32_t value, const uint16_t *pair, std::string *error)'.
- **Correction.** Core writes WIDE_DYNAMIC_RANGE (CC:6925-6952) and the HDR threshold, blend and gain-adder controls (CC:6954-6970) on the first imx585 subdev (CC:6875-6892), before every CameraManager start (CC:7239-7242).
- **For the port.** For dual, these writes must be bound to each Core's own sensor.

### K2 · CONFIRMED · KB architecture/drivers.md:112 and r4 Q4 'cam0' bullet vs r5 l.19 and interpretation row 5

- **Claim.** KB/r4: the cam0 override leaves reg_frag on cam1_reg, so the 300 ms delay lands there (in dual, cam1_reg gets it from both overlays). r5: on this CM5, cam1_reg and cam0_reg are one node.
- **Evidence.** imx585-overlay.dts:36-39@cd548ef: 'reg_frag: fragment@4 {' / 'target = <&cam1_reg>;' / 'startup-delay-us = <300000>;'. Lines 129-135 retarget only reg_alwayson_frag and vana-supply. r5:19: __symbols__/cam1_reg points to /cam0_reg.
- **Correction.** The overlay reading is right, but on this CM5 both labels are one regulator (GPIO 34), so the delay and the power are shared and the possible bug does not apply. Mark drivers.md:112 'not applicable on the CM5 rig'.
- **For the port.** Both sensors power up and down together. One Core cannot power-cycle its sensor alone.

### K3 · CONFIRMED · KB architecture/config.md:91 vs r3 'Read these four first' item 1

- **Claim.** KB: hdmi_external_only defaults to false. r3: it defaults to true, so the HDMI picture comes from ExternalMonitorWindow.
- **Evidence.** src/DisplayConfigBridge.cpp:294@c153c33: 'm_hdmiExternalOnly = true;'. :354-357: readConfigBool(... 'hdmi_external_only' ...) with fallback 'true);'.
- **Correction.** The default is true (DisplayConfigBridge.cpp:294, 354-357@c153c33). KB hardware-log.md:995 already says the HDMI picture comes from the external-monitor window.
- **For the port.** Dual preview panes go into ExternalMonitorWindow first.

### K4 · CONFIRMED · KB llm/README.md:128 (trap 13) and llm/ui-map.md:469, 473, 578 vs r3 'Read these four first' item 4

- **Claim.** KB: the UI sends set_fps and set_resolution by itself (ensureValid*Selection). r3: both functions return at once when a control bridge exists.
- **Evidence.** qml/CameraPage.qml:1485-1486@c153c33: 'if (root.controlBridge)' / 'return'. Lines 1668-1669 do the same in ensureValidFpsSelection.
- **Correction.** Trap 13 is stale on drop-frames. With a control bridge, which the rig always has, neither function sends anything.
- **For the port.** A cam1 control bridge will not send automatic set_fps or set_resolution. Mode mirroring has to come from the relay.

### K5 · CONFIRMED · KB architecture/build.md:96 vs r2 'Corrections' l.8 and r5 l.28

- **Claim.** KB: the Core drop-in sets LimitNICE=-5. r2/r5: it also sets LimitRTPRIO=80.
- **Evidence.** config/apertar-core-capture-priority.conf:3@31d5418: 'LimitNICE=-5'. :7: 'LimitRTPRIO=80'. r5:28: systemctl cat shows both.
- **Correction.** The drop-in sets LimitNICE=-5 and LimitRTPRIO=80 (lines 3 and 7).
- **For the port.** A cam1 unit must copy both limits, and LIBCAMERA_LOG_LEVELS, to get the same capture priority.

### K6 · CONFIRMED · KB llm/ui-map.md:465 vs r3 Q1 'Preview client path'

- **Claim.** KB: the socket path defaults to /tmp/apertar-core.sock and APERTAR_CONTROL_SOCKET overrides it. r3: the preview client ignores that variable.
- **Evidence.** src/ApertarPreviewSocketClient.hpp:31@c153c33: 'Q_INVOKABLE bool connectToCore(const QString &socketPath = QStringLiteral("/tmp/apertar-core.sock"));'. The variable is read only at ApertarControlBridge.cpp:1168 and :1805 among these files.
- **Correction.** The override reaches only the control/event, media, audio and system bridges. The preview socket path is the connectToCore argument.
- **For the port.** Pointing the UI at cam1 through the env variable alone would pair cam1's controls with cam0's preview.

### K7 · CONFIRMED · KB llm/core-map.md:15, :154 and llm/ui-map.md:133 vs r3 'Refs'

- **Claim.** The KB maps give ApertarCoreApp.cpp 11025 lines, WebControlPage.cpp 11618 and CameraPage.qml 4160 (upstream-1.6.0). r3: 14628, 20539 and 4349 on drop-frames.
- **Evidence.** wc -l: 31d5418:src/ApertarCoreApp.cpp = 14628; src/web/WebControlPage.cpp = 20539; c153c33:qml/CameraPage.qml = 4349.
- **Correction.** Both maps carry upstream-1.6.0 line numbers. On drop-frames, use the grep anchors (the maps already say so) or re-map them.
- **For the port.** Dual work cites drop-frames lines, and the maps' line numbers will mislead.

### K8 · CONFIRMED · KB architecture/drivers.md:122, :124 and architecture/core.md:360 vs r2 Q2

- **Claim.** KB: detectSensorFamily matches imx577, imx477, imx294 and imx585, and the first non-USB camera is picked at CameraController.cpp:5304-5307. r2: it also matches imx283, and the camera is picked at CC:7262-7265.
- **Evidence.** CameraController.cpp:2560-2561@31d5418: 'if (lower.find("imx283") != std::string::npos)' / 'return SensorFamily::Imx283;'. :7262: 'auto selected = std::find_if(cameras.begin(), cameras.end(), [](const auto &camera) {'.
- **Correction.** Add imx283 (CC:2547-2565@31d5418). The camera is picked at CC:7262-7265 and the probe's camera at CC:7063-7066.
- **For the port.** These two pick sites are where a --camera id filter goes (r2 Q2).

### New findings

1. **r2 and r4 say Core's WDR and HDR writes go to 'the first imx585 subdev', and r2 calls it cam0's sensor. 'First' here means first in unsorted readdir order of /sys/class/video4linux, not port order. The driver also grabs WDR while streaming. So a Core whose first-listed imx585 subdev belongs to the other, streaming camera cannot start, because the WDR write fails with EBUSY. If that camera is between streams, the write flips its Clear HDR instead.** Evidence: CameraController.cpp:6878@31d5418: 'for (const auto &entry : std::filesystem::directory_iterator("/sys/class/video4linux", ec)) {'. imx585.c:4209@cd548ef: '__v4l2_ctrl_grab(imx585->hdr_mode, true);'. setSensorWideDynamicRange gives up after 4 tries (CC:6938-6951), and then start() returns false (CC:7239-7240). For the port: Binding these writes by of_node (the pattern at CC:8118-8130) is a precondition for running two Cores, not a cleanup. Until it is done, readdir order decides which Core fails to start.
2. **r2's 'half a period at 24 fps in about 130 frames' is optimistic. I ran FramePhaseLock's control law (kp 0.06, ki 0.0015, clamp 150 us, deadband 6 us) against an ideal sensor with a 2-8 frame push delay. Starting about half a frame off, the error first crosses zero after about 134-146 frames. It then overshoots by about 1.7-2.3 ms because of integral windup, and stays within ±12 us only after about 250-350 frames (10-14 s).** Evidence: FramePhaseLock.hpp:120 and :122@31d5418: 'const double windup = tuning.clampUs / std::max(tuning.integral, 1e-9);' / 'requestedUs = nominalUs - (tuning.proportional * errorUs + tuning.integral * integralUs);'. Windup = 100000 us·frame, which equals 150 us of request. This is an in-memory Python estimate (no files written) and ignores the HMAX lattice effects of X9. For the port: Allow about 15 s of locking in preview before a synced take, and gate record_start on a small error. Consider clearing the integral at the first zero-crossing during the large initial pull-in.
3. **A shared grid needs no relay message. Both Cores measure SensorTimestamp on CLOCK_BOOTTIME, so if each snaps its datum to a multiple of the period counted from the BOOTTIME epoch, both land on the same grid. Today arm() sets the datum to the process's own first frame.** Evidence: FramePhaseLock.hpp:149@31d5418: 'originNs = referenceNs;'. control_ids_core.yaml:785-786@6b0b49f3: 'since the system boot time, as defined by the' / 'Linux-specific CLOCK_BOOTTIME clock id.' CC:8775 reads SensorTimestamp. For the port: This is a small change in arm(), and both Cores must use the same fps. The (originNs, fps) that r2 has the primary publish then becomes optional. Re-arms (on an fps change at :95, or in preview when the error exceeds half a frame at :110-117) must snap the same way.
4. **Each Core blocks reconfigure-type changes only during its own take. A secondary that is not recording can still restart its CameraManager while the primary records, which triggers the sensor writes in X7.** Evidence: CameraController.cpp:10518@31d5418: 'setErrorLocked("Resolution changes are blocked while recording.");'. The same pattern is at :11196 and :11493, and the recording flag is per process. For the port: With a cam0-only record policy, relayed mode changes and the secondary's own WebUI mode changes must also be refused while either camera records.
5. **The Pi's recent tests ran buffer=ram, while frames is the code default (both r2 and r4 are right). The [storage] buffer setting lives in the hardware conf, so a secondary with its own file runs frames unless that file says otherwise.** Evidence: hardware-log.md:910 records buffer=ram. ApertarCoreApp.cpp:267@31d5418 calls parseBufferConf(hardware::configStore().currentText()). BufferBudget.hpp:296: 'return conf.ram.value_or(false) ? "ram" : "frames";'. Line 33 caps ram mode at 0.5 of MemTotal per process. For the port: Keep the secondary on frames. Two ram queues could each budget up to half of the CM5's 4 GB.

Checker's note: I read all five reports and the KB pages, then checked each disagreement in code at the given refs with git show and git grep. I did not ssh anywhere, wrote no files and used no web access; the only computation was one in-memory Python run for new finding 2. Highest impact for the two-Core plan: (1) X9: the existing phase lock made the picture flicker and dropped frames on the Pi's libcamera (KB-confirmed, still applicable), and no report mentions it. (2) X7 plus new finding 1: each Core's CameraManager starts write to the other camera's sensor, and Core's WDR writes hit the first imx585 subdev readdir returns. (3) X11: XDG_CONFIG_HOME cannot split camera_settings.conf without also splitting UI.conf. (4) X3: equal link frequencies are the dual rule, and the cam1 line must name 891 because the overlay default is 720. UNVERIFIED here: the kernel facts (two PiSP BE node groups; the D-PHY 1500 Mbps table, known only from KB notes that cite kernel dphy.c); that the Waveshare board needs no jumpers (web only); Cinemate's claim that kernels before 6.12.93 corrupt 16-bit CSI capture (docs/raspberry-pi-models.md:7@d6cc93e) against the Pi's 6.12.75; and r1's 'stock libcamera lacks FrameWallClock' (no upstream ref on this Mac; Apertar's libcamera has it at control_ids_core.yaml:1269@6b0b49f3, and FramePhaseLock does not use it). r4 cites fork lines (libcamera 6b0b49f3, driver e5b74d3) while the Pi runs 7e9fef0b and cd548ef. The libcamera files cited outside pisp/ are identical at 7e9fef0b; there the PiSP match starts at pisp.cpp:969. On the Pi's driver, flips and WDR are grabbed at imx585.c:4207-4209 and HBLANK becomes HMAX at :3525-3540.
