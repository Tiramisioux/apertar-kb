# Inventory: Media-fault-tune (stage 1, no judgement)

Refs: port = `cinemate-port` Core `01f170c`, UI `7ea9afc`; upstream = `upstream-1.6.0`. All claims confirmed (read in code) unless marked.

## 1. Commits and status (fork-log.md lines 41-49, 142-143)

| Commit | What | Recorded status / test |
| --- | --- | --- |
| 438a342 | MediaFault, MediaProbe, MediaIntent headers; writers latch fault; watcher thread; record gate; state fields; WebUI follows media_alive | "desk only (not built yet)" in message; fork-log: built 22:27 with e8bb1b7 |
| e8bb1b7 | MLV abandon moved to MLV worker | build fix |
| 0b1632f | CfeHat.hpp: HAT slot bit read; dead-medium stop bounded (2 s) | message "pi build (see next run)"; fork-log built 22:43. Pull test on Pi 2026-10-26 reported in a3ac8da message |
| a3ac8da | pulled card latched until new mount id; 5 s write stall ends take | fork-log built 22:51; behaviour found on Pi 22:46 |
| 70e8376 | media_state/media_alive in socket get_state | built 22:54 |
| 26da30e | MediaProfile, apertar-media-tune helper, sudoers, tmpfiles, noatime | "built 23:04, not tested"; helper "added but not installed" |
| 0358fcf | exFAT row set back to {4,12,+0}; audio ring 100 ms | measured C0106 vs C0101 |
| ebdcd08 | kernel tuning helper opt-in (APERTAR_MEDIA_TUNE=1) | tested: no helper call after restart |
| 3c4f07d | storage label "Media Removed"/"Media Error" (T20 step 4) | T21 tested |
| 2edc6d0 | MediaTune.hpp + config/apertar-media-tune.conf + README | "desk only (host test 46 checks)"; fork-log: built on Pi, Core not restarted yet |
| 46d0e8c | scripts/apertar-tune | "desk only (py_compile; ...)"; fork-log: on the Pi |
| UI 160898c | UI follows Core media_state | "pi build (see next run)" |
| UI dc471c1 | automounter releases a card pulled while mounted | "pi build (see next run)"; behaviour found on Pi 2026-10-26 |
| 4ce382e, 7d9dd60, 5b68f1f, 441e42a, b606c4f | once-a-second fsync / sync_file_range / audio raw fsync (neighbours; they read the tune file via mediaTuneForConfiguredRoot) | built; pull test C0011, C0013 |

Host test: header of MediaTune.hpp names `tools/media_tune_test.cpp`; the file is not in `Apertar-Core/tools/` (confirmed: `git ls-files tools` has no media_tune_test; upstream has no tools/ at all). unconfirmed whether it lives elsewhere.

## 2. New files (read completely)

| File | Lines | Job |
| --- | --- | --- |
| src/util/MediaFault.hpp | 108 | enum MediaFault {None,Removed,Full,ReadOnly,Permission,Other}; errno -> class; exception -> class; names `media_removed media_full media_read_only media_permission write_error`; operator text |
| src/util/MediaProbe.hpp | 292 | MediaSnapshot (state none/mounted/removed/error), CardPresence, /proc/mounts parse, mountinfo mount id, rootDiskForDevice, pure `evaluateMediaProbe`, syscall `probeMediaRoot`, process-wide cached snapshot (static mutex + optional) |
| src/util/MediaIntent.hpp | 67 | eject-intent flag file `$APERTAR_MEDIA_RUN_DIR/eject/<dev>` (default /run/apertar-media) |
| src/util/CfeHat.hpp | 75 | CfeHatConfig {enabled, bus=10, addr=0x34}; CfeHatReader: SMBus receive byte on /dev/i2c-N, two agreeing reads, 0x69 = unknown |
| src/util/MediaProfile.hpp | 236 | MediaClass (pi-nvme usb-uas usb-storage sd-card other), MediaFilesystem, writer table per fs, MediaProfile, sysfs class detection, `configuredMediaRoot()` global, `mediaExtraRawBuffersForConfiguredRoot`, `mediaTuneForConfiguredRoot`, `loadMediaTuneLogged` (call_once log) |
| src/util/MediaTune.hpp | 318 | INI parser/resolver for base + override file, 8 keys, section order class.fs > fs > class > default, warnings, `summary()`; namespaces `apertar` and `apertar::mediatune` |
| scripts/apertar-media-tune | 112 | POSIX sh root helper `apply|restore <rootdisk> <class> <fs>`: block queue scheduler/nr_requests/rq_affinity, vm.dirty_*, nvme_core default_ps_max_latency_us; saves originals under /run/apertar-media/tune |
| scripts/apertar-tune | 487 | Python 3 CLI `show|set|unset|clear|init`; edits override file atomically; refuses root; validates keys/ranges itself (duplicate of C++ table) |
| config/apertar-media-tune.conf | 54 | template of the base file |
| config/apertar-media.sudoers | 3 | `pi ALL=(root) NOPASSWD: /usr/local/libexec/apertar-media-tune` |
| config/apertar-media.tmpfiles.conf | 5 | /run/apertar-media (pi), /run/apertar-media/eject (pi), /run/apertar-media/tune (root) |
| (neighbour, not in scope) config/apertar-media-trim.sudoers, scripts/apertar-media-trim | - | trim helper, same pattern; README documents install, not so for apertar-media-tune |

Note: there are no `mediafault::`, `mediaprobe::`, `mediaprofile::` namespaces; all of it is flat `apertar::` (only `apertar::mediatune` exists). The use-grep for those prefixes matches nothing.

## 3. Features (operator-visible)

| # | Feature | Commits | Operator gets |
| --- | --- | --- | --- |
| F1 | Dead-medium handling during a take | 438a342 e8bb1b7 0b1632f a3ac8da | A pulled/lost drive ends the take with a named fault instead of a hang; take files up to the pull are kept; record_stop is bounded |
| F2 | Media watcher thread + record gate | 438a342 a3ac8da 3c4f07d | record_start / capture_photo / timelapse_start refused with a reason when media not mounted, pulled, errored, or under 1 GiB free |
| F3 | CFexpress slot bit in the probe | 0b1632f a3ac8da | Pulling the card is seen at once, not after the NVMe I/O timeout; a pulled-and-reinserted card stays "removed" until remount |
| F4 | Eject intent flag | 438a342 | Deliberate eject is not undone by an automounter reacting to udev "change" (written by Core; no reader in this repo or in Apertar-UI, see section 8) |
| F5 | Media profile (class + fs -> writers, queue, extra raw buffers) | 26da30e 0358fcf | Writer count / queue / raw buffers follow the mounted medium; logged per take |
| F6 | Kernel tuning helper (opt-in) | 26da30e ebdcd08 | dirty-page, scheduler, queue depth, NVMe APST per class, apply on mount / restore on loss. Off unless APERTAR_MEDIA_TUNE=1 or kernel_tune=on |
| F7 | Media tuning file + override | 2edc6d0 | ~/apertar-media-tune.conf and /run/apertar-media/media-tune.override.conf replace env drop-ins for write-path knobs |
| F8 | apertar-tune CLI | 46d0e8c | `apertar-tune set workers=4 --section pi-nvme.exfat`, show, unset, clear, init |
| F9 | Touch UI follows Core media state | UI 160898c | MEDIA REMOVED / MEDIA ERROR status, no QStorageInfo call on a dead mount |
| F10 | UI automounter releases a pulled card | UI dc471c1 | After a pull, the automounter lazy-unmounts and removes the PCIe device so the next insert remounts without reboot |
| F11 | WebUI follows media_alive | 438a342 3c4f07d | Status "MEDIA REMOVED"; controls disabled when no media |
| F12 | noatime on Core's own mounts | 26da30e | mount options in embedded python watcher and mountDeviceAtMediaPath |

## 4. Interfaces added or changed

### Socket / HTTP

| Item | Change |
| --- | --- |
| `get_state` (socket) | added `recording_fault`, `media_state`, `media_alive` (App.cpp:12943-12962). `media_state` is emitted twice in the same JSON object (12944 from 438a342/70e8376 and 12961); confirmed by reading |
| state JSON for HTTP `/api/state` (App.cpp:9555-9562) | added `media_state`, `media_alive`, `media_device`, `media_fstype`, `media_class`, `media_profile`, `recording_fault` |
| event `media` (new) | `{"event":"media","state","mounted","device","fstype","free_bytes","total_bytes","errno"}`; sent on every change of state/device/fstype/card/pulled (App.cpp:10824, 10911) |
| `record_start`, `capture_photo`, `timelapse_start` | now refused by `mediaGateError()` in handleCommand (App.cpp:12597-12599); upstream has no gate (grep in upstream: no "No media" refusal at record_start) |
| `eject_media` / `mount_media` | write/clear eject intent (App.cpp:4355, 4389) |
| hardware peripheral card `cfexpress_hat` | `cfeHatPeripheralJson` reads the slot byte for the Hardware page (App.cpp:12084-12125) (belongs to dcf09ee Hardware page unit; uses CfeHatReader) |
| New socket commands | none for this unit. `set_media_trim` is the neighbour trim feature |
| `/api/state` clip line in log | `media_class= media_fs= dontneed= writeback= sync_ms= tune_override=` in the "recording clip:" stderr line (CC:4395-4404) |

### State fields / events

`media_state`, `media_alive`, `media_device`, `media_fstype`, `media_class`, `media_profile`, `recording_fault` (values: "" / media_removed / media_full / media_read_only / media_permission / write_error), event `media`.

### Config keys

| File:[section] key | Notes |
| --- | --- |
| apertar-hardware.conf:[cfexpress_hat] enabled, bus, address | upstream already has this section (upstream App.cpp:3449 in python helper, :4303 template; UI CfeAutomounter.cpp:38). Port adds a C++ reader `loadCfeHatConfig` (App.cpp:5298) read by the watcher; reload via `cfeHatGeneration_` on save |
| ~/apertar-media-tune.conf (base, hardcoded /home/pi/...) | keys dontneed, writeback, sync_ms, raw_buffers, extra_raw_buffers, workers, queue, kernel_tune; sections default, fs, class, class.fs |
| /run/apertar-media/media-tune.override.conf | same format, wins over base |

Precedence stated: env > override > base > code default (conf header, README:339).

### Env vars

| Var | Where | Default | Added by |
| --- | --- | --- | --- |
| APERTAR_MEDIA_RUN_DIR | MediaIntent.hpp, helper script | /run/apertar-media | 438a342 |
| APERTAR_MEDIA_REQUIRE_MOUNT=0 | App.cpp:11365 | gate on | 438a342 |
| APERTAR_MEDIA_MIN_FREE_MB | App.cpp:11379 | 1024 | 438a342 |
| APERTAR_DEAD_MEDIUM_STOP_MS | CC:4469 | 2000 (100..600000) | 0b1632f |
| APERTAR_WRITE_STALL_MS | CC:4861 | 5000 (1000..600000) | a3ac8da |
| APERTAR_MEDIA_TUNE | App.cpp:11401 | off ("1" = on; wins over file) | 26da30e / ebdcd08 |
| APERTAR_DNG_DONTNEED, APERTAR_DNG_WRITEBACK, APERTAR_MEDIA_SYNC_MS | CdngEncoder.cpp:91, CC:4365, 4718 | now fall back to the tune file | 2edc6d0 (vars themselves from neighbour commits) |
| APERTAR_RAW_CAMERA_BUFFERS, APERTAR_CDNG_UNCOMPRESSED_WORKERS, APERTAR_CDNG_QUEUE_FRAMES | CC:1469, 4320, 4329 | existed upstream; default now comes from profile/tune | 26da30e, 2edc6d0 |

### Files on disk

/run/apertar-media/ (pi), /run/apertar-media/eject/<devbase>, /run/apertar-media/tune/<saved kernel values> (root), /run/apertar-media/media-tune.override.conf, /home/pi/apertar-media-tune.conf, /usr/local/libexec/apertar-media-tune (not installed by anything in repo; README documents no install), /etc/sudoers.d/apertar-media, /etc/tmpfiles.d/apertar-media.conf. Raw PCM `audio_capture.raw` left in place when medium gone (AudioRecordingSession.cpp).

### UI elements

Touch UI: status text "MEDIA REMOVED" / "MEDIA ERROR" (MediaStatusBridge.cpp:1251). Signal `ApertarControlBridge::coreMediaStateChanged(QString,bool)`; slot `MediaStatusBridge::setCoreMediaState`; wired in main.cpp (+2 lines). WebUI: `recordingStatus` text "MEDIA REMOVED", `hasMedia` uses `media_alive` (WCP:10891, 14405, 15255, 15392), controls disabled when `!hasMedia`. Hardware card "CFexpress hat" (other unit). No QML change.

## 5. Original code modified

| Region | Where | Change | Kind |
| --- | --- | --- | --- |
| `rawCameraBufferCount` | CC:1457-1470 | base + profile extra, or tune raw_buffers, env still wins | extended-in-place |
| uncompressed worker count and queue depth in recorder startAtFolder | CC:4315-4330 | env > media profile > format default; was `max(2,min(4,hwthreads))` and 12/24 | extended-in-place (behaviour: exFAT/ext4 table gives 4/12, equals old on 4 cores) |
| `startAtFolder` | CC:4225-4250 | refuses while writers from a dead-medium stop remain; resets fault/mediumGone/progress | extended-in-place |
| recorder `stop()` | CC:4440-4520 | bounded wait (APERTAR_DEAD_MEDIUM_STOP_MS), 5 s stall detection, detach stuck workers, "dead-medium stages" log | rewritten (stop join was unconditional upstream) |
| DNG/MLV/lossy writer error handling | CC:5290-5440; MlvEncoder.cpp; LossyDngEncoder.cpp (abandonWrites, abandon) | errno classified; first fault wins; medium gone -> abandon files, no rename/fsync | rewritten/extended |
| `failRecording` | CC:5424 | takes MediaFault; sets mediumGone_ | behaviour-changed |
| `checkRecordingFailure` | CC:12456 | reports fault name; calls stopRecording(mediumGone) | extended-in-place |
| `CameraController::flagMediaFault`, `recordingFaultName`, members externalFailureMessage_ etc. | CC:12483; CameraController.hpp:116 | new methods | added |
| record start | CC:7735 | `recorder_.setMediaProfile(detectMediaProfile(cached snapshot))`; `configuredMediaRoot() = mediaRoot` | extended-in-place |
| `CdngEncoder.cpp` dngPageCacheDrop | :85-110 | env, else tune file `dontneed`; was env only | extended-in-place |
| AudioRecordingSession.cpp | writer drains without touching a gone medium; leaves raw PCM; APERTAR_AUDIO_BUFFER_MS default 1000 -> 100 (0358fcf) | extended / behaviour-changed |
| App state builders | App.cpp:9313, 9555-9562, 12943-12962 | new fields | extended-in-place |
| `ejectMediaAtPath` / `mountMediaDeviceAtPath` | App.cpp:4355, 4389 | eject-intent write/clear | extended-in-place |
| `mountDeviceAtMediaPath` + embedded python reinsert watcher mount commands | App.cpp:4208-4212, 4279-4286 | add `noatime` | behaviour-changed |
| storage label | App.cpp:9316-9326 | "Media Removed"/"Media Error" instead of mount-table label | extended-in-place |
| `handleCommand` | App.cpp:12597 | media gate before three commands | extended-in-place |
| `playbackHoldReason` | App.cpp:11339 | `mediaUsable` from watcher | extended-in-place (T47 unit) |
| UI CfeAutomounter.cpp | UI dc471c1 | new `handleSurpriseRemoval` (lazy umount2 MNT_DETACH, PCIe remove, LED off), `removePcieDevice` extracted from unmountPcie | extended-in-place + moved |
| UI ApertarControlBridge, MediaStatusBridge, main.cpp | UI 160898c | media state passthrough; `updateStatus` short-circuits on dead state | extended-in-place |
| WCP | 438a342, 3c4f07d | hasMedia from media_alive, status text | extended-in-place |

## 6. New abstractions

| Name | Files | Purpose | Upstream equivalent | Used by |
| --- | --- | --- | --- | --- |
| `apertar::` header-only modules MediaFault/Probe/Intent/Profile/Tune/CfeHat (6 headers, ~1100 lines) | src/util | classify, probe, profile, tune | upstream util/ has 4 small headers (AtomicStillFile, RecordingDropWarning, RecordingFailure, SettingsFile); mount logic is free functions in App.cpp (`isMountedPath` :2014, `mountedDeviceForPath` :2031). `RecordingFailure.hpp` is the nearest precedent for a fault class | App, CC, CdngEncoder, MlvEncoder |
| Media watcher thread `runMediaWatcher` | App.cpp:10855 | 1 s idle / 250 ms recording probe, publishes `media` event, trims, merges, pre-roll triggers, tuning | none: upstream polls `isMountedPath` inside state builders; no media thread | App |
| Process-global cached snapshot (static mutex+optional) and `configuredMediaRoot()` static string | MediaProbe.hpp, MediaProfile.hpp | let configure-time code read media state without App | none (upstream passes mediaRoot as option) | CC, CdngEncoder |
| MediaTune INI resolver with 2 files | MediaTune.hpp | tune per medium | upstream: env vars (`unsignedEnvValue`), `camera_settings.conf` via SettingsFile.hpp, `apertar-hardware.conf` via hwconf in App | CC, CdngEncoder, MediaProfile |
| Root helper scripts/apertar-media-tune + sudoers + tmpfiles | scripts, config | kernel tuning | upstream root helpers: `/usr/local/libexec/apertar-standby-usb`, `apertar-standby-low-power` called as `sudo -n` (App.cpp:1544, 1549); upstream repo has no sudoers/tmpfiles files in config/ (only apertar-core-capture-priority.conf); fork main has apertar-boot-config.sudoers (README:203) | App |
| scripts/apertar-tune (Python, 487 lines) | scripts | CLI for override | upstream scripts/: only start-apertar-core.sh | operator |
| Eject-intent flag file protocol | MediaIntent.hpp | tell an automounter | none | App (writer only) |
| Dead-medium writer detach (liveWorkers_, exitCv_, mediumGone_) | CC recorder | bounded stop | upstream joins all workers | CC |
| CfeHatReader | CfeHat.hpp | second reader of the HAT byte | upstream: UI `CfeAutomounter.cpp` I2cHat class (:393); Core python helper in App.cpp:3394 | watcher, Hardware card |

## 7. Removed, narrowed, hidden

| What | Where | Effect |
| --- | --- | --- |
| record_start without media check | handleCommand | now refused below 1 GiB free (default; upstream recorded until failure) |
| `media_mounted` as UI truth | WCP, MediaStatusBridge | still emitted; UI prefers `media_alive`; when Core fields absent the UI behaves as before |
| exFAT 2 writers / queue 16 / +2 buffers | MediaProfile.hpp | table row reverted to 4/12/0 (0358fcf); vfat, ntfs, ntfs-fuse still 2/16/+2; `other` 2/12/0 |
| `workers` for unknown/other medium | MediaProfile writerSettingsFor | unmounted/other: workers=2 but `known()` false for None, so the format default stays; for `Other` fs profile is known and gives 2 workers (was 4 on 4 cores): behaviour change, unconfirmed on hardware |
| Writer join on stop | CC stop() | detached threads possible (documented "shutdown only") |
| direct I/O flag in MediaWriterSettings | MediaProfile.hpp | field present, comment says unused (T24 not in this fork) |
| Audio capture ring 1000 -> 100 ms default | AudioRecordingSession | back to old |
| `apertar-tune` / kernel tuning in upstream README | none | README gains section "Write-path knobs" (env table + file); no install step for apertar-media-tune/sudoers/tmpfiles |

Nothing was found that removes an upstream command or UI element.

## 8. Observations that affect later stages (facts only)

| Fact | Evidence |
| --- | --- |
| Eject intent has a writer in Core and no reader: Apertar-UI automounter and upstream CfeAutomounter.cpp do not mention `/run/apertar-media` or `eject/` | `grep -rn "apertar-media\|eject/" Apertar-UI/src` finds nothing |
| tmpfiles/sudoers for apertar-media-tune have no documented install step; override file dir `/run/apertar-media` exists only after the tmpfiles rule is installed, so `apertar-tune set` fails without it | README has trim install only (README:308-312); `write_atomic` uses mkstemp in override dir |
| Base path `/home/pi/apertar-media-tune.conf` and sudoers user `pi` hardcoded | MediaTune.hpp:27; sudoers. Upstream also hardcodes `/home/pi/apertar-hardware.conf` (App.cpp:4921) |
| apertar-tune says Core reads files "once, at start"; conf header and README say "at start and when a take starts" | apertar-tune docstring vs conf line 17. CC reads tune per take (`mediaTuneForConfiguredRoot` in startAtFolder, CC:4364); `dontneed`/`writeback` fixed per process |
| Tune keys, ranges and section names are written three times: MediaTune.hpp, apertar-tune, conf template | read |
| `mediaTuneForConfiguredRoot` re-reads and re-parses both files on every call (no cache) | MediaProfile.hpp; called from rawCameraBufferCount, startAtFolder, per-take |
| Duplicate `"media_state"` key in socket get_state body | App.cpp:12944 and 12961 |
| `media_alive` is `mounted()`; state "none" (nothing mounted) also reports alive=false, UI checks state removed/error separately | App.cpp:12962; UI MediaStatusBridge.cpp:1245 |
| Referenced host test tools/media_tune_test.cpp absent | git ls-files |
| README says 4 raw buffers "plus the filesystem's extra" while exFAT/ext4 extra = 0 | README:table row |
| Eject-intent clear on "node gone" uses /sys/class/block, which exists on every Pi for the name until removed | MediaIntent.hpp |

## 9. Board assumptions

| Assumption | Where |
| --- | --- |
| Pi 5 / CM5 with CFexpress HAT on NVMe via PCIe: "a Pi 5 cannot hot-plug NVMe", PCIe remove + rescan before reuse | MediaProbe.hpp (pulledSinceMount), App.cpp:10863, UI dc471c1 comment, MediaProbe nvme "dead" state |
| HAT on I2C bus 10 address 0x34 (default; configurable via [cfexpress_hat]); bus 10 is the Pi 5 RP1-side bus used by upstream | CfeHat.hpp:21, UI CfeAutomounter.cpp:38; upstream python helper I2C_BUS = 10 (App.cpp:3392) |
| HAT status byte semantics (bit0 no card, bit1 eject held, 0x69 = none) | CfeHat.hpp |
| PCIe controller id `1000110000.pcie` (upstream, Pi 5 RP1 address) | upstream App.cpp:3398, not new |
| Four cores: `min(4, hardware_concurrency)` caps writers; compressed queue 24 only when threads >= 4 | CC:4315-4329 |
| RAM size: none in this unit | - |
| gpiochip numbering: none in this unit | - |
| Fan: none | - |
| Storage classes decided from sysfs: nvme*, mmcblk* (SD), USB via "/usb" in realpath and driver=uas | MediaProfile.hpp classifyMediaClass |
| nvme_core `default_ps_max_latency_us` (APST) only for pi-nvme | helper script |
| Mount root /media/RAW default; `configuredMediaRoot()` | MediaProfile.hpp |
| User `pi`, /home/pi, udisksctl, `sudo -n` | sudoers, MediaTune.hpp, App.cpp |
| Pi 4 / CM4: NVMe not applicable, USB/SD classes work; HAT reader disabled unless [cfexpress_hat] present (enabled only when section exists, App.cpp:5318) | probable |
