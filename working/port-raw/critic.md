# critic — completeness gaps from workflow wf_10785596-249 (2026-10-26)

Written by the workflow's completeness critic after all six reader reports were verified. Each item: question, where to look, why it matters, with the critic's own status word. Folded into the answers/tutorials where marked in `working/clearhdr-compare-notes.md`.


## X1. Is the 'patch against f60e301' the seven uncompiled commits already on clearhdr-fixes (2f5a880, ce723fd, 9e06ad6, bb85899, 4ea877c, d405e22, 90e2415 = HEAD), and have all line numbers stamped 2715569/2a6f114/6853891 (dangling, on no branch) been re-anchored to 90e2415?

- **Where:** git -C apertar-core log --oneline f60e301..HEAD; git branch -a --contains 2715569 (empty); apertar-kb/working/patches/README.md:1-20; T28 tutorial line 11 ('Core 2715569')
- **Why:** All three features are already committed but 'not compiled here'; the verifiers and T28 cite commits that no longer sit on any branch, so every cited line must be re-derived before the tutorials are trusted. CONFIRMED.


## X2. Which commit do each tutorial's line numbers belong to? T27 cites CC:7147/:7263 and CC:7147-7181, T28 cites App:11047 for the always-broadcast list; at 90e2415 stepFramePhaseLock is CameraController.cpp:7170-7205, the pin :7279-7291, the broadcast list ApertarCoreApp.cpp:11100-11116.

- **Where:** apertar-kb/llm/tutoring.md:103-106; T27 §4 line 132; T28 §4.5 line 117; apertar-core/src/camera/CameraController.cpp:7170,:7286,:7359@90e2415; apertar-core/src/ApertarCoreApp.cpp:11100-11116@90e2415
- **Why:** Each later commit shifts the earlier files; a reader on HEAD finds mismatched anchors unless the tutorials name their commit or cite function names. CONFIRMED.


## X3. What is the per-commit build order on the Pi (git am stop points T23→T24→T25→T27→T28→T29→T30) given CameraController.cpp is touched by five of seven commits and cannot be compiled off the Pi?

- **Where:** apertar-kb/working/patches/README.md (table and last paragraph); apertar-core/README.md:206-207@f60e301; apertar-kb/working/build-deploy.md:10-11
- **Why:** The user asked for step-by-step build-and-test; HEAD validates 1,956 inserted lines in one build unless the reader checks out f60e301 and applies one patch per tutorial. CONFIRMED.


## X4. Which user does apertar-core.service run as, what is its ExecStart, and does `systemctl set-environment` reach it? The sudoers snippet hard-codes `pi`; the unit is in no local repo.

- **Where:** apertar-core/config/apertar-media.sudoers:3@90e2415; apertar-core/scripts/start-apertar-core.sh:4-21@90e2415; apertar-core/config/apertar-core-capture-priority.conf:1-3; apertar-core/README.md:229-245@f60e301; apertar-kb/working/build-deploy.md:10; on the Pi: systemctl cat apertar-core
- **Why:** T29's root helper and T27/T29's env-var A/B both depend on it; a wrong user makes `sudo -n` fail silently as 'tuning helper failed'. UNKNOWN.


## X5. Where do the host tests run and with what exact g++ line, given Core's CMakeLists has no enable_testing/add_test and the simulators live in apertar-kb/working/tools (phase_lock_sim.cpp, media_probe_test.cpp, media_profile_test.cpp)?

- **Where:** apertar-core/CMakeLists.txt:69-134@f60e301; apertar-kb/working/tools/; T27 line 55 (the one g++ line present); cinepi-raw/tests/phase_lock_core_test.cpp:46-56@63a08d5 (sensor model worth copying)
- **Why:** T28/T29 reference their test tools without a compile line; Cinemate's 4624-check test suite with a sensor model is the reference the port lacks. CONFIRMED.


## X6. Do all writers of settings_ (CC:3441, :5869, :6003, :6150, :6924, :8328-8331, :8367-8369, :8433) hold controlsMutex_, which stepFramePhaseLock (:7180-7184) and the pin (:7286-7289) rely on? Only applyControls (:6150) was confirmed.

- **Where:** apertar-core/src/camera/CameraController.cpp:3441,:5869,:6003,:6150,:6924,:8328,:8367,:8433,:7180-7184,:7286-7289@90e2415; p2 brief 'Still open after verification'
- **Why:** The servo reads fps/photoModeEnabled/fpsPhaseLock on the completion thread; an unlocked writer in reconfigure is a data race the patch author must audit or replace with atomics. PROBABLE.


## P1. Which libcamera does the Pi binary run: the qbc getBlanking lattice (4cff971, where a ±1 µs push is a no-op at 41666↔41667 and each real push re-chooses HMAX, changing rolling-shutter skew up to 8 %) or the default helper (±1 µs = one VBLANK line)?

- **Where:** libcamera(qbc)/src/ipa/rpi/cam_helper/cam_helper_imx585.cpp:130,:135,:162-165,:185-207,:219-223@7e9fef0; libcamera(cinemate)/src/ipa/rpi/cam_helper/cam_helper.cpp:96-97@bfe0b76; T27 lines 100-111, 152-159; apertar-kb/working/tools/phase_lock_sim.cpp; apertar-core/README.md:186,199@f60e301
- **Why:** T27 §5's predictions (req_us 39990..40010, pushes≈frames/4, max_abs_err≤20) come from the idealised simulator and hold in neither regime as written; the hblank readback in §3.3 is the deciding step. PROBABLE.


## P2. What do 39999 and 40001 µs (and 33332-33334, 16665-16667) become under the qbc lattice search? Only 41664-41669 (24 fps) was simulated, yet 25 fps is the tutorial's primary test and 40000 is exact (HMAX 550 × VMAX 5400).

- **Where:** p2 brief §Verification added item D; libcamera(qbc)/src/ipa/rpi/cam_helper/cam_helper_imx585.cpp:185-207@7e9fef0; imx585-apertar/imx585.c:1663,:1684-1685@98b9862 (VMAX rounds down to even, HMAX floor)
- **Why:** The expected dur_us/HBLANK trace at 25 fps cannot be written down without running the same model on the ±1-2 µs neighbours. PROBABLE gap.


## P3. What is the IMX585-vs-Pi crystal offset (sign and ppm) on the rig, and how is a fast sensor measured? T27 §3.2 infers only the slow case from nextFrameIndex holes.

- **Where:** apertar-core/src/camera/CameraController.cpp:7381-7382@90e2415 (SensorTimestamp/FrameDuration reads); :7520-7565@f60e301 (trackRecordingCadence); apertar-kb/working/tools/ipa_rate.py; T27 lines 81-96
- **Why:** A fast sensor produces no holes and shows only as end-of-take A/V offset; the lock's target number is unknown until SensorTimestamp deltas over N frames are logged directly. CONFIRMED missing.


## P4. What is the control-loop delay at HEAD (one request per raw buffer: kClearHdrBufferCount=8, kConfiguredBufferCount=4, +2 from the profile → ~11 frames in Clear HDR, like cinepi-raw's --buffer-count 8), and how are kp/ki re-tuned on the Pi when the Tuning struct has no env or setting override?

- **Where:** apertar-core/src/camera/CameraController.cpp:1055,:1059,:1173-1181@90e2415; apertar-core/src/camera/FramePhaseLock.hpp:26-31@90e2415; p1 brief §Verification A2; cinemate/src/module/cinepi_multi.py:845-847@d6cc93e
- **Why:** p1's '3 in flight / 5-6 frames' estimate is stale at HEAD; every gain trial now costs a rebuild unless APERTAR_PHASE_LOCK_KP/KI are added. PROBABLE numbers, CONFIRMED missing knob.


## P5. How is saturation at a mode's maximum fps detected? HEAD never reads the IPA-validated FrameDurationLimits echo (the only metadata read of it is the mode probe at :5796) and the 'saturated' log line is deferred to 'going further'.

- **Where:** libcamera(qbc)/src/ipa/rpi/common/ipa_base.cpp:1788-1796@7e9fef0 (clamp + echo); apertar-core/src/camera/CameraController.cpp:5796,:7381-7382@90e2415; :2843-2844@f60e301 (fps clamp); T27 line 207
- **Why:** At the fastest fps the pin equals the IPA minimum, the servo can only lengthen frames, and the clamp hides the failure; the port needs the per-frame echo and a once-per-clip log. CONFIRMED missing.


## P6. Where do the WebUI toggle and the phase-error telemetry go? WebControlPage.cpp has zero hits for fps_phase_lock; state carries only the boolean (App:7917); error/duration reach only stderr.

- **Where:** apertar-core/src/web/WebControlPage.cpp:10610@f60e301 ('cameraFps' key list); apertar-core/src/ApertarCoreApp.cpp:6674,:7852-7854@f60e301; :7917,:9692@90e2415; cinepi-raw/cinepi/cinepi_controller.cpp:1257-1258@63a08d5
- **Why:** Cinemate at least publishes pll_phase_err_us/pll_req_dur_us; the patch author needs the three plumbing points (web key list, addString beside cameraFps, status field beside recording_has_dropped_frames). CONFIRMED missing.


## P7. What settling time should the tutorial expect? Cinemate's test skips 1000 frames (~42 s at 24 fps) before bounding |err|<300 µs and 2000 before averaging; T27 §5.1 predicts err_us ±15 after 20 s with no source.

- **Where:** cinepi-raw/tests/phase_lock_core_test.cpp:182,:189@63a08d5; T27 lines 152-157; cinepi-raw commit 55562b6 body
- **Why:** The prediction should come from the simulator run on the measured offset (P3), not a guess; a wrong window makes a correct lock look failed. CONFIRMED (test) / UNKNOWN (rig).


## P8. What ALSA period does the rig's audio device negotiate? p1's '~5.3 ms' tolerance implied a 1024-frame period on Cinemate's device; 90e2415 now logs buffer_frames/period_frames at open.

- **Where:** apertar-core/src/audio/TimestampedAudioCapture.cpp:195-218@90e2415; cinepi-raw/cinepi/cinepi_audio_capture.cpp:510-513,:606,:611@63a08d5
- **Why:** The value falls out of T30's first run and belongs in the phase-lock tutorial's audio paragraph. UNKNOWN value, CONFIRMED mechanism.


## P9. Are Cinemate's three design rationales carried into T27 §2: pure-integral control railed the clamp (85d0326), a reconfigure stall is not an integer number of frames so preview re-arms instead of absorbing (3b3ff60), and the lock runs in preview so recording starts locked (d038556)?

- **Where:** git -C cinepi-raw show 85d0326 3b3ff60 d038556 --stat; cinepi-raw/cinepi/phase_lock_core.hpp:96-97,:113-118,:130-139@63a08d5; T27 lines 100-111
- **Why:** T27 cites 3b3ff60/4537153 only; without the 'why' a reader may simplify the gap rules away and reintroduce the 90-169 ms start-behind bug. CONFIRMED.


## Y1. Does statvfs on the mount root actually fail after a pull on ext4/exFAT? ext4_statfs reads in-memory per-cpu counters with no forced_shutdown check (returns 0); exfat_statfs/fat_statfs do I/O only on the first uncached call; fs_bdev_mark_dead leaves the root dentry pinned.

- **Where:** kernel-rpi/fs/ext4/super.c:6834-6867@5bd564a (git show HEAD:; counters :6849-6850, return 0 :6867); kernel-rpi/fs/exfat/super.c:72-87@5bd564a; kernel-rpi/fs/fat/inode.c:834-848@5bd564a; kernel-rpi/fs/super.c:1419-1435@5bd564a; apertar-core/src/util/MediaProbe.hpp:13-18,:108-131@90e2415; apertar-core/src/ApertarCoreApp.cpp:9190-9203@90e2415; T28 lines 14, 68-74, 152; cinemate/services/storage-automount/storage-automount.py:835-864@d6cc93e
- **Why:** Both Cinemate's watchdog and HEAD's MediaProbe assume 'statvfs then fails with EIO/ENODEV'; if it does not, MediaSnapshot never leaves Mounted, the watcher's 'lost' never fires, only the writer's EIO stops the take, and the gate then lets the next take start onto the dead mount (ENOTCONN is the FUSE case, ENOENT only after umount -l). PROBABLE; T28 §5.2 prediction 1 must allow both outcomes.


## Y2. On FAT32 media, which writer notices the pull at all? fat_sops has no .shutdown and fs/fat/file.c has no shutdown check, so buffered write() (MLV, H.264, audio) keeps succeeding into the page cache; only O_DIRECT cDNG fails at once. ext4 and exFAT do return -EIO.

- **Where:** kernel-rpi/fs/fat/inode.c:935@5bd564a (fat_sops); kernel-rpi/fs/ext4/file.c:134,:156,:695,:794@5bd564a; kernel-rpi/fs/exfat/file.c:692@5bd564a; apertar-core/src/ApertarCoreApp.cpp:3822@f60e301 (vfat mkfs offered); apertar-core/src/cdng/CdngEncoder.cpp:1808-1815@90e2415
- **Why:** Core offers FAT32 formatting; the yank tutorial needs a 'which filesystem are you on' step before any prediction. CONFIRMED (source), PROBABLE (Pi).


## Y3. How long does a CFE/NVMe pull take to reach the first EIO on this Pi? NVMe namespaces are marked dead only after nvme_timeout (io_timeout 30 s) and a failed reset; pcie-brcmstb checks link-up only at probe/resume; USB (sd_remove→del_gendisk) is immediate. HEAD has no /sys/block/<nvme>/device/state or I2C-latch poll.

- **Where:** kernel-rpi/drivers/nvme/host/core.c:52,:4985-4995@5bd564a; kernel-rpi/drivers/nvme/host/pci.c:1419,:1488,:1549-1553@5bd564a; kernel-rpi/drivers/pci/controller/pcie-brcmstb.c:899-941,:1806-1810,:2002,:2553@5bd564a; kernel-rpi/drivers/scsi/sd.c:4084@5bd564a; kernel-rpi/block/genhd.c:587,:651,:684@5bd564a; cinemate/services/storage-automount/storage-automount.py:813-833,:925-1105@d6cc93e; apertar-core/src/ApertarCoreApp.cpp:9161-9162,:9208@90e2415; T28 line 191
- **Why:** Cinemate added a 0.5 s NVMe state==dead watchdog and a 0.05 s latch poll precisely for this; without them writers can block 30-60 s and T28's troubleshooting covers only USB. PROBABLE (mechanism CONFIRMED, Pi timing UNKNOWN).


## Y4. Who unmounts the dead mount and rescans PCIe after a pull? Core is unprivileged with no umount sudoers rule, so the dead entry stays in /proc/mounts, media_mounted (isMountedPath, App:7705) stays true, mount_media refuses, and a reinserted CFE card needs the UI automounter's unbind/bind (CfeAutomounter.cpp:632-648 per KB) that reacts to the hat edge, not to Core's media event.

- **Where:** apertar-core/src/ApertarCoreApp.cpp:7705,:9314@90e2415; :10663-10673@f60e301; apertar-core/src/util/MediaIntent.hpp:15-30@90e2415; apertar-kb/architecture/ui.md:398-410; apertar-kb/architecture/core.md:493-496; apertar-kb/llm/change-recipes.md:26; T28 line 204
- **Why:** Whether apertar-cfe-automounter honours /run/apertar-media/eject/<dev> or runs umount -l on surprise removal is unknown (Apertar-UI not local); T28 lists it as future work. UNKNOWN.


## Y5. After a yank, media_mounted (still isMountedPath) and media_state (watcher) disagree; the WebUI's hasMedia and the record button's disabled rule follow media_mounted, so the button stays enabled and only the gate's toast appears. Is that intended?

- **Where:** apertar-core/src/ApertarCoreApp.cpp:7705,:7936-7942@90e2415; apertar-core/src/web/WebControlPage.cpp:9390,:9523,:9837-9838@90e2415
- **Why:** T20/T28 prediction 5.1 holds after an eject (unmounted) but not after a pull; the WebUI should gate on media_alive or media_state. CONFIRMED.


## Y6. Is the 'recording' event still swallowed into a command reply (KB #36)? HEAD's always-broadcast list has media/recording_health/settings but not recording; the watcher's stop runs under commandMutex_ and lands in another requester's reply if one is being collected.

- **Where:** apertar-core/src/ApertarCoreApp.cpp:11100-11116,:7092-7103,:9197-9201@90e2415
- **Why:** The HDMI process consumes events and can miss the stop; the fix is one line in the list. CONFIRMED.


## Y7. Why were gyro and ProRes left out of 4ea877c? gyroRecorder_.stop() (:6319) exports the sidecar with no stream-state check and logs 'exported' regardless; proresRecorder_.stop() (:6324) has no mediumDead flag while ProresEncoder fsyncs its sidecar.

- **Where:** apertar-core/src/camera/CameraController.cpp:6319,:6324@90e2415; apertar-core/src/hardware/Mpu6050RecordingSession.cpp:2234,:2275,:2277@90e2415; apertar-core/src/prores/ProresRecorder.cpp:139@90e2415; apertar-core/src/prores/ProresEncoder.cpp:1247-1281@f60e301; git diff --stat f60e301..HEAD (no src/hardware, src/prores)
- **Why:** Both can hang or lie on a dead mount, contradicting the commit's 'nothing touches the medium again'. CONFIRMED.


## Y8. Why do blocking probes run off the watcher thread? mediaExtraRawBuffersForConfiguredRoot() calls statvfs inside rawCameraBufferCount() at configure, CameraSession::startRecording probes again under the controller mutex (:6273), and mediaSnapshot() falls back to a direct probe before the first cycle, against MediaProbe.hpp's own 30 s+ warning.

- **Where:** apertar-core/src/util/MediaProfile.hpp:206-215@90e2415; apertar-core/src/camera/CameraController.cpp:1178,:6273,:8356@90e2415; apertar-core/src/ApertarCoreApp.cpp:9224-9233@90e2415; apertar-core/src/util/MediaProbe.hpp:133-145@90e2415
- **Why:** On T28's row-191 case (hung, not removed) configure and record_start would freeze every command. CONFIRMED.


## Y9. What errno sequence do Core's writers actually see on a pulled USB vs NVMe vs CFE device, direct vs buffered? No repo holds a log of a pull during a take; MediaFault's Removed set is Cinemate's guess plus ENXIO/ENOMEDIUM, and ENOENT is only right after an unmount.

- **Where:** apertar-core/src/util/MediaFault.hpp:24-48@90e2415; apertar-core/src/camera/CameraController.cpp:3970-3973,:4076-4079@90e2415 (fault= errno= logged); cinemate-handbook/lessons/hardware-log.md (grep yank|surprise removal|hot-?unplug: none); cinemate commit 3259da7 body ('Live Pi verification pending')
- **Why:** T28 §3 asks the reader to write it down; until then the class table is unverified. UNKNOWN.


## Y10. Is hat bit0 = 1 'latch open / card out' as Cinemate reads it, and which of Core's embedded reinsert watcher (default_state=True, waits True then False) and the UI automounter (same edge, no /run/apertar-cfe/ready skip in Core) mounts first?

- **Where:** apertar-core/src/ApertarCoreApp.cpp:3493-3504,:3582-3599@f60e301; cinemate/services/storage-automount/storage-automount.py:999-1001,:1026-1027@d6cc93e; apertar-kb/architecture/core.md:493-496; apertar-kb/architecture/ui.md:402-408
- **Why:** T28 reinsert predictions depend on it; measure with i2ctransfer with the card in and out. UNKNOWN (polarity), CONFIRMED (race).


## Y11. Should the record gate's free-space floor be per format? APERTAR_MEDIA_MIN_FREE_MB defaults to 256 MiB, under one second of 16-bit 4K at 25 fps (~415 MB/s payload); the bytes/s model under-estimates 16-bit by ≥19 %.

- **Where:** apertar-core/src/ApertarCoreApp.cpp:9253-9259@90e2415; :4752-4772@f60e301; cinemate/src/module/cinepi_controller.py:2352@d6cc93e (Cinemate's space term is a bound method, always truthy)
- **Why:** A format-blind floor neither protects a 4K take nor matches Cinemate (which has no working space gate). CONFIRMED.


## Y12. Who consumes the eject-intent flag /run/apertar-media/eject/<dev>, and who creates the directory? Nothing in any local repo reads it; the tmpfiles snippet must be installed by hand; T28 §5.3 only checks the flag appears.

- **Where:** apertar-core/src/util/MediaIntent.hpp:15-57@90e2415; apertar-core/config/apertar-media.tmpfiles.conf:3-5@90e2415; T28 lines 127, 161-167, 193, 204; cinemate commit f01b6cd
- **Why:** Until the automounter half exists this is bookkeeping and the tutorial should say so. CONFIRMED.


## Y13. Why does Cinemate not stop a take on media loss? unmount_event has no subscriber; the take ends only by operator, the 90 %/80 % watchdog or pool exhaustion; 3259da7's 'recording can continue' means the next take on a promoted standby.

- **Where:** cinemate/src/module/ssd_monitor.py:133,:431@d6cc93e; cinemate/src/module/cinepi_controller.py:4279-4327@d6cc93e; cinemate commit 3259da7 body lines 9-10; y1 brief §1.4-1.5
- **Why:** Core deliberately diverges (stop at once); the investigation answer should present that as a choice with the evidence, not as a port. CONFIRMED absence.


## Y14. What does the T18 workbook actually say (Step 0 paths, Step 5 /usr/local/libexec install) that T28 claims to supersede?

- **Where:** apertar-kb/llm/tutoring.md:94,:96; apertar-kb/tutorials/README.md:107,:109
- **Why:** Only index rows exist locally; T28 cannot quote what it replaces. UNKNOWN.


## S1. What filesystem and transport is the rig's /media/RAW, and does exFAT on this kernel accept O_DIRECT at open and at write (ce723fd falls back on EINVAL at either point)? T28 predicts fstype=exfat; T29 §3.1 reads findmnt first.

- **Where:** T29 lines 58-62; T28 line 133; apertar-core/src/cdng/CdngEncoder.cpp:1808-1815,:1860-1864@90e2415; apertar-core/src/util/MediaProfile.hpp:152-164@90e2415; cinemate-handbook/lessons/hardware-log.md:967,:1068,:3098-3101@c99ff77
- **Why:** The whole writer table and the yank predictions branch on it; the handbook's only NVMe runs are PROBABLE exFAT and PROBABLE fuseblk for NTFS. UNKNOWN.


## S2. Does /etc/sysctl.d/60-apertar-writeback.conf exist on the image with vm.dirty_bytes 128 MB, as Core's own ProresEncoder comment asserts? T29 line 72 predicts kernel defaults (dirty_ratio 20, dirty_bytes 0).

- **Where:** apertar-core/src/prores/ProresEncoder.cpp:326-329,:402@f60e301; apertar-core/scripts/apertar-media-tune:48-53,:79-82,:94-101@90e2415; T29 lines 62, 72, 176
- **Why:** The helper's save_once would preserve 128 MB and restore returns to it, which is right, but the tutorial's prediction and its 'reboot restores defaults' note are wrong if the file exists. PROBABLE (file), UNKNOWN (contents).


## S3. What measured rationale backs the writer table? Cinemate's 8/2 disk workers come from an empty-bodied commit (2a49fa1); Core's 4/2, queue 12/16, +2 buffers are 'starting points'; the only measured storage numbers are NTFS-over-FUSE 264/355 MB/s and an unstated-media 317-334 MB/s table.

- **Where:** cinemate/src/module/storage_profiles.py:50-95@d6cc93e; git -C cinemate show 2a49fa1:src/module/storage_profiles.py; cinemate-handbook/lessons/hardware-log.md:964-978@c99ff77; cinemate-handbook/docs/settings-json.md:329-338@c99ff77; apertar-core/src/ApertarCoreApp.cpp:4752-4772@f60e301
- **Why:** T29 §5.2's decision rule is sound, but the tutorial lacks the expected payload rate of the rig's mode (16-bit 4K 25 fps ≈ 415 MB/s; the clip model says 336) to judge headroom per medium. CONFIRMED absence.


## S4. What does Cinemate's 2 s pre-roll at max fps physically warm? No source or handbook entry says; origin commit e577437 has an empty body; T29 §5.3 can only A/B take A vs take B after a remount.

- **Where:** cinemate/src/module/storage_preroll.py:1-6,:195-303@d6cc93e; git -C cinemate show e577437; T29 line 146; apertar-kb/working/tools/writeback_watch.py
- **Why:** If A is worse the port has no model to design from (page cache, FAT allocator, SLC cache); the tutorial should also log nr_dirty and the first second's peak_queue. UNKNOWN.


## S5. Does the image already set nvme_core.default_ps_max_latency_us, and should the helper write it? Cinemate's table sets it to 0 for NVMe classes; apertar-media-tune has no nvme_core line.

- **Where:** cinemate/services/storage-automount/storage-automount.py:328-333@d6cc93e; apertar-core/scripts/apertar-media-tune:67-92@90e2415; T29 lines 58-62; on the Pi: cat /sys/module/nvme_core/parameters/default_ps_max_latency_us and /boot/firmware/cmdline.txt
- **Why:** APST exit latency is one of Cinemate's NVMe knobs and is absent from Core's port without a stated reason. UNKNOWN.


## S6. Is the omission of RT priority/affinity deferred or rejected? Cinemate runs chrt -f 70, ionice -c2 -n0, taskset -c 1-3, isolates core 3 for audio (isolcpus/nohz_full/rcu_nocbs/irqaffinity=0-2) and learned disk affinity on the audio core corrupted timecode; Core has LimitNICE=-5, setpriority(-5) on the callback thread, worker nice, no affinity, unknown unit.

- **Where:** cinemate/src/module/cinepi_multi.py:294-313@d6cc93e; cinemate/src/module/storage_profiles.py:41-49@d6cc93e; cinemate/cinemate-install.sh:1257-1281@d6cc93e; apertar-core/src/camera/CameraController.cpp:3917,:7320@90e2415; apertar-core/config/apertar-core-capture-priority.conf:1-3
- **Why:** The storage answer should say which, and the tutorial should print the unit's CPUAffinity/Nice. CONFIRMED absence.


## S7. Does takes.sh see the counters the ports add? It greps enqueued=, dropped_queue_full=, dropped_gap_estimate=, peak_queue= only; write_failures=, discarded_on_failure=, skipped_after_failure=, fault=, media_class=, direct_io= and the phase-lock stats line are invisible, and the stats line prints only when a counter is non-zero.

- **Where:** apertar-kb/working/tools/takes.sh:14-15; apertar-core/src/camera/CameraController.cpp:3533-3540,:3605-3620,:6312-6315@90e2415; :3523-3532@f60e301
- **Why:** The pass criteria in T27/T28/T29 ('write_failures=0', 'max_abs_err ≤ 20') are unmeasured until the script grows those tokens. CONFIRMED.


## S8. What happens when the medium changes after Core has configured the camera? rawCameraBufferCount adds the profile's extra buffers at configure; the watcher logs a new profile but never triggers a reconfigure; Cinemate restarts cinepi-raw on mount_event, deferred while recording.

- **Where:** apertar-core/src/camera/CameraController.cpp:1173-1181@90e2415; apertar-core/src/ApertarCoreApp.cpp:9174-9190@90e2415; cinemate/src/module/cinepi_controller.py:2144-2215@d6cc93e; T29 line 132
- **Why:** T29 §5.1's 'count=10 on exFAT' holds only if the exFAT medium was mounted before configure; the port needs a deferred reconfigure or a documented restart. CONFIRMED.


## S9. With what options does the boot mounter mount /media/RAW (media-RAW.service/mount-raw.sh or the UI automounter's mount(2): ntfs3; exfat/vfat uid/gid 1000; ext4 plain per KB)? d405e22's noatime reaches only Core's own mount_media.

- **Where:** apertar-kb/architecture/ui.md:406; apertar-kb/architecture/overview.md:15,:146; apertar-core/src/ApertarCoreApp.cpp:3621-3637@f60e301; T29 line 58
- **Why:** findmnt -no OPTIONS /media/RAW answers it, but the tutorial should say which mounter produced the line and that Core's noatime does not apply to it. UNKNOWN.


## S10. Is fio installed on the image? The dd fallback's timer includes the failed fio attempt and labels MiB as 'MB'; run_media_speed_test is a T29 §6e prerequisite.

- **Where:** apertar-core/src/ApertarCoreApp.cpp:9035-9051,:3911-3924@f60e301; apertar-kb/working/clearhdr-compare-notes.md:85
- **Why:** `which fio` decides whether the speed figure is QD1 fio or dd-with-startup. UNKNOWN.


## S11. Why does the tuning helper (sudo -n subprocess) run synchronously on the watcher thread before flagMediaFault on 'lost'? A sudo prompt, missing sudoers rule or slow sh delays the take's stop by that call.

- **Where:** apertar-core/src/ApertarCoreApp.cpp:9186-9201,:9273-9300@90e2415
- **Why:** Order the abort first or run the helper detached; otherwise the yank latency the tutorial measures includes a sudo round-trip. CONFIRMED.


## S12. What do /sys/class/block/<root>/device realpath and uevent read on each medium the tutorials use? A USB bridge without '/usb' in its realpath lands in MediaClass::Other, mmcblk lands in sd-card (mq-deadline/128), and the CFE-hat evidence (1000110000.pcie ancestry, DRIVER=nvme) is Cinemate's only.

- **Where:** apertar-core/src/util/MediaProfile.hpp:98-113@90e2415; cinemate/services/storage-automount/storage-automount.py:238-266@d6cc93e; cinemate/src/module/ssd_monitor.py:511-543@d6cc93e; T29 lines 72, 169
- **Why:** readlink -f and cat uevent per medium should be pasted into media_profile_test.cpp before trusting the class. UNKNOWN per medium.
