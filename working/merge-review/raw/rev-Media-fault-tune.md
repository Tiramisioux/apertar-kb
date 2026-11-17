# Review: Media-fault-tune (stage 2)

Refs: port = `cinemate-port` Core `01f170c`, UI `7ea9afc`; upstream = `upstream-1.6.0` (`core-upstream`, `ui-upstream`); fork main = `core-main` `f60e301`.
Yardstick: `raw/conv-platform-build.md` (S*, I*, N*), `raw/conv-core-command-plane.md` (C1-*), `raw/conv-hardware-config.md` (HW-*). No `apertar-conventions.md` yet.
Inventory: `raw/inv-Media-fault-tune.md`. All claims confirmed (read in code) unless marked.

## 1. Verdict in one table

| Id | Title | Category | Severity | Deliberate |
| --- | --- | --- | --- | --- |
| F1 | Media tuning file + override + Python CLI: a second config system for developer knobs | mismatch | major | yes |
| F2 | Kernel tuning root helper: shell script in Core, open sudoers, no timeout, no lock | mismatch / security | major | yes |
| F3 | Process-global media snapshot and `configuredMediaRoot()` as a channel from App to CameraController | mismatch | major | yes |
| F4 | Eject-intent flag protocol with no reader in Apertar | slop (dead) | major | yes |
| F5 | Writer table changes upstream defaults for vfat/ntfs/other, unmeasured | removed-upstream-behaviour | minor | yes |
| F6 | Record gate: env switches in the command plane; 1 GiB floor also gates stills; unmounted dir refused | mismatch / removed-upstream-behaviour | minor | yes |
| F7 | CfeHat reader lives in `src/util`, parsed in App, reloaded on save, default off | mismatch | minor | unknown |
| F8 | Duplicate `media_state` key in socket `get_state` | bug / protocol | minor | no |
| F9 | Automounter surprise-removal acts on a single HAT read | bug (probable) | minor | no |
| F10 | User stop with a slow (alive) medium can be judged "removed" after 5 s | bug (probable) | minor | no |
| F11 | Internal references and history in comments; missing test file named; stale claims | slop | minor | no |
| F12 | Second mount-table parser beside App's `isMountedPath` / `mountedDeviceForPath` | duplication | nit | no |
| F13 | `loadMediaTuneLogged` logs only the first resolution; docs disagree on when files are read | bug / slop | nit | no |

No protocol break: all socket and HTTP changes are additive scalar fields and a new event, which an unmodified UI ignores (`ui-upstream/src/ApertarControlBridge.cpp:1182-1197`: unknown events fall through), and the port UI keeps old behaviour when the fields are absent (`Apertar-UI` 160898c `setCoreMediaState` only on `contains("media_state")`).

## 2. Findings

### F1 Media tuning file + override + Python CLI (mismatch, major, deliberate yes)

Port:
- `src/util/MediaTune.hpp:8-15,27-28` two INI files `/home/pi/apertar-media-tune.conf` and `/run/apertar-media/media-tune.override.conf`, 8 keys, 4-level section lookup, precedence env > override > base > code.
- `scripts/apertar-tune` (487 lines, Python 3) edits the override file; keys, ranges and section names repeated at `scripts/apertar-tune:69-81`; third copy in `config/apertar-media-tune.conf:144-174`.
- `README.md:337-357` documents the env vars and the file for operators.
- Read sites: `CameraController.cpp:1467` (raw buffers), `:4364` (sync_ms), `:4718` (writeback, static once), `CdngEncoder.cpp:91` (dontneed), `ApertarCoreApp.cpp:11405` (kernel_tune), `MediaProfile.hpp:195` (workers/queue/extra).

Upstream:
- Capture-pipeline engineering knobs are `APERTAR_*` env vars read at the point of use, clamped, not settings, not in README: C1-I22, I1. Example `core-upstream/src/camera/CameraController.cpp:3330` `maxQueuedFrames_ = unsignedEnvValue("APERTAR_CDNG_QUEUE_FRAMES", defaultQueueFrames, 4, 64);`.
- Scripts are bash in `scripts/` (S10); upstream `scripts/` holds only `start-apertar-core.sh`.
- No shared INI parser library (HW-S2); hand-edited operator file is `apertar-hardware.conf` for wiring only (HW-N3).

Why it matters: the original developer gets a third configuration surface (after `camera_settings.conf` and `apertar-hardware.conf`) whose job is A/B measurement, a 487-line Python tool, a tmpfs override that needs a tmpfiles rule, and a key table written three times. The env vars it wraps already exist and still win. The KB states the motive: "a test night needs no systemd drop-in" (`working/drop-frames/media-tune-file.md`, asked for by Patrik 2026-11-02). That is a lab convenience, not camera behaviour. The template also sets `[default] raw_buffers = 8` (`config/apertar-media-tune.conf:156`), so `apertar-tune init` doubles SDR raw buffers (4 -> 8) for every mode.

Rework:
1. Delete `src/util/MediaTune.hpp`, `scripts/apertar-tune`, `config/apertar-media-tune.conf`, the override path, the README "media tuning file" paragraph (`README.md:339`) and the `tune_override=` field of the clip log line.
2. Read sites go back to env-only with the code default: `CdngEncoder.cpp:85-110` `APERTAR_DNG_DONTNEED`; `CC:4718` `boolEnvValue("APERTAR_DNG_WRITEBACK", true)`; `CC:4364` `APERTAR_MEDIA_SYNC_MS`; `rawCameraBufferCount` `unsignedEnvValue("APERTAR_RAW_CAMERA_BUFFERS", base, 3, 16)`; `applyMediaTuning` see F2.
3. Per-filesystem writer values: keep only as code defaults (F5) with `APERTAR_CDNG_UNCOMPRESSED_WORKERS` / `APERTAR_CDNG_QUEUE_FRAMES` as overrides.
4. Move the README env table out of the operator README into a developer note (I1: not in README), or keep one short "developer knobs" list if the owner insists.
5. Keep the A/B tooling (override file, `apertar-tune`) in the KB / test-rig repo, where the systemd drop-ins it replaces also live.

Risk: test scripts (`b1-arm.sh`) that write the override file must switch back to drop-ins. No camera behaviour changes when the base file is absent (it is absent on a stock image).

### F2 Kernel tuning root helper (mismatch + security, major, deliberate yes)

Port:
- `scripts/apertar-media-tune` POSIX sh, takes `apply|restore <rootdisk> <class> <fs>`, writes `/sys/block/<root>/queue/*`, `/proc/sys/vm/dirty_*`, `nvme_core default_ps_max_latency_us`; saves originals in `${APERTAR_MEDIA_RUN_DIR:-/run/apertar-media}/tune`.
- `config/apertar-media.sudoers:3` `pi ALL=(root) NOPASSWD: /usr/local/libexec/apertar-media-tune` (any arguments).
- `config/apertar-media.tmpfiles.conf:3-5` `/run/apertar-media` owned by `pi`, `tune/` owned by root inside it.
- Caller `ApertarCoreApp.cpp:11420-11423` `"sudo -n " + helper + " apply " + shellQuote(rootDisk) + ...` on the media watcher thread, no timeout.
- Off by default (`APERTAR_MEDIA_TUNE=1` or `kernel_tune=on`); commit 26da30e "helper added but not installed"; KB: "kernel_tune stays off until B3 shows a kernel setting helping". No install step in README for this helper, sudoers or tmpfiles.

Upstream (S7, I6, N7, S9):
- Root work is a single-file Qt-free C++ helper `UI/src/<Name>.cpp`, target `apertar-<name>`, called as `/usr/bin/timeout Ns /usr/bin/sudo -n <abs path> <literal verb>` (`core-upstream/src/ApertarCoreApp.cpp:1541-1550`: "Fixed executable and arguments only; never accept paths from WebUI/config.").
- Sudoers lists every verb: `ui-upstream/systemd/apertar-standby-usb.sudoers:1` `... apertar-standby-usb off, ... apertar-standby-usb on`.
- Helper shape: euid check, root-owned `/run/apertar-<name>` checked with `lstat`, `flock(LOCK_NB)` (I6, `UI/src/StandbyUsbPower.cpp:15-23,241-273`).
- System files live flat in `UI/systemd/`; Core holds only `config/` drop-in and `scripts/start-apertar-core.sh` (S9).

Why it matters:
- Security (probable, needs Pi check): `tune/` is root-owned but its parent `/run/apertar-media` is `pi`-owned, so `pi` can rename `tune` away and create its own `tune/` with chosen `vm_dirty_bytes`, `queue_scheduler` ... files; the next `restore` writes those values as root into `/proc/sys/vm/*` and the queue. Impact is limited to these fixed knobs (system-wide writeback DoS). On Raspberry Pi OS `pi` usually has full NOPASSWD sudo anyway (S8 note), which lowers the real gain, but the file pattern is still what upstream's lstat/root-owned-dir rule exists to avoid.
- No `timeout`: a hung `sudo`/sysfs write blocks the media watcher, i.e. pull detection.
- `vm.dirty_*` are global; `dirty_bytes = 1 GiB` for pi-nvme is half the RAM of a 2 GB Pi 5/CM5 (pi-compat).
- Unproven: the code comment itself says 16-bit 4K25 ran clean without it (`ApertarCoreApp.cpp:11398-11400`).

Rework: drop F6 from the merge: delete `scripts/apertar-media-tune`, `config/apertar-media.sudoers`, `config/apertar-media.tmpfiles.conf`, `ApertarCoreApp::applyMediaTuning` and its two calls in `runMediaWatcher`, the `kernel_tune` key. If a later test proves it, re-add per R3/S7: `Apertar-UI/src/MediaTune.cpp` -> `apertar-media-tune`, verbs `apply-<class>` / `restore` only, root disk derived inside the helper from the mount of `/media/RAW` (no argument), state in root-owned `/run/apertar-media-tune` with `lstat` + `flock`, sudoers in `UI/systemd/apertar-media-tune.sudoers` listing each verb, caller `/usr/bin/timeout 6s /usr/bin/sudo -n ...`.

### F3 Process-global media snapshot and configuredMediaRoot (mismatch, major, deliberate yes)

Port:
- `MediaProbe.hpp:260-290` static mutex + static `std::optional<MediaSnapshot>`, written by `ApertarCoreApp::runMediaWatcher` (`App:10889 updateCachedMediaSnapshot(current)`), read by `CameraController` and `CdngEncoder` through `cachedMediaSnapshotOrProbe`.
- `MediaProfile.hpp:214-218` static `std::string &configuredMediaRoot()` set in `CameraController.cpp:10543`, read by `rawCameraBufferCount` (`CC:1467`) and `CdngEncoder.cpp:91`.
- Comment reason: "configure-time code read media state without App" (`MediaProbe.hpp:257-259`; "critic Y8").

Upstream:
- Parts talk to App only through `std::function` callbacks; no part holds an App pointer (C1-S19). The controller already owns the root: `core-upstream/src/camera/CameraController.cpp:8247` `session_->startRecording(mediaRoot_, settings_, ...)`.
- Function-local static caches exist only as private caches inside one file (`core-upstream/src/ApertarCoreApp.cpp:2269`, `:2788`; C1-I19), never as a cross-module channel.

Why it matters: buffer count, writer topology and page-cache mode now depend on a hidden global filled by another thread in another class; a reader of `rawCameraBufferCount` cannot see where the value comes from, and a probe (blocking statvfs) runs on the configure path if the watcher has not cycled yet.

Rework: App pushes the profile into the controller: `CameraController::setMediaProfile(const MediaProfile &)` (atomically stored under the controller mutex), called from `runMediaWatcher` where `mediaProfile_` is updated (`App:10935-10940`). `rawCameraBufferCount(bool clearHdr, unsigned extra)` takes the extra from the controller's copy; `recorder_.setMediaProfile(...)` at `CC:7735` reads the same copy; `CdngEncoder` gets `dontneed` through its existing options struct. Delete `cachedMediaSnapshot*`, `updateCachedMediaSnapshot`, `configuredMediaRoot`, `mediaExtraRawBuffersForConfiguredRoot`, `mediaTuneForConfiguredRoot`.

### F4 Eject-intent flag protocol with no reader (slop/dead, major, deliberate yes)

Port: `src/util/MediaIntent.hpp` writes `$APERTAR_MEDIA_RUN_DIR/eject/<dev>`; writer `ApertarCoreApp.cpp:4389` (eject), cleared at `:4355` (mount) and `:10917` (removal). Comment: protects against "an automounter that treats 'change' like 'add'" (Cinemate f01b6cd).

Upstream: Apertar's automounter is HAT-button driven, not udev-driven (`ui-upstream/src/CfeAutomounter.cpp:544-553`; only `udevadm settle` at `:721`). Its runtime dir is `/run/apertar-cfe` (`CfeAutomounter.cpp:40`). Nothing in `Apertar-UI/src` or upstream reads `/run/apertar-media/eject` (inventory section 8, `grep -rn "apertar-media\|eject/" Apertar-UI/src` empty).

Why it matters: a protocol for a Cinemate automounter that Apertar does not have; one more `/run` directory needing a tmpfiles rule; without the rule every eject logs "eject intent not recorded ... an automounter may remount the drive" (`App:4390-4392`), a warning about a risk that does not exist on Apertar.

Rework: delete `MediaIntent.hpp`, the three call sites, `blockDeviceNodeExists`, and the `eject` line of the tmpfiles file.

### F5 Writer table changes upstream defaults (removed-upstream-behaviour, minor, deliberate yes)

Port `MediaProfile.hpp:136-150`: ext4/exFAT `{4,12,+0}`; vfat, ntfs `{2,16,+2}`; ntfs-fuse `{2,16,+2}`; `Other` (btrfs, xfs, f2fs ...) `{2,12,0}` and `known()` true, so `CC:4319-4320` gives 2 writers. Comment `CC:4316-4318` still says "exFAT/NTFS get 2".
Upstream `core-upstream/src/camera/CameraController.cpp` (same function, fork main `CC:3433`): `normalWorkerCount = std::max(2u, std::min(4u, hardwareThreads))` (4 on a Pi 5), queue 12, raw buffers fixed.
Why: on FAT32, NTFS and any other filesystem the port halves the writers and adds 2 raw buffers, using Cinemate's numbers that dropped frames when measured on exFAT (`MediaProfile.hpp:140-141`: "Cinemate's {2, 16, +2} dropped frames ... 4/12 held"). The rows are unmeasured (header: "starting points for the measurement in T29").
Rework: make every row equal the upstream default (4 writers via `formatWorkerCount`, queue 12, +0) or drop `writerSettingsFor` and the table; keep `MediaProfile` only for class/fs logging. Delete the unused `directIo` field (`:133`).

### F6 Record gate details (mismatch + removed-upstream-behaviour, minor, deliberate yes)

Conforms: the gate is a multi-command guard at the top of `handleCommand` (`App:12597-12600`, C1-S04), refusal sentences follow C1-I07, and upstream already refuses the Sound Recorder without mounted media (`core-upstream/src/ApertarCoreApp.cpp:8351-8354` "Sound Recorder needs mounted media.").
Deviations:
- `APERTAR_MEDIA_REQUIRE_MOUNT` and `APERTAR_MEDIA_MIN_FREE_MB` read in the command plane (`App:11335`, `:11379`). C1-S24: "the command plane reads no `APERTAR_*` switch"; a launch option is an `Options` member (upstream `options_.simulateCamera`).
- The 1 GiB floor also refuses `capture_photo` (a DNG still is tens of MB); upstream records and shoots until the write fails.
- An unmounted `/media/RAW` (plain directory on the root fs) is now refused for video and stills; upstream allowed it.
Rework: one launch option `--allow-unmounted-media` (Options member, usage line, README row) instead of `APERTAR_MEDIA_REQUIRE_MOUNT`; floor as a constant, applied to `record_start` and `timelapse_start` only, `capture_photo` refused only when not mounted/removed/error.

### F7 CfeHat reader placement and config (mismatch, minor, deliberate unknown)

Port: `src/util/CfeHat.hpp` class `CfeHatReader`; parser `loadCfeHatConfig()` free function in App (`App:5298-5345`); reloaded on save via `cfeHatGeneration_` (`App:10869-10875`, comment "T39"); `enabled` true only when the section exists (`App:5318`).
Upstream: device classes in `src/hardware/<Device>.{hpp,cpp}` with their own `static loadConfig()` (HW-S1, HW-S2); wiring read once at start, restart required (HW-N1); `[cfexpress_hat]` default enabled when absent (`core-upstream/src/ApertarCoreApp.cpp:3394` `CFE_HAT_ENABLED = True`; `ui-upstream/src/CfeAutomounter.cpp:106` `bool enabled = true;`).
Conforms: raw `/dev/i2c-N` + `I2C_SMBUS` ioctl (HW-I6), same aliases `bus|channel|i2c_bus`, `address|addr` as upstream python (`core-upstream/...:3449-3452`), a per-process copy (S12).
Rework: move to `src/hardware/CfeHatSlot.{hpp,cpp}` with `static Config loadConfig()` (default enabled = true like the other two readers), register in `add_executable` (HW-S9), read once at start; drop `cfeHatGeneration_` reload or justify it next to HW-N1.

### F8 Duplicate `media_state` key (bug/protocol, minor)

`ApertarCoreApp.cpp:12944` `",\"media_state\":\"" << mediaSnapshot().stateName()` and `:12961` `",\"media_state\":\"" << mediaState.stateName()` in the same object. Qt's `QJsonDocument` keeps the last; a `find`-based flat parser takes the first; the two can differ (two separate snapshot reads). Rework: delete line 12944.

### F9 Automounter surprise removal on one HAT read (bug, probable, minor)

`Apertar-UI/src/CfeAutomounter.cpp:549-550` (dc471c1) `if (!lastInsert && insert && m_mounted) handleSurpriseRemoval();` acts on one `readButtons()` (`:402-420`, no debounce) and lazy-unmounts plus PCIe-removes the recording drive. Core's own reader requires two agreeing reads because "a glitch must not end a take" (`CfeHat.hpp:35-36`). Upstream already acts on one read for the eject button edge (`:551-552` `unmountPcie()`), so this matches upstream risk tolerance, but it adds a second destructive single-read edge. Failing input: one I2C read with bit 0 set during a take. Rework: require the empty slot on two consecutive 100 ms polls before `handleSurpriseRemoval`.

### F10 User stop on a slow, alive medium (bug, probable, minor)

`CameraController.cpp:4476-4484`: during any `stop()`, a writer that has made no progress for `APERTAR_WRITE_STALL_MS` (5 s) makes the stop call `failRecording(..., MediaFault::Removed)`; the take is then abandoned (no rename/fsync, `mediaFaultMeansGone`). Failing input (probable): a USB HDD or SD card in a GC pause > 5 s at stop; the clip is left unfinalised although the medium is alive. Settle on a Pi with a throttled USB stick (`echo 1 > /sys/block/sdX/queue/...` or `dm-delay`). Rework: in `stop()` treat a stall as Removed only when the media watcher also reports Removed/Error (pass `mediumDead`), else keep waiting.

### F11 Slop in the unit's files (minor)

- Internal ids and history in code comments: `MediaProfile.hpp:21` "s2 §1", `:25` "T29", `:133` "T24's direct I/O, which this fork does not carry; unused", `:141` "C0106, 2026-10-26 ... C0101", `:221` "critic Y8"; `MediaProbe.hpp:179` "critic Y1"; `MediaTune.hpp:11` "2026-11-03"; Cinemate commit hashes `MediaIntent.hpp:14`, `MediaProbe.hpp:23`, `MediaProfile.hpp:80`, `scripts/apertar-media-tune:8`; `scripts/apertar-media-tune:11` "T29 measures them"; watcher `App:10869` "T39", `:10914`/`:10966` "T47", `:10976` "T48", `:10938` "critic S11", `:10901` "kb working/dng-chain, R4". Upstream comments are rare reasons, no tickets (C1-I14).
- `MediaTune.hpp:5` names `tools/media_tune_test.cpp`, which is not in the repo.
- `scripts/apertar-media-tune:20` "With O_DIRECT cDNG ..." describes direct I/O this fork does not have.
- `CameraController.cpp:4316-4318` "exFAT/NTFS get 2" contradicts the table (exFAT 4).
Rework: rewrite each as a one-line reason or delete; remove the test-file reference.

### F12 Second mount-table parser (duplication, nit)

`MediaProbe.hpp:81-130` `decodeMountField`, `normalizeMountPathForProbe`, `findMountEntry` vs App's `decodeProcMountField` (`App:2327`), `isMountedPath` (`:2397`), `mountedDeviceForPath` (`:2414`), same as upstream `core-upstream/src/ApertarCoreApp.cpp:2014-2045`. `rootDiskForDevice` vs upstream `parentDriveForDevice` (`lsblk -no PKNAME`, `:3312`). Both live in the same process. Rework: let `findMountEntry` be the one parser and make `isMountedPath` / `mountedDeviceForPath` thin wrappers, or have the probe call App's helpers through the watcher. Low priority (S12 tolerates copies across classes).

### F13 Tune log and documentation drift (nit; moot if F1 is applied)

`MediaProfile.hpp:172-181` logs `summary()` with `std::call_once`, so only the first resolution (often with nothing mounted, class `unknown`) is logged; later media are never shown although README says "Core logs the values in effect". `scripts/apertar-tune:12` "Core reads the files once, at start" vs `config/apertar-media-tune.conf:139` and `README.md:339` "at start and when a take starts". C++ parser treats lines before any header as `[default]` (`MediaTune.hpp:145`); the Python editor does not (`scripts/apertar-tune:188-202`).

## 3. Abstraction verdicts

| Abstraction | Verdict | Reason |
| --- | --- | --- |
| `MediaFault.hpp` (errno -> fault class, names, text) | keep | Nearest precedent `src/util/RecordingFailure.hpp`; small, pure, used by CC/MLV/Lossy writers. Trim Cinemate references (F11). |
| `MediaProbe.hpp` probe (`evaluateMediaProbe`, `probeMediaRoot`, mount id) | keep, simplify | Solves a real gap (upstream `isMountedPath` stays true for a pulled drive). Remove the global cache (F3) and fold the mount parser with App's (F12). |
| `MediaIntent.hpp` eject-intent protocol | rework-to-upstream-pattern | No reader in Apertar; delete (F4). |
| `CfeHat.hpp` / `CfeHatReader` | simplify | Raw ioctl shape conforms; move to `src/hardware/` with own `loadConfig`, default enabled, read once (F7). |
| `MediaProfile.hpp` (class/fs classification, writer table) | simplify | Classification for logs is fine; writer table must not change upstream defaults (F5); drop `configuredMediaRoot` and `*ForConfiguredRoot` (F3). |
| `MediaTune.hpp` + base/override files | rework-to-upstream-pattern | Env vars at point of use (C1-I22, I1) (F1). |
| Media watcher thread `runMediaWatcher` | keep, simplify | A thread is justified: statvfs can block, and C1-S17/S20 allow an App-owned worker thread. It has become the home of trim, merge, pre-roll, playback yield and frame-slot trimming (`App:10895-10980`); those belong to their own units' supervision (C1-S21 1 Hz loop) and should not ride on the probe thread. |
| Process-global cached snapshot + `configuredMediaRoot()` | rework-to-upstream-pattern | Push the profile into `CameraController` (F3). |
| Root helper `apertar-media-tune` + sudoers + tmpfiles | rework-to-upstream-pattern | Drop until measured; if re-added, S7/I6 shape (F2). |
| `scripts/apertar-tune` Python CLI | rework-to-upstream-pattern | Remove from the repo; test-rig tool (F1). |
| Dead-medium writer detach (`liveWorkers_`, `exitCv_`, `mediumGone_`) | keep | No upstream precedent; bounded stop on a pulled drive is a real need and is commented as shutdown-only. Fix F10. |

## 4. What conforms (for the handoff)

| Item | Rule | Where |
| --- | --- | --- |
| Record gate as one guard at the top of `handleCommand`, covering socket, WebUI and hardware buttons | C1-S04, C1-S01 | `App:12597-12600` |
| Refusals are operator sentences ("Media was removed. Insert or mount media before recording.") | C1-I07, C1-N02 | `App:11359-11384` |
| `media` event built at the emit site, `event` first, flat scalars | C1-I20, C1-S12, C1-I09 | `App:10824-10835` |
| New state fields are flat scalars, additive; old UI ignores them | C1-I09, C1-N11 | `App:9555-9562`, `:12943-12962` |
| Logs use the `ApertarCore media ...` prefix, one key=value line per change | I3, C1-I13 | `App:10861`, `:10902-10910` |
| Watcher is a `std::thread` member started and stopped by App | C1-S17 | `App:8044`, `stopMediaWatcher` |
| Root helper probed with `std::filesystem::exists`, `sudo -n`, one-time journal line when missing | C1-N13, S8 | `App:11411-11419` |
| HAT read with raw `/dev/i2c-N` + `I2C_SMBUS` ioctl, aliases as upstream | HW-I6, HW-I1 | `CfeHat.hpp:224-244`, `App:5334-5340` |
| Failure reporting extends `checkRecordingFailure` instead of adding a second path | C1-N05 | `CC:12456-12490` |
| UI: Core state passed through a bridge signal wired in `main.cpp`; behaviour unchanged without Core's fields | conv-ui-cpp wiring, C1-N11 | UI 160898c |
| UI automounter change reuses upstream helpers (`pciAddressForBlockDevice`, `writeTextFile`, `udevadm settle`) and log prefix | S12, I3 | UI dc471c1 |
| `noatime` added to Core's own mount commands only | - | `App:4208-4212`, `:4279-4286` |

## 5. Commit and test status relevant to the rework

| Feature | Evidence of test |
| --- | --- |
| Pull detection, bounded stop, slot bit | Pi pull test 2026-10-26 (a3ac8da message) |
| Writer table exFAT row | measured C0101 vs C0106 (0358fcf) |
| Kernel tuning | never installed; only "no helper call after restart" (ebdcd08) |
| Tune file / CLI | "desk only"; host test file named but absent |
| UI automounter release | "pi build (see next run)" |

## Skeptic

Stage 3. Every finding re-read in code on both sides (port Core `01f170c`, UI `7ea9afc`; `core-upstream`, `ui-upstream`, `core-main`).

| Id | Verdict | Why |
| --- | --- | --- |
| F1 | corrected | Confirmed. Refs fixed: the template has 54 lines and `raw_buffers = 8` is at `config/apertar-media-tune.conf:36` (not :144-174, :156). The env vars it wraps are themselves port additions: none of `APERTAR_RAW_CAMERA_BUFFERS`, `_DNG_DONTNEED`, `_DNG_WRITEBACK`, `_MEDIA_SYNC_MS`, `_MEDIA_TUNE` is in `core-upstream` or `core-main`. Rework risk adds owner sign-off: Patrik asked for the file. |
| F2 | corrected (stronger) | Confirmed. Added: `save_once` (`scripts/apertar-media-tune:48-53`) runs `cat "$2" > "$STATE_DIR/$1"` as root. pi can rename the root-owned `tune/` (its parent is pi-owned) and plant a dangling symlink, so root creates a file of pi's choosing. The helper also takes any `<rootdisk>` from pi. Exposure only once installed, which nothing does yet. |
| F3 | stands | Confirmed (`MediaProbe.hpp:257-290`, `MediaProfile.hpp:212-234`, `CC:10543`, `App:10889`). Upstream controller owns `mediaRoot_` (`core-upstream CC:8247`, `.hpp:118`). Rework risk added: the watcher must not wait on the controller mutex during configure. |
| F4 | corrected | Severity major -> minor. Dead code with one misleading log line, no behaviour harm. The KB says the same: "nothing in any local repo consumes the eject flag yet (critic Y12)" (`working/yank-answer.md:75`). |
| F5 | stands | Confirmed `MediaProfile.hpp:136-150`, `known()` true for `Other` (:160), `CC:4315-4330`; `core-main CC:3433` fixed `max(2, min(4, threads))`. |
| F6 | stands | Confirmed `App:11331-11384`, `:12597-12600`. Upstream App reads env only for paths (`APERTAR_HARDWARE_CONFIG`, `core-upstream App:4254`), never to change a command's reply. |
| F7 | corrected | Reload on save comes from the port-wide hot-apply commit `dcf09ee` (`App:12328-12329`), not from this unit. It is judged with Controls, so that step is removed from this rework. Upstream Core's `CFE_HAT_ENABLED = True` sits in the embedded automounter Python string (`core-upstream App:3394`). |
| F8 | stands | Confirmed `App:12944` and `:12961` read two separate snapshots. |
| F9 | corrected | "Apertar way" was wrong. Upstream acts on a single read for both edges: insert -> `mountPcie` (`ui-upstream CfeAutomounter.cpp:547-548`) and eject -> `unmountPcie` (:549-550). The difference is cost: a glitch now does a lazy unmount plus a PCIe remove during a take, and Core's own reader of the same byte demands two agreeing reads. Stays minor, probable. |
| F10 | corrected | Deliberate yes, not no: the comment at `CC:4466-4467` says "this stop may be the user's, before any fault", and `0b1632f` records the hang that forced a reboot. The proposed rework (wait unless the watcher says Removed) brings that hang back, because the stall rule exists for "a pulled or hung medium the probe has not seen" (`CC:4833-4834`). New rework below. |
| F11 | stands | Confirmed `MediaProfile.hpp:25,133,141,221`, `MediaProbe.hpp:179`. `tools/media_tune_test.cpp` is absent (`ls tools`). |
| F12 | corrected | Rework reversed. Upstream's `normalizeMountPath`/`decodeProcMountField`/`isMountedPath`/`mountedDeviceForPath` (`core-upstream App:1937,1944,2014,2031`) are the original developer's code and should stay the primary parser. The port's copy should go, not upstream's. |
| F13 | stands | Confirmed `MediaProfile.hpp:172-181` call_once; `scripts/apertar-tune:12` says "once, at start"; `conf:18` says "at start and when a take starts". Moot under F1. |

No new findings.

## Final findings

### Media-fault-tune-F1 [mismatch, major] Media tuning file + tmpfs override + Python CLI form a second config system for developer knobs
- where: `src/util/MediaTune.hpp:1-40`@cinemate-port; `scripts/apertar-tune:1,69-81`@cinemate-port; `config/apertar-media-tune.conf:1-54` (`raw_buffers = 8` at :36)@cinemate-port; `README.md:337-357`@cinemate-port; `src/camera/CameraController.cpp:1458-1470,4364-4365,4718`@cinemate-port; `src/cdng/CdngEncoder.cpp:91`@cinemate-port; `src/util/MediaProfile.hpp:172-181,195,230-234`@cinemate-port
- port way: Two INI files (`/home/pi/apertar-media-tune.conf`, `/run/apertar-media/media-tune.override.conf`) with 8 keys and a 4-level section lookup. Precedence: env > override > base > code. A 487-line Python 3 editor. The key table is written three times (MediaTune.hpp, apertar-tune:69-81, the template's comments). The README documents the knobs for operators. The template sets `[default] raw_buffers = 8`, so `apertar-tune init` doubles SDR raw buffers (4 -> 8) in every raw mode.
- Apertar way: Capture-pipeline knobs are `APERTAR_*` env vars read where they are used, clamped, kept out of settings and the README (C1-I22, I1). Example: `core-upstream/src/camera/CameraController.cpp:3329-3330`@upstream-1.6.0 `maxQueuedFrames_ = unsignedEnvValue("APERTAR_CDNG_QUEUE_FRAMES", defaultQueueFrames, 4, 64);`. Upstream `scripts/` holds only `start-apertar-core.sh` (bash, S10). No shared INI parser (HW-S2). Note: the env vars this file wraps are port additions too (none is in `core-upstream` or `core-main`).
- why it matters: A third config surface, after `camera_settings.conf` and `apertar-hardware.conf`, whose job is A/B measurement on test nights. It needs a tmpfiles rule and a Python tool and keeps the key table in three places. The env vars still win over it.
- rework: Delete `MediaTune.hpp`, `scripts/apertar-tune`, `config/apertar-media-tune.conf`, the override path, the README file paragraph (`README.md:339`) and `tune_override=` in the clip log line. Read sites go back to env plus code default: `CdngEncoder.cpp:85-110` `APERTAR_DNG_DONTNEED`; `CC:4718` `boolEnvValue("APERTAR_DNG_WRITEBACK", true)`; `CC:4364` `APERTAR_MEDIA_SYNC_MS`; `rawCameraBufferCount` `unsignedEnvValue("APERTAR_RAW_CAMERA_BUFFERS", base + extra, 3, 16)`. Per-filesystem writer values stay only as code defaults (F5). Move the env table to a developer note. Keep the A/B tooling in the test-rig or KB repo.
- rework risk: Patrik asked for the file (2026-11-02), so this needs his sign-off. Test scripts that write the override (`b1-arm.sh`) must go back to systemd drop-ins. A stock image has no base file, so camera behaviour does not change.
- effort M; deliberate yes. Evidence: KB `working/drop-frames/media-tune-file.md` ("Asked for by Patrik on 2026-11-02 ... test nights must be able to override it"); fork-log `2edc6d0`.

### Media-fault-tune-F2 [security, major] Kernel tuning root helper is a shell script in Core with open sudoers, no timeout, no lock and a pi-owned state parent
- where: `scripts/apertar-media-tune:1-112` (`save_once` :48-53, `restore_one` :55-65)@cinemate-port; `config/apertar-media.sudoers:3`@cinemate-port; `config/apertar-media.tmpfiles.conf:3-5`@cinemate-port; `src/ApertarCoreApp.cpp:11396-11429` (callers :10942, :10963)@cinemate-port
- port way: A POSIX sh helper takes `apply|restore <rootdisk> <class> <fs>` and writes queue knobs, global `vm.dirty_*` and the `nvme_core` APST parameter. Sudoers: `pi ALL=(root) NOPASSWD: /usr/local/libexec/apertar-media-tune`, which allows any arguments. Originals are saved in the root-owned `tune/` inside the pi-owned `/run/apertar-media`. Core calls it as plain `sudo -n` on the media watcher thread, with no timeout. It is off by default, and nothing installs or has measured it.
- Apertar way: S7/I6/N7/S9. A single-file, Qt-free C++ helper in UI/src, called as `/usr/bin/timeout 6s /usr/bin/sudo -n /usr/local/libexec/apertar-standby-usb <verb>` (`core-upstream/src/ApertarCoreApp.cpp:1541-1545`@upstream-1.6.0, "Fixed executable and arguments only"). The sudoers line lists each verb (`ui-upstream/systemd/apertar-standby-usb.sudoers:1`). The helper checks euid, lstat on a root-owned state dir, and flock (`ui-upstream/src/StandbyUsbPower.cpp:254-262`). System files live in `UI/systemd`.
- why it matters: (1) pi can rename the root-owned `tune/`, because its parent is pi-owned, and plant saved values that `restore` writes as root to `/proc/sys/vm` and the block queue. pi can also plant a dangling symlink, which `save_once`'s `cat ... > "$STATE_DIR/$name"` follows, so root creates a file at a path pi picks (confirmed code path; exploit probable). (2) pi can pass any `<rootdisk>`. (3) Without a timeout, a hung helper blocks pull detection on the watcher thread. (4) A `dirty_bytes` of 1 GiB is half the RAM of a 2 GB Pi 5/CM5, and the code's own comment says it would undo the 1 s sync bound and that 16-bit 4K25 ran clean without it (`App:11398-11400`). Exposure exists only after an install step that nothing performs yet.
- rework: Drop the feature from the merge. Delete `scripts/apertar-media-tune`, `config/apertar-media.sudoers`, the `tune` line of `config/apertar-media.tmpfiles.conf`, `ApertarCoreApp::applyMediaTuning` and its two calls in `runMediaWatcher`, and the `kernel_tune` key. If a measurement later justifies it, re-add it as recipe R3: `Apertar-UI/src/MediaTune.cpp` -> `apertar-media-tune` with literal verbs and no path argument (it derives the disk from the `/media/RAW` mount itself), a root-owned `/run/apertar-media-tune` checked with lstat and flock, `UI/systemd/apertar-media-tune.sudoers` listing each verb, and `/usr/bin/timeout` on the caller.
- effort S; deliberate yes. Evidence: `26da30e` and `ebdcd08` messages (opt-in after testing); KB `media-tune-file.md` "kernel_tune stays off until B3 shows a kernel setting helping".

### Media-fault-tune-F3 [mismatch, major] Process-global media snapshot and configuredMediaRoot() act as a hidden channel from App to CameraController
- where: `src/util/MediaProbe.hpp:257-290`@cinemate-port; `src/util/MediaProfile.hpp:212-234`@cinemate-port; `src/camera/CameraController.cpp:1467,7735,10543`@cinemate-port; `src/cdng/CdngEncoder.cpp:91`@cinemate-port; `src/ApertarCoreApp.cpp:10889`@cinemate-port
- port way: App's watcher thread writes a function-static mutex and a static `optional<MediaSnapshot>`, and CameraController and CdngEncoder read them. CameraController sets a static string `configuredMediaRoot()` that free functions read. If the watcher has not run yet, a blocking probe runs instead.
- Apertar way: Parts talk to App only through `std::function` callbacks and setters; no part holds App state (C1-S19; `core-upstream/src/camera/CameraController.hpp:19-21`). The controller already owns the root: `core-upstream/src/camera/CameraController.cpp:8247`@upstream-1.6.0 `session_->startRecording(mediaRoot_, settings_, ...)`. Function-local statics are only private caches inside one file (C1-I19).
- why it matters: Buffer count, writer topology and page-cache mode depend on a global that another class's thread fills. A reader of `rawCameraBufferCount` cannot see where its value comes from.
- rework: Add `CameraController::setMediaProfile(const MediaProfile&)`, called from `runMediaWatcher` where `mediaProfile_` changes (App:10935-10940). Store it under a small dedicated mutex or as a copy guarded apart from the controller's main mutex, so the watcher never waits behind a configure. `rawCameraBufferCount(bool clearHdr, unsigned extra)` takes the extra from that copy, and `recorder_.setMediaProfile` at CC:7735 uses the same copy. Pass dontneed to `CdngEncoder` through its options. Delete `cachedMediaSnapshot*`, `updateCachedMediaSnapshot`, `configuredMediaRoot`, `mediaExtraRawBuffersForConfiguredRoot` and `mediaTuneForConfiguredRoot`.
- rework risk: The watcher must not wait on the controller mutex. Before the first watcher cycle the profile is empty, which gives the upstream defaults (safe).
- effort M; deliberate yes. Evidence: the comments "critic Y8" say configure time must not block on a dead device.

### Media-fault-tune-F4 [slop, minor] Eject-intent flag protocol has no reader in Apertar
- where: `src/util/MediaIntent.hpp:1-67`@cinemate-port; `src/ApertarCoreApp.cpp:4355,4386-4391,10917`@cinemate-port; `config/apertar-media.tmpfiles.conf:4`@cinemate-port
- port way: Before an eject, Core writes `/run/apertar-media/eject/<dev>`. It clears the flag on mount or removal, so that "an automounter that treats udev change like add" does not remount (Cinemate `f01b6cd`).
- Apertar way: Apertar's automounter is driven by the HAT button, not by udev (`ui-upstream/src/CfeAutomounter.cpp:544-553`@upstream-1.6.0). Nothing in `Apertar-UI`@cinemate-port or upstream reads `/run/apertar-media/eject` (grep empty).
- why it matters: It is dead code for a Cinemate problem. Without the tmpfiles rule, every eject logs "an automounter may remount the drive", a risk that does not exist on Apertar. The KB agrees: "nothing in any local repo consumes the eject flag yet (critic Y12)" (`working/yank-answer.md:75`).
- rework: Delete `MediaIntent.hpp`, the three call sites, `blockDeviceNodeExists` (unless another unit uses it) and the eject line of the tmpfiles file.
- effort S; deliberate yes. Evidence: the `438a342` message and the header comment cite the Cinemate automounter.

### Media-fault-tune-F5 [removed-upstream-behaviour, minor] Writer table changes upstream writer, queue and buffer defaults for vfat, ntfs and other filesystems without measurement
- where: `src/util/MediaProfile.hpp:121-150,160`@cinemate-port; `src/camera/CameraController.cpp:4315-4330`@cinemate-port
- port way: vfat/ntfs/ntfs-fuse get {2 workers, queue 16, +2 raw buffers}. `Other` (btrfs, xfs, f2fs) gets 2 workers, and `known()` is true for it. ext4 and exFAT stay at {4, 12, 0}.
- Apertar way: `core-main/src/camera/CameraController.cpp:3433`@main (same as upstream :3324) `normalWorkerCount = std::max(2u, std::min(4u, hardwareThreads))`, queue 12, raw buffer count fixed.
- why it matters: The port halves writers on FAT32, NTFS and other filesystems with Cinemate's values. Those values dropped frames when they were measured on exFAT (`MediaProfile.hpp:140-141`). The vfat, ntfs and other rows are unmeasured.
- rework: Make every row equal the upstream default, or remove `writerSettingsFor` and keep MediaProfile for class and filesystem logging only. Delete the unused `directIo` field. Fix the stale comment at CC:4316-4318 ("exFAT/NTFS get 2").
- effort S; deliberate yes. Evidence: header "starting points for the measurement in T29"; exFAT row reverted after C0106 (`0358fcf`).

### Media-fault-tune-F6 [mismatch, minor] Record gate reads env switches in the command plane; the 1 GiB floor also gates stills
- where: `src/ApertarCoreApp.cpp:11331-11384`@cinemate-port; `src/ApertarCoreApp.cpp:12597-12600`@cinemate-port
- port way: `handleCommand` refuses `record_start`, `capture_photo` and `timelapse_start` through `mediaGateError()`. `APERTAR_MEDIA_REQUIRE_MOUNT=0` bypasses the gate, and `APERTAR_MEDIA_MIN_FREE_MB` sets the free-space floor (default 1024).
- Apertar way: The guard shape conforms (C1-S04), and refusing on unmounted media has a precedent (`core-upstream/src/ApertarCoreApp.cpp:8351-8354` "Sound Recorder needs mounted media."). But the command plane reads no `APERTAR_*` switch (C1-S24). Upstream App reads env only for path overrides (`APERTAR_HARDWARE_CONFIG`, :4254), and launch options are `Options` members (`options_.simulateCamera`). Upstream records video and stills until the write fails.
- why it matters: A hidden env switch changes command replies. A card with 900 MB free can no longer take a single DNG still.
- rework: Add a `--allow-unmounted-media` `Options` member with a usage line and a README row. Make the floor a constant and apply it to `record_start` and `timelapse_start` only. Refuse `capture_photo` only when the medium is unmounted, removed or in error.
- effort S; deliberate yes. Evidence: `438a342` message (record gate).

### Media-fault-tune-F7 [mismatch, minor] CfeHat reader sits in src/util, is parsed by an App free function and defaults to off
- where: `src/util/CfeHat.hpp:1-75`@cinemate-port; `src/ApertarCoreApp.cpp:5298-5345`@cinemate-port; `src/ApertarCoreApp.cpp:10860-10875,12328-12329`@cinemate-port
- port way: A header-only `CfeHatReader` in `util`, and `loadCfeHatConfig` as a free function in App. The reader is enabled only when a `[cfexpress_hat]` section exists. It is re-read when `cfeHatGeneration_` changes, which is the port-wide hot-apply of Controls saves (`dcf09ee`).
- Apertar way: Device classes are `src/hardware/<Device>.{hpp,cpp}` with their own `static Config loadConfig()` (HW-S1, HW-S2; e.g. `core-upstream/src/hardware/Pcf8574Input.hpp:40`). Upstream defaults the HAT to enabled: `ui-upstream/src/CfeAutomounter.cpp:106` `bool enabled = true;`, and `core-upstream/src/ApertarCoreApp.cpp:3394` `CFE_HAT_ENABLED = True` (in the embedded automounter script).
- why it matters: A hardware reader outside the hardware layer, with a different default from the two upstream readers of the same HAT.
- rework: Move it to `src/hardware/CfeHatSlot.{hpp,cpp}` with `static Config loadConfig()` (`enabled = true` by default; a failed open already returns Unknown) and list it in `add_executable`. Whether to reload on save follows the verdict on `dcf09ee` in the Controls unit, not this one.
- effort S; deliberate unknown.

### Media-fault-tune-F8 [bug, minor] Socket get_state emits media_state twice
- where: `src/ApertarCoreApp.cpp:12944`@cinemate-port; `src/ApertarCoreApp.cpp:12961`@cinemate-port
- port way: Two `"media_state"` members in one object, built from two separate snapshot reads (`mediaSnapshot()` at :12944, `mediaState` at :12961).
- Apertar way: One flat object with each key once (C1-I09).
- why it matters: QJsonDocument keeps the last value and a find-based flat parser takes the first, and the two can differ.
- rework: Delete line 12944, which keeps the value that matches `media_alive`.
- effort S; deliberate no.

### Media-fault-tune-F9 [bug, minor] Automounter unmounts and PCIe-removes the drive on one HAT read
- where: `Apertar-UI/src/CfeAutomounter.cpp:549-550`@cinemate-port; `Apertar-UI/src/CfeAutomounter.cpp:402-420,732-746`@cinemate-port
- port way: `if (!lastInsert && insert && m_mounted) handleSurpriseRemoval();` with no debounce. `handleSurpriseRemoval` runs `umount2(MNT_DETACH)` and then writes `1` to the PCI device's `remove` (UI `dc471c1`).
- Apertar way: Upstream also acts on single reads, but only for cheap or user-initiated edges: insert -> `mountPcie` and eject button -> `unmountPcie` (`ui-upstream/src/CfeAutomounter.cpp:547-550`@upstream-1.6.0). The port's own Core reader of the same byte needs two agreeing reads, because "a glitch must not end a take" (`CfeHat.hpp:35-36`@cinemate-port).
- why it matters: Probable failure: one I2C read with bit 0 set during a take lazily unmounts the recording drive and removes it from PCIe.
- rework: Call `handleSurpriseRemoval` only after the slot reads empty on two consecutive 100 ms polls.
- effort S; deliberate no.

### Media-fault-tune-F10 [bug, minor] A user stop on a slow but alive medium is judged 'removed' after 5 s without progress, and the clip is not finalised
- where: `src/camera/CameraController.cpp:4441-4500`@cinemate-port (stall rule :4476-4483); `:4833-4842`; `:4859-4861`
- port way: While `stop()` waits for writers, a 5 s stall (`APERTAR_WRITE_STALL_MS`) calls `failRecording(..., MediaFault::Removed)`, which sets `mediumGone_`. The writers then get 2 s more and are detached, and every finalise step that touches the medium (rename, fsync) is skipped, even when the writers do return.
- Apertar way: Upstream joins all workers unconditionally (`core-upstream/src/camera/CameraController.cpp:3407`); there is no precedent for a bounded stop. The bounded stop is needed: `0b1632f` records a stop that hung on a pulled card until a reboot.
- why it matters: Probable failure: a USB HDD or SD card that pauses for more than 5 s at stop leaves an unfinalised clip although the medium is alive. During the take, the same rule fires only with the queue full (:4837), when frames are already lost; at stop, waiting longer costs nothing except lock time.
- rework: Keep the bounded wait. Do not make the stall at stop a fault by itself: mark the medium gone only if the writers are still stuck when a separate stop limit expires (for example 15 s, its own env value), or when the watcher reports Removed or Error. Writers that return before that limit go through the normal finalise. Do not make the wait unbounded, which would bring back the hang fixed in `0b1632f`.
- effort S; deliberate yes. Evidence: comment at `CC:4466-4467` "this stop may be the user's, before any fault"; `0b1632f` message.

### Media-fault-tune-F11 [slop, minor] Ticket ids, critic ids, dates, Cinemate hashes and stale claims in comments; the named host test is missing
- where: `src/util/MediaProfile.hpp:21,25,133,141,221`@cinemate-port; `src/util/MediaProbe.hpp:23,179`@cinemate-port; `src/util/MediaTune.hpp:5,11`@cinemate-port; `src/util/MediaIntent.hpp:14`@cinemate-port; `scripts/apertar-media-tune:8,11,20`@cinemate-port; `src/ApertarCoreApp.cpp:10869,10901,10914,10938,10966,10976`@cinemate-port; `src/camera/CameraController.cpp:4316-4318`@cinemate-port
- port way: Comments cite T24/T29/T39/T47/T48, critic Y1/Y8/S11, s2 §1, R4, C0106/C0101, dates and Cinemate commits. `MediaTune.hpp:5` names `tools/media_tune_test.cpp`, which is absent from `tools/`. The helper describes an O_DIRECT path that the fork does not carry. A comment says exFAT gets 2 workers, which is no longer true.
- Apertar way: Comments are rare sentences that give a hazard or a reason, with no tickets (C1-I14).
- why it matters: Meaningless or misleading to the original developer.
- rework: Rewrite each as a one-line reason or delete it. Drop the test-file reference and the O_DIRECT sentence.
- effort S; deliberate no.

### Media-fault-tune-F12 [duplication, nit] Second mount-table parser beside upstream's isMountedPath and mountedDeviceForPath
- where: `src/util/MediaProbe.hpp:81-130,154-175`@cinemate-port; `src/ApertarCoreApp.cpp:2327,2397,2414`@cinemate-port
- port way: `decodeMountField`, `normalizeMountPathForProbe` and `findMountEntry` re-implement the `/proc/mounts` parsing. `rootDiskForDevice` derives the parent disk by string rules.
- Apertar way: `core-upstream/src/ApertarCoreApp.cpp:1937,1944,2014,2031`@upstream-1.6.0 `normalizeMountPath`, `decodeProcMountField`, `isMountedPath`, `mountedDeviceForPath`; `:3312` `parentDriveForDevice` via `lsblk -no PKNAME`.
- why it matters: Two parsers for the same file in one process, one of them the original developer's.
- rework: Keep upstream's functions as the parser. Extend `mountedDeviceForPath` (or add a sibling next to it) to return the fstype too, and have the watcher pass that entry to the probe. Delete `decodeMountField`, `normalizeMountPathForProbe` and `findMountEntry`. `rootDiskForDevice` may stay (a shell `lsblk` once a second on the watcher is worse) with a one-line reason.
- effort S; deliberate no.

### Media-fault-tune-F13 [bug, nit] Tune summary is logged only for the first resolution; docs disagree on when the files are read
- where: `src/util/MediaProfile.hpp:172-181`@cinemate-port; `scripts/apertar-tune:12`@cinemate-port; `config/apertar-media-tune.conf:18`@cinemate-port
- port way: `std::call_once` logs the first resolution, which is often `unknown/none` before a medium is mounted. The CLI says the files are read "once, at start", while the conf file and README say "at start and when a take starts". The C++ parser treats lines before any header as `[default]`; the Python editor does not.
- Apertar way: no precedent.
- why it matters: The log claims to show the values in effect but does not. Moot if F1 is applied.
- rework: Resolved by F1. Otherwise, log once per profile change.
- effort S; deliberate no.
