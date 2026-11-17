# Fix list: Core app, command plane, state, build

Editor's list for the merge review of the cinemate port. Domain: `src/ApertarCoreApp.{cpp,hpp}` (units App-1 to App-5), build, scripts, config and README (unit Build-scripts-docs), plus the findings of the sweeps protocol-security, state-consistency, knobs and stock-behaviour that lie in these files. Port refs: Core `cinemate-port` `01f170c`, UI `7ea9afc`. Yardstick: `apertar-conventions.md` (rule ids CMD-, CAM-, WEB-, PLT-, STY-, with the older C1-/C7-/C8- ids where the reports used them).

Already done on the improvement branch (`/home/user/wt/core-work`, `/home/user/wt/ui-work`), not listed as open:

| Commit | What | Findings |
| --- | --- | --- |
| Core `04fe197` | GPIO chip is a Controls setting again, checks per chip | owner request 16 |
| Core `7dc6f7a`, UI `6a59d83` | Display defaults 720x720 / square / hdmi_external_only=false again | App-2-F1, X-knobs-2, X-stock-behaviour-1 (blocker) |
| UI `2d9cf94` | Audio meter outline off by default (Core half open: APP-19) | X-stock-behaviour-13 |
| UI `ac1fc28` | HDMI timecode white until red timecode is set | X-stock-behaviour-12 |

Ids: APP-n, most severe first. `check_core.sh` and `smoke_core.sh` are in `/home/user/build/bin/`.

## Summary

| Id | Title | Kind | Sev | Effort | Rec |
| --- | --- | --- | --- | --- | --- |
| APP-1 | Boot Config writes free text into config.txt as root through a 1355-line in-place editor | security | blocker | L | ask-owner |
| APP-2 | Storage pre-roll runs by itself: a raw take at every boot, card insert and format | stock | blocker | S | fix-now |
| APP-3 | Boot Config has a second HTTP door with its own lock, header revision, Origin test and status codes | mismatch | major | M | fix-now |
| APP-4 | Three write routes for config.txt; the helper breaks fan mode on files without [pi5]/[pi4]/[all]; operator errors carry shell commands | mismatch | major | S | fix-now |
| APP-5 | errorReplyBody: a third reply builder with machine error codes and extra members | mismatch | major | M | fix-now |
| APP-6 | Preview temporal denoise off by default also strips TDN from H.264 and ProRes recordings | stock | major | S | ask-owner |
| APP-7 | A second dispatcher answers six commands before the command lock | mismatch | major | M | fix-now |
| APP-8 | test_input lets a LAN client run any readable file with bash, without a button press | security | major | S | fix-now |
| APP-9 | Environment knobs in the command plane override saved settings and surface as *_env state | knob | major | M | fix-now |
| APP-10 | [storage] parsed by App and by CameraController; live state shared through header singletons and global std::function hooks | mismatch | major | L | fix-now |
| APP-11 | Storage switches inline the hardware-store edit three times; one family of recording switches spread over two stores | mismatch | major | M | ask-owner |
| APP-12 | Storage pre-roll worker starts and finishes a camera take outside handleCommand | mismatch | major | L | fix-now |
| APP-13 | Three root helpers as /bin/sh scripts with sudoers and tmpfiles inside Core; trim switch says on without the helper | mismatch | major | M | fix-now |
| APP-14 | A second bench-tuning mechanism (INI, /run override, 487-line apertar-tune, tmpfiles) beside upstream's .apertar-tuning | duplication | major | M | ask-owner |
| APP-15 | Real-time scheduling in the start script; LimitRTPRIO=80 under upstream's 'non-real-time' comment | knob | major | S | fix-now |
| APP-16 | No first-run hardware file, and the only default lacks chip=, input tuning and [mpu6050] | removed | major | M | fix-now |
| APP-17 | Ticket numbers, KB paths, Cinemate hashes, banners and narration in App, its header, scripts and config | slop | major | M | fix-later |
| APP-18 | README grows into a lab manual: env knob table, install recipes, socket field lists, measurements | docs | major | S | fix-later |
| APP-19 | Core treats a missing audioRecordedOutlineEnabled as on (the UI half was fixed in U2) | stock | minor | S | fix-now |
| APP-20 | FPS and ISO step lists now end on the mode's odd ceiling | removed | minor | S | fix-now |
| APP-21 | settingsBody carries 14 [storage] members the settings event lacks | mismatch | minor | S | fix-now |
| APP-22 | get_state writes media_state twice from two snapshots | bug | minor | S | fix-now |
| APP-23 | Record gate refuses a --media folder that is not a mount point; the opt-out is an undocumented env variable | removed | minor | S | fix-now |
| APP-24 | Downloads refused in Standby and without media, not only during a take | removed | minor | S | fix-now |
| APP-25 | /api/media hides folders during a hold; cDNG size_bytes and file_count change meaning | removed | minor | S | fix-now |
| APP-26 | audio_url is JSON-escaped, not URL-encoded | bug | minor | S | fix-now |
| APP-27 | /api/buffer 'recording' means something else than /api/state 'recording' | protocol | minor | S | fix-now |
| APP-28 | set_storage_preroll takes value=on|off and the action is the bare noun storage_preroll | protocol | minor | S | fix-now |
| APP-29 | Eject-intent flag file has no reader | slop | minor | S | fix-now |
| APP-30 | Worker lifecycle: three start styles, stopMediaWatcher stops five more threads, five idle predicates, three clocks, record_start waits 4.5 s under the lock | mismatch | minor | M | fix-later |
| APP-31 | Buffer level pushed by an App polling thread; two identical events in one turn | mismatch | minor | M | fix-later |
| APP-32 | Controls worker polls the hardware file every 2 s | mismatch | minor | S | fix-later |
| APP-33 | Delete gate is not atomic with record_start | bug | minor | S | fix-later |
| APP-34 | State and protocol fields with no reader | slop | minor | S | fix-later |
| APP-35 | [cfexpress_hat]: two parsers, defaults in two places, C++ reader off where upstream's is on, status row on boards without the HAT | duplication | minor | S | fix-later |
| APP-36 | clipInfoJson nests meta/extra objects that repeat top-level values | new-ground | minor | S | fix-later |
| APP-37 | set_value_steps: range table inside the branch, repeated in the snapshot reader; nested ui reply | mismatch | minor | S | fix-later |
| APP-38 | Clip name template parsed in App and again in CameraController; dead out-parameter | duplication | minor | S | fix-later |
| APP-39 | IMX585 Clear HDR fallback fps cap disagrees with Core's table | bug | minor | S | fix-later |
| APP-40 | Hardware-file checker reads config.txt for [all] and [pi5] only | board | minor | S | fix-later |
| APP-41 | ApertarCoreApp.hpp: methods among members, split member groups, 37 comment lines | mismatch | minor | S | fix-later |
| APP-42 | Host tests in tools/ outside CMake, with build lines that disagree | new-ground | minor | S | keep-and-document |
| APP-43 | HardwareConfigStore replaces upstream's one save function | new-ground | minor | S | keep-and-document |
| APP-44 | Socket request line raised from 64 KiB to 1 MiB for whole-file set_controls | protocol | minor | S | fix-later |
| APP-45 | set_timecode_mode target= sets screen and file timecode apart | new-ground | minor | S | keep-and-document |
| APP-46 | Serialiser nits: leading-comma fragments, two ladder_tops precisions, help lacks test_input, start logs every success | mismatch | nit | S | fix-later |
| APP-47 | preview_tdn and media_trim are persisted but not preset fields | mismatch | nit | S | ask-owner |
| APP-48 | set_iso_auto gains enabled=false (lock at the measured gain) | new-ground | nit | S | keep-and-document |
| APP-49 | Second include block after the JPEG #if; util/ headers ahead of public headers | mismatch | nit | S | fix-later |
| APP-50 | Core's liblj92 README.apertar.md says 'in the UI' | docs | nit | S | fix-later |

## APP-1. Boot Config writes free text into config.txt as root through a 1355-line in-place editor

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| security | blocker | L | yes | ask-owner | App-1-F6, App-1-F7, App-1-F9, X-protocol-security-1 |

**Where.** `src/hardware/BootConfigText.hpp:1-1355@cinemate-port`; `src/ApertarCoreApp.cpp:3651-3850@cinemate-port`; `src/ApertarCoreApp.cpp:14586-14590@cinemate-port`; `scripts/apertar-boot-config:37-54@cinemate-port`

**Problem.** set_boot_config text= (the card's Edit file) carries the whole of /boot/firmware/config.txt from any LAN client. Core checks only size and NUL bytes and writes it as root; kernel=, cmdline=, os_prefix=, initramfs and dtoverlay= all pass, so one bad or hostile save leaves the Pi unbootable. Around this sits a header-only module with a parser, board rules, link frequencies, a line diff, a review step, a revision check and nested replies (boot_config{state{},drm[],text}, changes[]); most of it exists only because arbitrary lines are edited in place.

**Apertar way.** Upstream touches config.txt only through one generated, Apertar-managed block: fanModeBlock / stripManagedFanBlock / applyFanMode (src/ApertarCoreApp.cpp:3042, :3084, :3127@upstream-1.6.0); the LAN picks one of fixed values (set_fan_mode, App:10568@upstream-1.6.0). Fixed helper command lines only, 'never accept paths from WebUI/config' (App:1543@upstream-1.6.0; WEB-6/C1-N10). Code with I/O is a .hpp/.cpp pair (src/hardware/GpioInput.{hpp,cpp}@upstream-1.6.0); header-only modules are pure logic of about 200 lines (src/camera/DefaultTuningSelection.hpp). Replies are flat, one object per topic at most (imuStatusBody "imu":{...}, App:130@upstream-1.6.0; CMD-9).

**Rework.**

1. Owner answers the question below first.
2. Answer A: delete the text= path from bootConfigSet (src/ApertarCoreApp.cpp:3775-3850) and the Edit file control in WCP (WCP editor owns the page side).
3. Write dtparams, RP1 clock and per-port link frequency as one Apertar-managed block, copied from fanModeBlock / stripManagedFanBlock (App:3042-3110@upstream-1.6.0): begin/end marker lines, stripped and rewritten on each save.
4. Sensor overlays keep a narrow in-place edit: comment or uncomment the existing dtoverlay=imx... lines and camera_auto_detect, nothing else.
5. Split what is left into src/hardware/BootConfig.hpp (types, pure parse) and src/hardware/BootConfig.cpp (read, build block, write); drop the line diff, the review step and the drm list.
6. Reply: okReply with one flat "boot_config":{...} object of scalars, like imuStatusBody; changes[] becomes a count or goes; drm[] becomes a count of connected connectors.
7. Answer B: keep text=, but in bootConfigSet refuse any change to kernel, cmdline, os_prefix, initramfs, start_file, fixup_file, device_tree, overlay_prefix and boot_* (bootconf::lineChanges against the file on disk) with errorReply(id, "config.txt: <key> is not changed from the WebUI."); write only through the helper (APP-4); move the module to BootConfig.{hpp,cpp} anyway and document it as new ground.

**Owner decision.** Keep the free-text 'Edit file' on the Boot Config card? Recommendation: no (A). A costs the free editor (operators edit config.txt over ssh, as in 1.6.0) and about 800 lines of rework, and leaves a block the original developer recognises from the fan mode. B keeps the feature but keeps the 1355-line module, the diff and review machinery and a root write of LAN text that must be documented as new ground and defended to the original developer.

**Check here.** check_core.sh /home/user/wt/core-work core-work both tests; tools/boot_config_test.cpp rewritten against the managed block (g++ -std=c++20 -O2 -Wall -Wextra -I src -I include tools/boot_config_test.cpp -o /tmp/bc && /tmp/bc); with APERTAR_BOOT_CONFIG pointing at a copy until APP-4 lands, save from the card in --simulate and diff the copy.

**Needs the Pi.** Save each card field, reboot, confirm the Pi boots and the sensor comes up: sudo cat /boot/firmware/config.txt | sed -n '/apertar/,/apertar/p'; vcgencmd get_config int | grep -i dtparam.

**Risk.** A Pi whose config.txt was already edited by the port's card keeps those in-place lines; the first save must not duplicate them in the new block.

## APP-2. Storage pre-roll runs by itself: a raw take at every boot, card insert and format

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| stock | blocker | S | yes | fix-now | App-4-F4, X-knobs-3, X-stock-behaviour-5 |

**Where.** `src/util/StoragePreroll.hpp:98@cinemate-port`; `src/ApertarCoreApp.cpp:5069-5072@cinemate-port`; `src/ApertarCoreApp.cpp:10945-10960@cinemate-port`; `src/ApertarCoreApp.cpp:12588-12592@cinemate-port`

**Problem.** automaticEnabled() returns conf.automatic.value_or(true) (confirmed, StoragePreroll.hpp:98). A stock camera with no [media] preroll key records a 2 s take at the mode's maximum fps (0.7-1.5 GB) and deletes it at every Core start, card insert and format. While it runs, record_start, capture_photo, format, eject, standby and four more answer 'Storage pre-roll is running. One moment.'

**Apertar way.** 1.6.0 has no pre-roll: power on and record. The port's own plan said 'default off at first' (KB working/drop-frames/README.md:341) and the KB says no measurement exists for the automatic triggers.

**Rework.**

1. StoragePreroll.hpp:98: value_or(false).
2. defaultHardwareConfigTemplate() (App:5069-5072): template line '# preroll=off' with one comment sentence.
3. Keep the manual command (renamed in APP-28) and the WebUI switch.
4. README: one operator sentence under the storage section (lands with APP-18).

**Owner decision.** None.

**Check here.** check_core.sh /home/user/wt/core-work core-work both tests; tools/storage_preroll_test.cpp asserts the default is off; --simulate start log shows no pre-roll request.

**Needs the Pi.** Fresh boot with no preroll key: journalctl -u apertar-core -b | grep -i preroll shows nothing; insert a card and press record at once: it records.

**Risk.** The rig that relies on it sets preroll=on in its own file.

## APP-3. Boot Config has a second HTTP door with its own lock, header revision, Origin test and status codes

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| mismatch | major | M | yes | fix-now | App-1-F4, App-3-F1, App-3-F4, X-protocol-security-7, App-1-F18 |

**Where.** `src/ApertarCoreApp.cpp:9161-9198@cinemate-port`; `src/ApertarCoreApp.cpp:3512-3516@cinemate-port`; `src/ApertarCoreApp.cpp:3709-3718@cinemate-port`; `src/ApertarCoreApp.cpp:3761-3841@cinemate-port`; `src/ApertarCoreApp.cpp:8633-8641@cinemate-port`; `src/web/WebControlPage.cpp:20004-20017@cinemate-port`

**Problem.** POST /api/boot-config finds the first '{' in the body, splices "cmd":"set_boot_config" into it, runs parseControlCommand and calls bootConfigSet outside handleCommand under its own bootConfigMutex(). It reads the revision from an X-Apertar-Revision header and refuses a request with an Origin header and no revision (409 old_page); the socket path reaches the same function with browser=false and no such rule. BootConfigReply{status, body} returns 200/400/403/409/500. boolFieldValue accepts on/yes/off/no as a second boolean parser.

**Apertar way.** A field change goes through POST /api/command -> handleWebCommand -> handleCommand (App:7085-7091, :7637-7641@upstream-1.6.0; WEB-3/C1-S09), one flat chain under commandMutex_ (CMD-2, CMD-3). set_fan_mode writes config.txt from inside handleCommand (App:10568@upstream-1.6.0). Route parameters travel in the query (queryParameterValue, App:7440@upstream-1.6.0). Core and page ship together, no page-version concept (CMD-30). Booleans are tested *enabled == "true" || "1" (CMD-8/C1-I05).

**Rework.**

1. Delete the POST /api/boot-config write route (App:9170-9198), BootConfigReply and bootConfigMutex(); set_boot_config and get_boot_config stay ordinary handleCommand blocks (App:14586-14590) returning okReply / errorReply under commandMutex_.
2. Drop the browser parameter of bootConfigSet and the Origin test; revision becomes a plain command field, required on every non-dry-run save; a stale revision is refused with a sentence ('config.txt changed since the page read it. Reload the card.').
3. WCP bootConfigPost: sendCommand({cmd:'set_boot_config', ..., revision}) to /api/command; on any refusal re-read with get_boot_config (WCP editor).
4. Keep GET /api/boot-config as the read twin of GET /api/config. Fold POST /api/boot-config/parse into set_boot_config dry_run=true, or keep it as a raw-body file route shaped like POST /api/config (App:7175-7195@upstream-1.6.0).
5. Delete boolFieldValue; use the upstream hand test with the existing '<field> must be true or false.' refusal for other text.

**Owner decision.** None.

**Check here.** check_core.sh /home/user/wt/core-work core-work both tests; in --simulate with APERTAR_BOOT_CONFIG on a copy: curl -s localhost:8011/api/command -d '{"cmd":"set_boot_config","dry_run":"true"}' replies okReply; POST /api/boot-config answers 404.

**Needs the Pi.** Save from the card twice from two tabs: the second gets the stale sentence; config.txt changes once.

**Risk.** An open WebUI tab from the old build posts to the removed route and gets 404 until reloaded.

**Depends on.** APP-1, APP-5

## APP-4. Three write routes for config.txt; the helper breaks fan mode on files without [pi5]/[pi4]/[all]; operator errors carry shell commands

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| mismatch | major | S | yes | fix-now | App-1-F11, App-1-F12, App-1-F8, Build-scripts-docs-F5, X-knobs-16 |

**Where.** `src/ApertarCoreApp.cpp:3519-3610@cinemate-port`; `src/ApertarCoreApp.cpp:3425-3447@cinemate-port`; `src/ApertarCoreApp.cpp:3733@cinemate-port`; `scripts/apertar-boot-config:51-53@cinemate-port`

**Problem.** writeBootConfigText tries a direct write (as root, or to the APERTAR_BOOT_CONFIG copy) with its own fsyncPath and temp/fsync/rename sequence, then the apertar-boot-config helper on stdin, then sudo -n install twice. With the helper installed, fan mode fails on a config.txt that has only [cm4]/[cm5] sections or none (the helper exits 2, confirmed at scripts/apertar-boot-config:51-53), where 1.6.0 wrote any file. Errors pass the helper's stderr and two 'sudo install ...' command lines to the operator, and name wire fields ('<port>_link_frequency must be ... or null', 'Send confirm_display=true').

**Apertar way.** One route: sudo -n install -m 644 <tmp> /boot/firmware/config.txt (App:3155-3158@upstream-1.6.0); a missing rule becomes 'Changing the fan mode needs sudo permission.' (App:3164@upstream-1.6.0; PLT-5, STY-10). Atomic writes go through settingsFile::atomicWrite (src/util/SettingsFile.hpp:36-55@upstream-1.6.0).

**Rework.**

1. writeBootConfigText: keep only the upstream sudo -n install route, with the backup install line (App:3595) before it. Delete the direct-write branch, fsyncPath and the helper branch (helper itself goes with APP-13).
2. Delete APERTAR_BOOT_CONFIG (App:3505-3510); give the writer a path parameter so the host test writes a temp copy through settingsFile::atomicWrite.
3. Operator sentences: 'Changing config.txt needs sudo permission.'; 'The display connector changes with this save. Save again to confirm.' Remove field names and shell commands; log the raw output with std::cerr instead (STY-7).
4. If the owner keeps the helper (APP-13 answer B): drop its section check so fan mode works on every file; map exit codes 2 and 3 to sentences.

**Owner decision.** None.

**Check here.** check_core.sh /home/user/wt/core-work core-work both tests; boot_config_test writes a temp file through the path parameter; tools/boot_config_helper_test.sh goes with the helper.

**Needs the Pi.** On a CM4/CM5 image whose config.txt has only [cm5]: set_fan_mode value=quiet succeeds and the fan block appears.

**Risk.** None beyond losing the narrow sudoers rule, which never confined Core (X-protocol-security-9).

**Depends on.** APP-13

## APP-5. errorReplyBody: a third reply builder with machine error codes and extra members

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| mismatch | major | M | yes | fix-now | App-1-F5, App-3-F5, App-3-F6, App-4-F20 |

**Where.** `src/ApertarCoreApp.cpp:173-184@cinemate-port`; `src/ApertarCoreApp.cpp:3787-3841@cinemate-port`; `src/ApertarCoreApp.cpp:8460-8569@cinemate-port`; `src/ApertarCoreApp.cpp:8687@cinemate-port`; `src/ApertarCoreApp.cpp:8816@cinemate-port`; `src/ApertarCoreApp.cpp:12801-12927@cinemate-port`

**Problem.** 15 call sites send ok:false with "code":"invalid|unreadable|old_page|stale|refused|confirm_display|permission|write_failed" plus revision, drm and issue arrays (Boot Config, set_controls, /api/config, set_buffer_mode, set_frames_per_folder, set_storage_preroll). Playback routes hand-build 409 bodies at five sites ('Playback held: media_test. Downloads wait.'), {"ok":false,"busy":true} with no error sentence (App:8532) and a gone flag (App:8506). The WebUI branches on result.code (WCP:18233, :18661, :18948, :20329). App-3-F5 proposed reusing errorReplyBody for the hold replies; that contradicts App-1-F5 and CMD-9, so it is not taken.

**Apertar way.** Replies come only from okReply(id, fragment) and errorReply(id, sentence) (App:108-128@upstream-1.6.0; CMD-9); grep '"ok":false' in upstream App finds only errorReply itself. HTTP routes give the machine meaning in the status code with errorReply(-1, sentence) as body: 400, 404, 500 and 503 'Folder downloads need the zip package installed.' (App:7224-7226@upstream-1.6.0). Busy sentences: 'Stop recording before deleting media.' (App:7514), 'Wait for the media speed test to finish first.' (App:9110@upstream-1.6.0; STY-10).

**Rework.**

1. Delete errorReplyBody (App:173-184).
2. Socket commands: every refusal is errorReply(id, sentence). Stale revision: a sentence, and the client re-reads (get_boot_config, GET /api/config). Display guard: answer okReply with "display_changed":true,"written":false as dry_run already does; the card resends with confirm_display. Hardware-file issues: one sentence; details come from the existing GET /api/config.
3. HTTP routes: status carries the meaning (409 held or stale, 410 gone, 503 busy) and the body is errorReply(-1, sentence).
4. Add holdSentence(playback::Hold) in the anonymous namespace: recording 'Stop recording before downloading media.', writing 'Wait for the current capture to finish writing to media.', media_test 'Wait for the media speed test to finish first.', standby 'Wake the camera first.', media 'Mount media first.'. Use it at all six hold sites including /api/media/clip (App:8460).
5. busy (App:8532): 409 + errorReply(-1, 'The player is busy. One moment.'); gone (App:8506): 410 + errorReply(-1, 'This clip was removed.').
6. WCP readers switch from result.code to the HTTP status or a re-read (WCP editor; set_controls readers with the HW-config-text-store editor).
7. 'scan_i2c needs bus= (...)' becomes 'scan_i2c requires bus.'; drop errno from 'Media is not answering (errno N)' and log it.

**Owner decision.** None.

**Check here.** check_core.sh /home/user/wt/core-work core-work both tests; smoke_core.sh <build>/apertar-core 8011 before/after and diff; browser on http://localhost:8011 against --simulate: no reply anywhere contains "code":; grep -c errorReplyBody src/ApertarCoreApp.cpp = 0.

**Needs the Pi.** Nothing beyond the general smoke test.

**Risk.** The WCP and Controls card readers must change in the same commit.

**Depends on.** APP-3

## APP-6. Preview temporal denoise off by default also strips TDN from H.264 and ProRes recordings

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| stock | major | S | yes | ask-owner | Build-scripts-docs-F11, X-knobs-4, X-stock-behaviour-6 |

**Where.** `include/apertar/core/Types.hpp:139@cinemate-port`; `src/camera/CameraController.cpp:7302-7318@cinemate-port`; `src/camera/CameraController.cpp:7412@cinemate-port`; `README.md:315-325@cinemate-port`

**Problem.** bool previewTdn = false. Core hands libcamera a _notdn.json copy of the tuning file for every record format, and makeProresIspTuning derives the ProRes tuning from the stripped file. For H.264 and ProRes the ISP output is the recording, so a stock camera records them without temporal denoise, even with a tuning file the user picked (against the comment at CC:7302). The README speaks of DNG previews only; the reason was measured once on one rig.

**Apertar way.** libcamera loads the selected tuning file unchanged (scripts/start-apertar-core.sh:15-18, src/camera/DefaultTuningSelection.hpp@upstream-1.6.0).

**Rework.**

1. Always: in the loadablePath lambda (CC:7309-7318) strip only when the format records raw frames and the file is the default: if (!settings.previewTdn && !isProcessedVideoFormat(settings.recordingFormat) && !settings.photoModeEnabled && !userPickedTuning). isProcessedVideoFormat exists at CC:280 and upstream.
2. Confirm a format change re-runs start() (setRecordingFormat -> applySettingsLocked(next, requiresReconfigure), CC:11390) so the right file loads.
3. Answer A: Types.hpp:139 previewTdn = true; the rig sets preview_tdn=false.
4. Answer B: keep false for raw formats; one README sentence and a handoff line with the measurement.

**Owner decision.** Default preview TDN back to on (1.6.0 behaviour) or keep it off for raw formats? Recommendation: on (A) plus the format test. A costs the rig one camera_settings.conf line. B keeps a noisier DNG preview for every stock camera after the update, which must be stated to the original developer with the one measurement behind it.

**Check here.** check_core.sh /home/user/wt/core-work core-work both tests; tools/tuning_tdn_strip_test.cpp extended: H.264 and ProRes keep tdn.

**Needs the Pi.** Record H.264 and ProRes with defaults: journalctl -u apertar-core | grep -i tuning shows the original file, not _notdn.json.

**Risk.** The camera editor may hold the CC half; one commit for both.

## APP-7. A second dispatcher answers six commands before the command lock

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| mismatch | major | M | yes | fix-now | App-4-F1, X-protocol-security-5, App-1-F13, App-4-F20 |

**Where.** `src/ApertarCoreApp.cpp:12418-12556@cinemate-port`; `src/ApertarCoreApp.cpp:12558-12571@cinemate-port`; `src/ApertarCoreApp.cpp:291-299@cinemate-port`

**Problem.** handleReadOnlyHardwareCommand answers get_controls, controls_history, controls_last_input, scan_i2c and list_actions before commandMutex_ (confirmed, App:12560-12561); test_input and abortSafetyStopFlushForRecord also run before it. get_controls is not read-only: it writes controlsErrors_/controlsWarnings_, erases pendingUnitSince_, spawns systemctl show and parses the same text 8 times, and returns a deeply nested object that repeats what GET /api/config returns. scan_i2c checks for a take once, then probes up to 117 addresses unlocked.

**Apertar way.** One flat chain under one lock taken on the first line of handleCommand (App:9091-9093@upstream-1.6.0; CMD-2, CMD-3). The WebUI reads the hardware file lock-free through GET /api/config -> buildHardwareConfigFileJson (App:7168-7173@upstream-1.6.0). Slow work that must not hold the lock is a worker with polled state, like the media speed test (CMD-21).

**Rework.**

1. Extend buildHardwareConfigFileJson with revision, written_by, issues, replaced, model, peripherals, i2c_buses, apply, dpi_lines; parse the document once into a local.
2. Add GET /api/config/history[?name=] in handleWebRequest next to GET /api/config.
3. Move controls_last_input, list_actions and scan_i2c into ordinary handleCommand blocks under the lock (upstream accepts slow work under the lock, rough edge 18); if the scan is too slow, make it a worker like run_media_speed_test.
4. Move the systemctl show probe into runControlsWorker; get_controls stops writing counters.
5. Delete handleReadOnlyHardwareCommand. Keep test_input as the one pre-lock exception with its one comment line (its actions re-enter handleCommand).
6. abortSafetyStopFlushForRecord stays before the lock until the drain stops holding commandMutex_ (APP-10); then it moves into the record_start block.
7. WCP controlsCall({cmd:'get_controls'}) becomes fetch('/api/config') (WCP editor).

**Owner decision.** None.

**Check here.** check_core.sh /home/user/wt/core-work core-work both tests; smoke_core.sh <build>/apertar-core 8011 before/after and diff; browser on http://localhost:8011 against --simulate: GET /api/config carries the new members; get_controls answers 'Unknown command'.

**Needs the Pi.** Run scan_i2c bus=1 while idle and press record during it: record waits for the scan, then starts.

**Risk.** The Controls card must switch to /api/config in the same commit.

**Depends on.** APP-5

## APP-8. test_input lets a LAN client run any readable file with bash, without a button press

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| security | major | S | no | fix-now | X-protocol-security-2 |

**Where.** `src/ApertarCoreApp.cpp:12393-12415@cinemate-port`; `src/ApertarCoreApp.cpp:12565-12566@cinemate-port`; `src/hardware/HardwareScriptRunner.cpp:86-90,231-238@cinemate-port`

**Problem.** test_input section=gpio_buttons key=remote0 runs whatever the saved file maps to that key through handleHardwareInputAction (confirmed, App:12410); remoteN rows skip the section-on check. A LAN client saves [run_script] path1=<file> and remote0=run_script1 through POST /api/config, then calls test_input: the runner executes /bin/bash -- <file> as pi, who has NOPASSWD sudo on the stock image.

**Apertar way.** Same runner checks upstream (HardwareScriptRunner.cpp:88-89, :238@upstream-1.6.0), but handleHardwareInputAction is called only from the GPIO, NeoRotary and PCF8574 callbacks and the standby wake (App:6786-6792, :8613@upstream-1.6.0): a script runs only on a physical press.

**Rework.**

1. In testInputReply, before handleHardwareInputAction: for (const auto &a : line.actions) if (hardware::scriptActionSlot(a) >= 0) return errorReply(command.id, "Scripts run from a button, not from the WebUI.");
2. The WebUI Try button greys rows whose action is run_scriptN (WCP editor).

**Owner decision.** None.

**Check here.** check_core.sh /home/user/wt/core-work core-work both tests; --simulate: save remote0=run_script1 and send test_input: the reply is the refusal sentence and nothing runs.

**Needs the Pi.** A physical button mapped to run_script1 still runs the script.

**Risk.** None.

## APP-9. Environment knobs in the command plane override saved settings and surface as *_env state

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| knob | major | M | yes | fix-now | App-1-F3, App-2-F5, App-4-F5, App-3-F3, X-knobs-8, X-knobs-9 |

**Where.** `src/ApertarCoreApp.cpp:88-106@cinemate-port`; `src/ApertarCoreApp.cpp:260-285@cinemate-port`; `src/ApertarCoreApp.cpp:6399-6404@cinemate-port`; `src/ApertarCoreApp.cpp:9583-9586@cinemate-port`; `src/ApertarCoreApp.cpp:11154@cinemate-port`; `src/camera/CameraController.cpp:4293@cinemate-port`; `src/camera/CameraController.cpp:5503@cinemate-port`

**Problem.** App reads 17 APERTAR_* variables (upstream: 2 lines, one variable). APERTAR_CDNG_BUFFER, APERTAR_STORAGE_PREROLL, APERTAR_CDNG_FRAMES_PER_FOLDER, APERTAR_CLIP_MERGE and APERTAR_MEDIA_TRIM beat the switch the operator set in the WebUI; four state fields (storage_preroll_auto_env, frames_per_folder_env, clip_merge_env_off, media_trim_env_off) and 8 WCP uses exist only to explain the override. APERTAR_WEB_PREVIEW_RECORDING_FPS is an A/B leftover ('Not run on the Pi', fb557e9) whose default equals the old constant. mediaTrimSetting_ copies a camera setting.

**Apertar way.** App reads only APERTAR_HARDWARE_CONFIG (App:4254@upstream-1.6.0; CMD-23). A bench knob is read once at the point of use in the owning subsystem, overrides no saved setting and stays out of state, settings files and README (src/lossydng/LossyDngEncoder.cpp:98-105, :325@upstream-1.6.0; CAM-24, recipe R8). App keeps no copy of settings (App:7715@upstream-1.6.0; CMD-13).

**Rework.**

1. Delete the env reads of APERTAR_CDNG_BUFFER, APERTAR_STORAGE_PREROLL, APERTAR_CDNG_FRAMES_PER_FOLDER, APERTAR_CLIP_MERGE (App:266-285, BufferBudget.hpp:303-330, StoragePreroll.hpp) and APERTAR_MEDIA_TRIM (App:6402) plus the CC twin at CC:4293/:5503. A test script sends the socket command instead.
2. Delete the four *_env state fields in bufferSettingMembers / mediaTrimStateJson / clipMergeStateJson and the WCP greying (WCP editor).
3. Delete mediaTrimSetting_ and mediaTrimEnvOff(); the trim worker reads camera_.settings().mediaTrimEnabled when it decides.
4. APERTAR_WEB_PREVIEW_RECORDING_FPS: delete webPreviewRecordingFps(), the rawTakeActive branch (App:9778-9784) and the README row; kWebPreviewMaxFps stays the constant. If the Pi test shows a need, one fixed reduced rate during raw takes, no knob.
5. APERTAR_MEDIA_MIN_FREE_MB: constexpr uint64_t kMinFreeMiB = 1024 beside the gate. APERTAR_MEDIA_REQUIRE_MOUNT goes with APP-23, APERTAR_MEDIA_TUNE with APP-13.
6. X-knobs-9's other names (CC, encoders, driver, playback, audio) are for their owning editors; here only App, the start script (APP-15) and README (APP-18).

**Owner decision.** None.

**Check here.** check_core.sh /home/user/wt/core-work core-work both tests; grep -c 'getenv("APERTAR' src/ApertarCoreApp.cpp drops to 1 (HARDWARE_CONFIG) plus any knob the owner keeps; smoke_core.sh <build>/apertar-core 8011 before/after and diff; browser on http://localhost:8011 against --simulate: no *_env field.

**Needs the Pi.** Nothing beyond the general smoke test.

**Risk.** A campaign script that set these variables in the unit must send the command instead.

## APP-10. [storage] parsed by App and by CameraController; live state shared through header singletons and global std::function hooks

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| mismatch | major | L | unknown | fix-now | App-1-F2, App-2-F3, App-4-F6, App-3-F8, App-2-F15 |

**Where.** `src/ApertarCoreApp.cpp:273-286@cinemate-port`; `src/ApertarCoreApp.cpp:7987-7994@cinemate-port`; `src/ApertarCoreApp.cpp:6335-6352@cinemate-port`; `src/util/BufferBudget.hpp:224-333@cinemate-port`; `src/util/StoragePreroll.hpp:224-249@cinemate-port`; `src/camera/CameraController.cpp:2989-3005@cinemate-port`; `src/camera/CameraController.cpp:4629@cinemate-port`; `src/camera/CameraController.cpp:5018@cinemate-port`

**Problem.** App's refreshBufferRequest parses [storage] from hardware::configStore() twice per call (and start() calls it twice) and stores the result in header-level function-static atomics only App reads. CC parses [storage] again at take start with its own path search (loadBufferConf). App and CC also share safetyStopState(), bufferSettingStorage(), flushAbortFunction() and safetyStopHook(), a static std::function that App's constructor body assigns and the DNG write queue calls; it captures this and outlives App. The playback yield window is a file-scope static in App (playbackYield()). After a save the two parsers can disagree: state shows one frames_per_folder while CC records with another.

**Apertar way.** Each hardware-file section has one owner, the class that parses it (CMD-12/C1-S07). Parts reach App only through std::function callbacks passed in the constructor: camera_([this](const std::string &eventJson){ publishEvent(eventJson); }, ...) (App:6783-6792@upstream-1.6.0; CMD-18). Cross-thread flags are std::atomic members of the owner (AppH:110-176@upstream-1.6.0; CMD-20). Function-static singletons only file-local in the owner's .cpp (captureSettingsPersister(), CC:885-889@upstream-1.6.0). Upstream src has no static std::function.

**Rework.**

1. CameraController owns [storage]: one loadBufferConf, read in start() and in a new camera_.reloadStorageOptions(), which replaces App's 7 refreshBufferRequest() calls (one call in start(), before the first worker).
2. App reads camera_.storageOptions() and camera_.bufferSettingStatus() for state and the merge worker.
3. Safety-stop flags become std::atomic members of CC behind a getter; safetyStopHook becomes a std::function<void(const SafetyStopHit&)> constructor parameter of CameraController beside the event and preview callbacks, stored and handed to DngRecordingQueue as a member. Same for flushAbortFunction (CC:4629).
4. abortSafetyStopFlush becomes camera_.abortSafetyStopFlush(), taking only the queue's mutex.
5. playbackYield_ becomes a member in ApertarCoreApp.hpp (PlaybackHold.hpp pulls only <atomic>, <cstdint>); the streams take [this]{ return playbackYield_.active(nowMs()); }. clipFactsCache() stays a function-local static (cache, upstream precedent App:2269-2272).
6. Delete the singletons in BufferBudget.hpp and StoragePreroll.hpp; the pure parse and plan functions stay, with their host tests.
7. hardware::configStore(): leave to the HW-config-text-store editor (store as an App member passed by reference).

**Owner decision.** None.

**Check here.** check_core.sh /home/user/wt/core-work core-work both tests (buffer_budget_test, storage_buffer_conf_test, storage_preroll_test still pass); grep -n 'static std::function\|inline .*&.*()' src/util/*.hpp shows none with state.

**Needs the Pi.** cDNG take that fills the RAM buffer to the stop percent: the safety stop fires once, record_stop arrives through handleCommand, the clip closes: journalctl -u apertar-core | grep -i 'safety'.

**Risk.** The write queue construction path inside CC must carry the callback; test a safety stop on the Pi before merge.

## APP-11. Storage switches inline the hardware-store edit three times; one family of recording switches spread over two stores

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| mismatch | major | M | yes | ask-owner | App-5-F1, App-2-F5, X-knobs-7 |

**Where.** `src/ApertarCoreApp.cpp:12827-12927@cinemate-port`; `src/util/BufferBudget.hpp:150-195@cinemate-port`; `src/util/StoragePreroll.hpp:46-88@cinemate-port`; `src/ApertarCoreApp.cpp:13194-13212@cinemate-port`

**Problem.** set_buffer_mode, set_frames_per_folder / set_clip_merge and set_storage_preroll each build StoreFlags{backup, trusted=true}, call hardware::configStore().edit(...), return errorReplyBody with code/revision/issues, update the controls counters, wake the controls worker, refresh the buffer request and reply revision/written/apply plus bufferSettingMembers(). flags.trusted bypasses the store's text-mode-only rule. Meanwhile set_media_trim and set_preview_tdn from the same port store in camera_settings.conf. The unit reports disagree on the home: App-2-F5 and X-knobs-7 move the keys to camera_settings.conf, App-5-F1 keeps them in the hardware file.

**Apertar way.** An operator command that persists one hardware-file key calls the section owner's setter from a plain block: if (!Mpu6050RecordingSession::setConfiguredDriver(*value, &errorMessage)) return errorReply(command.id, errorMessage); return okReply(command.id, imuStatusBody(false)); (App:9646-9655@upstream-1.6.0); the owner calls writeHardwareConfigValue(path, "imu", "driver", ...) (Mpu6050RecordingSession.cpp:604, :1295-1300@upstream-1.6.0). A persisted camera switch set by a command is a CaptureSettings member saved by CC (recipe R2, CMD-12).

**Rework.**

1. Answer A (hardware file, recommended): add one owner function beside the [storage] parser in CameraController (APP-10 makes CC the owner): bool saveStorageKey(const std::string &section, const std::string &key, const std::string &value, std::string *error); it does the store edit with trusted (one comment line), the controls counts and the worker wake, then reloadStorageOptions().
2. Each App block becomes: check the value; if (!camera_.saveStorageKey("storage", "buffer", *value, &error)) return errorReply(command.id, error); return okReply(command.id, bufferSettingMembers()); plus clipMerge("switch") when merge is switched on.
3. Drop revision/written/issues/apply from these replies (grep WCP:14027-14031 and Apertar-UI ApertarControlBridge.cpp:621-627 first).
4. Move preroll from [media] to [storage] so the family has one section; the store migrates an existing [media] preroll key once.
5. Answer B (camera_settings.conf): five CaptureSettings members (bufferRam, framesPerFolder, clipMerge, storagePreroll, storagePrerollSeconds) saved after media_trim= (CC:976), carried across formats like mediaTrimEnabled (CC:11348-11367), setters shaped like setMediaTrimEnabled, preset keys; delete parseBufferConf/parsePrerollConf and the [storage]/[media] keys with a one-time migration.

**Owner decision.** Where do buffer mode, frames per folder, clip merge and pre-roll live: apertar-hardware.conf [storage] (A) or camera_settings.conf (B)? Recommendation: A. It has upstream precedent (set_imu_* write the hardware file through the section owner), keeps buffer next to buffer_ram_*/buffer_stop_percent, and is about a day of work. B matches media_trim and lets presets carry the switches, but touches CC load/save, profiles, presets, both UIs and needs a migration (several days).

**Check here.** check_core.sh /home/user/wt/core-work core-work both tests; --simulate: set_buffer_mode value=ram then get_state shows it; apertar-hardware.conf in the sim home has the key once; reply is a plain okReply.

**Needs the Pi.** Nothing beyond the general smoke test.

**Risk.** WCP and the touch bridge may read revision/written from the reply.

**Depends on.** APP-10, APP-5

## APP-12. Storage pre-roll worker starts and finishes a camera take outside handleCommand

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| mismatch | major | L | yes | fix-now | App-4-F2 |

**Where.** `src/ApertarCoreApp.cpp:11121-11144@cinemate-port`; `src/ApertarCoreApp.cpp:11254-11297@cinemate-port`

**Problem.** runStoragePrerollOnce takes commandMutex_ itself, runs its own copy of the busy guards (storagePrerollGuard -> storagepreroll::decideGuard), calls camera_.startStoragePreroll, then watches the clock and calls camera_.finishStoragePreroll without any lock. That is a third and fourth take start/stop path beside the command chain, with guards kept in step by hand.

**Apertar way.** Every camera state change enters through handleCommand (CMD-1/C1-S01). The idle timer builds ControlCommand enter_standby and calls handleCommand (App:7041-7047@upstream-1.6.0). Timed camera work lives in CameraController (timelapseLoop, CC:8447@upstream-1.6.0). The port's own safety stop does it right: record_stop via dispatchHardwareInputCommand (App:11107-11109@cinemate-port).

**Rework.**

1. The worker keeps request/coalesce and the settle wait, then builds ControlCommand storage_preroll_start (trigger, seconds) and calls handleCommand, as the idle timer does.
2. The storage_preroll_start block relies on the head guards (App:12588-12592) and checks only camera ready, not still mode, raw format; then camera_.startStoragePreroll(seconds).
3. Length and finish move into CameraController on a timer thread shaped like timelapseLoop; it emits the end through the existing event callback.
4. Delete storagePrerollGuard and the guard fields the head guards already cover.

**Owner decision.** None.

**Check here.** check_core.sh /home/user/wt/core-work core-work both tests; storage_preroll_test keeps the pure plan; --simulate storage_preroll_start answers like any command.

**Needs the Pi.** storage_preroll_start with a card in: the clip is written, drained and deleted; record_start right after works.

**Risk.** The finish must still wait for the drain and delete the clip; finishStoragePreroll already lives in CC.

**Depends on.** APP-2, APP-10, APP-28

## APP-13. Three root helpers as /bin/sh scripts with sudoers and tmpfiles inside Core; trim switch says on without the helper

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| mismatch | major | M | yes | fix-now | Build-scripts-docs-F4, Build-scripts-docs-F6, X-knobs-10, X-protocol-security-9, App-4-F11, X-stock-behaviour-11, X-knobs-16 |

**Where.** `scripts/apertar-boot-config@cinemate-port`; `scripts/apertar-media-trim@cinemate-port`; `scripts/apertar-media-tune@cinemate-port`; `config/apertar-boot-config.sudoers@cinemate-port`; `config/apertar-media-trim.sudoers@cinemate-port`; `config/apertar-media.sudoers@cinemate-port`; `config/apertar-media.tmpfiles.conf@cinemate-port`; `src/ApertarCoreApp.cpp:11393-11435@cinemate-port`; `src/ApertarCoreApp.cpp:11505-11514@cinemate-port`

**Problem.** POSIX sh helpers in Core scripts/, sudoers and tmpfiles in Core config/, install recipes in the README and config headers. Core calls apertar-media-tune although nothing installs it, and with sudo -n but no /usr/bin/timeout, on the media watcher thread. apertar-media-tune keeps root state under a pi-owned /run/apertar-media (symlink plant possible once installed) and its sudoers rule pins the path, not the arguments. The rules confine nothing: Core still needs full sudo for the upstream paths. mediaTrimEnabled defaults to true while no trim helper is installed on a stock image; the worker logs once and the WebUI shows trim on with media_trim_last_result empty.

**Apertar way.** Simple privileged tools are called directly: sudo -n install (App:3157), sudo -n mount (App:3623), sudo -n blockdev --flushbufs (App:3353@upstream-1.6.0; PLT-5); an optional tool is probed with std::filesystem::exists and skipped. A real root program is Qt-free C++ in the UI repo, called as /usr/bin/timeout 6s /usr/bin/sudo -n /usr/local/libexec/apertar-standby-usb <verb> (App:1544@upstream-1.6.0) with a sudoers file listing every verb (UI/systemd/apertar-standby-usb.sudoers@upstream-1.6.0; PLT-4, PLT-6). No #!/bin/sh file in either upstream tree (STY-16).

**Rework.**

1. Trim: in the trim worker call /usr/bin/timeout 20s /usr/bin/sudo -n /usr/sbin/fstrim -v <shellQuote(media root)>; the discard and mount checks move into App beside it. Delete scripts/apertar-media-trim, config/apertar-media-trim.sudoers and tools/media_trim_test.sh.
2. When fstrim is missing (std::filesystem::exists) or sudo refuses, call finish("not-available", 0, 0) so media_trim_last_result says so.
3. Media tune: delete scripts/apertar-media-tune, config/apertar-media.sudoers, applyMediaTuning (App:11393-11435), kernel_tune and APERTAR_MEDIA_TUNE. Kernel tuning, if ever wanted, is an image sysctl.d file and a udev rule.
4. Boot config: delete scripts/apertar-boot-config, config/apertar-boot-config.sudoers and tools/boot_config_helper_test.sh; config.txt goes through sudo -n install (APP-4).
5. config/apertar-media.tmpfiles.conf goes with APP-29 (eject line) and this item (tune line).
6. README: drop the three install recipes (APP-18).

**Owner decision.** None.

**Check here.** check_core.sh /home/user/wt/core-work core-work both tests; ls scripts config shows only start-apertar-core.sh and apertar-core-capture-priority.conf; --simulate media_trim state reports not-available when fstrim is absent.

**Needs the Pi.** Mount an NVMe card, wait for idle trim: journalctl -u apertar-core | grep -i trim shows fstrim output; sudo -n true succeeds as pi on the image.

**Risk.** An image built with the narrow sudoers files only (no NOPASSWD: ALL) loses trim; upstream already needs full sudo.

## APP-14. A second bench-tuning mechanism (INI, /run override, 487-line apertar-tune, tmpfiles) beside upstream's .apertar-tuning

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| duplication | major | M | yes | ask-owner | Build-scripts-docs-F1, X-knobs-6, App-4-F17 |

**Where.** `config/apertar-media-tune.conf:1-54@cinemate-port`; `scripts/apertar-tune:1-487@cinemate-port`; `src/util/MediaTune.hpp:1-318@cinemate-port`; `src/ApertarCoreApp.cpp:11400-11408@cinemate-port`; `src/cdng/CdngEncoder.cpp:86-96@cinemate-port`

**Problem.** Each write-path knob resolves through env > /run/apertar-media/media-tune.override.conf > ~/apertar-media-tune.conf (hard-coded /home/pi) > default, with its own key names (dontneed, writeback, sync_ms, raw_buffers, workers, queue, kernel_tune), per-medium sections, a 318-line parser and a 487-line Python editor. dontneed and writeback are read once per process, so a change still needs a restart; three texts disagree on when the file is read; MediaTune.hpp:5 names a test that does not exist. A fourth config file beside the three stores.

**Apertar way.** tuningOverride(name): env wins, else NAME=VALUE from /home/pi/.apertar-tuning with the same APERTAR_* names, re-read at clip open, absent in production, written for A/B arms without restart (src/prores/ProresEncoder.cpp:771-813@upstream-1.6.0; CAM-24: 'a second bench file beside .apertar-tuning' is the listed violation). Three stores only (CMD-12).

**Rework.**

1. Answer A: move tuningOverride() into src/util/TuningOverride.hpp; unsignedEnvValue and boolEnvValue (CC:1341, :1357) call it; read APERTAR_DNG_DONTNEED / APERTAR_DNG_WRITEBACK per take.
2. Per-medium defaults stay as the C++ table writerSettingsFor() in MediaProfile; echo effective values in the 'ApertarCore recording clip:' line.
3. Delete config/apertar-media-tune.conf, scripts/apertar-tune, src/util/MediaTune.hpp, the override path and the README section.
4. Answer B: keep the file, drop the /run override layer and the CLI, move the path next to the hardware file lookup (no hard-coded /home/pi), document it for the original developer as new ground.

**Owner decision.** You asked for the media-tune file on 2026-11-02. Replace it with upstream's .apertar-tuning (A) or keep it trimmed and documented (B)? Recommendation: A. A loses per-medium override sections (the per-medium defaults stay in code) and the editor script. B keeps a second tuning dialect the original developer must learn beside his own 40-line function.

**Check here.** check_core.sh /home/user/wt/core-work core-work both tests; --simulate take-start log line prints the effective write-path values; APERTAR_DNG_WRITEBACK=... in ~/.apertar-tuning changes the next take without restart (sim take).

**Needs the Pi.** A/B two cDNG takes with and without a .apertar-tuning line; the log line shows both values.

**Risk.** Campaign scripts that call apertar-tune must write .apertar-tuning instead.

**Depends on.** APP-13

## APP-15. Real-time scheduling in the start script; LimitRTPRIO=80 under upstream's 'non-real-time' comment

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| knob | major | S | yes | fix-now | Build-scripts-docs-F3, X-knobs-9 |

**Where.** `scripts/start-apertar-core.sh:20-44@cinemate-port`; `config/apertar-core-capture-priority.conf:2-7@cinemate-port`; `src/camera/CameraController.cpp:9109-9122@cinemate-port`

**Problem.** APERTAR_RT=1 prefixes exec with chrt -f 70, ionice and taskset -c 1-3; the drop-in gains an unconditional LimitRTPRIO=80 directly under '# Permit only a bounded, non-real-time boost' (confirmed). chrt is probed with /bin/true, taskset is not, so a bad APERTAR_RT_CPUS makes exec fail and Core does not start. APERTAR_RT_CAPTURE_PRIORITY was measured with no effect; whole-process RT was never measured. The comments name cinemate and the KB.

**Apertar way.** Drop-in = LimitNICE=-5 only (config/apertar-core-capture-priority.conf@upstream-1.6.0); the script ends exec "$CORE_BIN" --socket ... --media ... (scripts/start-apertar-core.sh:21@upstream-1.6.0). No affinity, no RT scheduling, only bounded nice (PLT-14); startup never blocks the camera (PLT-22).

**Rework.**

1. Restore scripts/start-apertar-core.sh lines 20-44 and the final exec to upstream (git show upstream-1.6.0:scripts/start-apertar-core.sh).
2. Restore config/apertar-core-capture-priority.conf to upstream (LimitNICE=-5 and its comment only).
3. Delete the APERTAR_RT_CAPTURE_PRIORITY block at CC:9109-9122 (camera editor may hold CC; one commit).

**Owner decision.** None.

**Check here.** diff against /home/user/wt/core-upstream for both files is empty; bash -n scripts/start-apertar-core.sh; check_core.sh /home/user/wt/core-work core-work both tests

**Needs the Pi.** sudo systemctl daemon-reload && sudo systemctl restart apertar-core; systemctl show apertar-core -p LimitRTPRIO shows 0; Core records.

**Risk.** None for stock; the rig loses an experiment arm that was never measured.

## APP-16. No first-run hardware file, and the only default lacks chip=, input tuning and [mpu6050]

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| removed | major | M | yes | fix-now | App-2-F2, X-stock-behaviour-2, App-2-F1, X-knobs-2, X-stock-behaviour-1 |

**Where.** `src/ApertarCoreApp.cpp:5081-5151@cinemate-port`; `src/ApertarCoreApp.cpp:6200-6201@cinemate-port`; `Apertar-UI/src/DisplayConfigBridge.cpp (ensureDefaultHardwareConfigFile removed in c9d841f)`

**Problem.** Done already: the [display] values of the template are 720x720/square/false again (Core 7dc6f7a, UI 6a59d83), which settles the blocker App-2-F1 / X-knobs-2 / X-stock-behaviour-1. Still open: UI c9d841f removed the first-run writer, so a fresh camera gets no file; the WebUI editor shows Core's template and its first save writes it. That template has [gpio] enabled=false, [gpio_encoders] enabled=false, no chip= key, no input tuning and no [mpu6050], and its [gpio_switches] comment says chip is read 'like [gpio]' although GpioInput.cpp:311-336 reads only enabled and switchN_* there.

**Apertar way.** Apertar-UI/src/DisplayConfigBridge.cpp:57-330@upstream-1.6.0 wrote the first-run file when /home/pi/apertar-hardware.conf was missing: [gpio_buttons] chip=auto, active_low=true, pull=up, poll_ms=12, debounce_ms=60 (:156-166); [gpio_encoders] chip=auto plus tuning (:168-183); [mpu6050] bus=1, address=0x68, gyro_range_dps=1000 and the rest (:206-232). One file, one writer per section (CMD-12).

**Rework.**

1. Fold the upstream UI first-run sections into defaultHardwareConfigTemplate(): [gpio_buttons] with chip=auto, active_low, pull, poll_ms, debounce_ms (the name the Controls code uses; [gpio] stays an alias); [gpio_encoders] chip and tuning; [mpu6050] with the UI writer's values and enabled=false.
2. [gpio_switches] comment: 'chip, pull, active_low and debounce_ms come from [gpio_buttons].'
3. First-run writer in Core, the file's single writer: in start(), when no hardwareConfigCandidatePaths() entry exists and the store has no last-written copy, write defaultHardwareConfigTemplate() through HardwareConfigStore. The replaced-file check (014fa22) keeps working for every later start.
4. Do not restore the UI writer: two writers for one file is what c9d841f fixed.

**Owner decision.** None.

**Check here.** check_core.sh /home/user/wt/core-work core-work both tests; --simulate with an empty HOME: the file appears once with the 720x720 [display] block; a second start does not rewrite it; moving it away is reported as replaced, not silently recreated.

**Needs the Pi.** Fresh SD image: after first boot ls -l ~/apertar-hardware.conf exists, the touch UI is on the 720x720 panel, GPIO buttons work with chip=auto.

**Risk.** A rig whose file was moved away on purpose must still be told, not overwritten; the store's adopt/replaced logic covers it.

## APP-17. Ticket numbers, KB paths, Cinemate hashes, banners and narration in App, its header, scripts and config

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| slop | major | M | no | fix-later | App-1-F16, App-2-F8, App-3-F7, App-4-F8, App-5-F6, Build-scripts-docs-F7 |

**Where.** `src/ApertarCoreApp.cpp (307 comment lines; 46 T<nn> matches)@cinemate-port`; `src/ApertarCoreApp.hpp:173-195@cinemate-port`; `include/apertar/core/Types.hpp:141,181-189@cinemate-port`; `src/playback/PlaybackHold.hpp:3-25@cinemate-port`; `src/ipc/ControlServer.cpp:15@cinemate-port`; `scripts/start-apertar-core.sh:20-24@cinemate-port`

**Problem.** Comments carry T21-T51, Q10, Q23, R1, 'request 24', 'critic S11', 'design §4.3', 'kb working/dng-chain', '(Cinemate f01b6cd)', 'design sketch v2 (not in any repository)', line numbers into other files, // ---- banners, 250-character lines and history ('as before', '64 KiB used to drop the client without a word'). Operator text points at raw2wav.py, a Cinemate tool, and template comments say 'CineMate style'. App has 307 comment lines; upstream App has 10.

**Apertar way.** Comments are rare one- or two-line present-tense statements of a hazard or invariant (App:8103-8104@upstream-1.6.0, ControlServer.cpp:25; STY-8). No ticket numbers or other projects' hashes: 0 hits in both upstream trees (STY-9).

**Rework.**

1. Delete every T<nn>, Q<nn>, R<n>, request, critic, design-section, KB path, Cinemate hash and cross-file line number in App, AppH, Types.hpp, PlaybackHold.hpp, ControlServer.cpp, the start script and config files.
2. Delete the // ---- banners.
3. Cut each remaining note to its one hazard sentence (why a thread, why not under the lock, hold before read, why the yield window exists).
4. Operator text App:7381: 'Audio not finalised (audio_capture.raw).'; template comments without product names.
5. Measurements go to the KB, install steps to the handoff.

**Owner decision.** None.

**Check here.** git grep -nE '\bT[0-9]{2}\b|Cinemate|cinemate|kb working|critic|§' -- src include scripts config returns nothing; check_core.sh /home/user/wt/core-work core-work both tests

**Needs the Pi.** Nothing beyond the general smoke test.

**Risk.** None; best done per file after the structural items so the diff stays reviewable.

## APP-18. README grows into a lab manual: env knob table, install recipes, socket field lists, measurements

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| docs | major | S | yes | fix-later | Build-scripts-docs-F2, Build-scripts-docs-F12, X-knobs-15 |

**Where.** `README.md:179-211@cinemate-port`; `README.md:303-358@cinemate-port`

**Problem.** +90 lines: 'Write-path knobs for A/B tests' with a 13-row APERTAR_* table, KB references and dated measurements ('measured 2026-11-04, probable'); three sudo install recipes; a 'Socket commands:' list of 14 fields; 'Apertar-UI 7ea9afc (local branch clip-split)', a private commit and local branch.

**Apertar way.** The README is for the camera builder, second person, tables stop at launch flags (README.md:248-257@upstream-1.6.0; STY-14); grep -c APERTAR_ README.md@upstream-1.6.0 = 0. Helpers get no install recipes (UI/README.md:199@upstream-1.6.0).

**Rework.**

1. Delete the knob section and table (README.md:337-358) together with APP-9 and APP-14.
2. One short operator paragraph per feature: Boot Config card, split clips with the import warning, media trim, preview denoise, the record gate option (APP-23).
3. Remove KB paths, commit refs, measurement dates and the socket field list.
4. Install steps for anything that survives go to the handoff notes.

**Owner decision.** None.

**Check here.** grep -c 'APERTAR_' README.md = 1 (APERTAR_HARDWARE_CONFIG if upstream mentions it, else 0); markdown renders.

**Needs the Pi.** Nothing beyond the general smoke test.

**Risk.** None.

**Depends on.** APP-9, APP-13, APP-14

## APP-19. Core treats a missing audioRecordedOutlineEnabled as on (the UI half was fixed in U2)

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| stock | minor | S | no | fix-now | fix-log U2 follow-up, X-stock-behaviour-13 |

**Where.** `src/ApertarCoreApp.cpp:1907@cinemate-port`; `src/web/WebControlPage.cpp:16157@cinemate-port`

**Problem.** UI 2d9cf94 made the audio meter outline default off. Core's SharedUiSettingsSnapshot still has bool audioRecordedOutlineEnabled = true (confirmed, App:1907), so get_state and /api/state send audio_recorded_outline_enabled:true for a UI.conf without the key, and the WebUI shows the switch on (uiState.audio_recorded_outline_enabled !== false, WCP:16157).

**Apertar way.** An optional monitoring aid defaults off everywhere its default is written: recordingFrameEnabled and frameBufferBarEnabled = false (App:1904-1905@cinemate-port; recipe R3 step 7).

**Rework.**

1. App:1907: bool audioRecordedOutlineEnabled = false;
2. WCP:16157: uiState.audio_recorded_outline_enabled === true (WCP editor, same commit).

**Owner decision.** None.

**Check here.** check_core.sh /home/user/wt/core-work core-work both tests; --simulate with a UI.conf without the key: /api/state ui.audio_recorded_outline_enabled is false.

**Needs the Pi.** Nothing beyond the general smoke test.

**Risk.** None; a stored value still wins.

## APP-20. FPS and ISO step lists now end on the mode's odd ceiling

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| removed | minor | S | yes | fix-now | App-1-F15 |

**Where.** `src/ApertarCoreApp.cpp:1272-1289@cinemate-port`; `src/ApertarCoreApp.cpp:1398-1416@cinemate-port`

**Problem.** selectableValueSteps appends the cap whenever a listed value lies above it (confirmed). The IMX477 4144x2176 dial was 24, 25, 30 and is now 24, 25, 30, 41.08; buttons and encoders step to it without an option.

**Apertar way.** availablePcfFpsOptions keeps presets <= max and adds max only if (filtered.empty()) (App:1150-1167@upstream-1.6.0).

**Rework.**

1. selectableValueSteps: push the cap only when selectable is empty, as upstream; drop the above flag.
2. State the choice in the handoff.

**Owner decision.** None.

**Check here.** check_core.sh /home/user/wt/core-work core-work both tests; --simulate imx477 4144x2176: ui.fps_steps ends at 30.

**Needs the Pi.** Turn the FPS encoder to the top on IMX477 4144x2176: it stops at 30.

**Risk.** A user who wants the ceiling adds it to the UI.conf list.

## APP-21. settingsBody carries 14 [storage] members the settings event lacks

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| mismatch | minor | S | unknown | fix-now | App-1-F1, X-state-consistency-7 |

**Where.** `src/ApertarCoreApp.cpp:393@cinemate-port`; `src/ApertarCoreApp.cpp:252-269@cinemate-port`; `src/camera/CameraController.cpp:163-250@cinemate-port`

**Problem.** settingsBody ends with << "," << bufferSettingMembers(), so every set_* reply and get_state carries buffer, pre-roll and merge state, built with std::string + and three getenv calls each time. settingsEvent has none of them. No client breaks (the bridge checks contains(); the buffer event carries the same members).

**Apertar way.** settingsBody (App:167-216@upstream-1.6.0) and settingsEvent (CC:136-187@upstream-1.6.0) carry the same CaptureSettings fields; 'a field in the reply but not the event' is the listed violation (CMD-10). Capture status goes in get_state before settingsBody (recipe R4 step 1). JSON is an ostringstream << chain (CMD-9).

**Rework.**

1. Delete the bufferSettingMembers() line from settingsBody.
2. Add << "," << bufferSettingMembers() to the get_state body next to clipMergeStateJson().
3. Rewrite bufferSettingMembers as an ostringstream << chain without getenv (APP-9).

**Owner decision.** None.

**Check here.** check_core.sh /home/user/wt/core-work core-work both tests; smoke_core.sh <build>/apertar-core 8011 before/after and diff; browser on http://localhost:8011 against --simulate: set_iso reply has no buffer_* keys, get_state has them.

**Needs the Pi.** Nothing beyond the general smoke test.

**Risk.** None.

**Depends on.** APP-9

## APP-22. get_state writes media_state twice from two snapshots

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| bug | minor | S | no | fix-now | App-5-F3, X-protocol-security-6, X-state-consistency-11 |

**Where.** `src/ApertarCoreApp.cpp:12944@cinemate-port`; `src/ApertarCoreApp.cpp:12961@cinemate-port`

**Problem.** The get_state body streams media_state from a fresh mediaSnapshot() at :12944 and again from the mediaState snapshot at :12961 (confirmed). While a card is pulled the two can differ; the client's JSON parser decides which wins.

**Apertar way.** One key per status field, the same key in get_state and /api/state (App:9223-9237, :7836-7856@upstream-1.6.0; recipe R4). The port's web state writes it once (App:9555).

**Rework.**

1. Delete line 12944; keep the line next to media_alive.

**Owner decision.** None.

**Check here.** check_core.sh /home/user/wt/core-work core-work both tests; echo '{"cmd":"get_state"}' | socat - UNIX:/tmp/apertar-core.sock | grep -o media_state | wc -l = 1 in --simulate.

**Needs the Pi.** Nothing beyond the general smoke test.

**Risk.** None.

## APP-23. Record gate refuses a --media folder that is not a mount point; the opt-out is an undocumented env variable

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| removed | minor | S | yes | fix-now | App-4-F3, X-knobs-5 |

**Where.** `src/ApertarCoreApp.cpp:11327-11384@cinemate-port`; `src/ApertarCoreApp.cpp:12596-12600@cinemate-port`; `src/util/MediaProbe.hpp:105-123@cinemate-port`

**Problem.** record_start, capture_photo and timelapse_start answer 'No media mounted at <root>.' when /proc/mounts has no exact entry for the media root, or under 1024 MiB free. apertar-core --media /home/pi/clips refused where 1.6.0 recorded. The bypasses are --simulate and APERTAR_MEDIA_REQUIRE_MOUNT=0 / APERTAR_MEDIA_MIN_FREE_MB, documented nowhere. The gate itself is sound: without it a take under an empty /media/RAW lands on the SD card.

**Apertar way.** README.md:253@upstream-1.6.0 '--media PATH | Recording destination.' Upstream already treats an unmounted root as no media for the speed test, the library and format (App:8970-8974, :7676@upstream-1.6.0). Launch options are Options members with a --flag, a usage line and a README row (src/main.cpp:52-82@upstream-1.6.0; CMD-23).

**Rework.**

1. Add bool allowUnmountedMedia = false to ApertarCoreApp::Options; in src/main.cpp add if (arg == "--allow-unmounted-media") beside --media, a usage line and a README Launch Options row.
2. mediaGateBypassed() returns options_.simulateCamera || options_.allowUnmountedMedia; same member in storagePrerollGuard and playbackHoldReason.
3. constexpr uint64_t kMinFreeMiB = 1024; delete both env reads.

**Owner decision.** None.

**Check here.** check_core.sh /home/user/wt/core-work core-work both tests; apertar-core --simulate --media /tmp/x --allow-unmounted-media records in sim; --help lists the flag.

**Needs the Pi.** Unmount the card and press record: refused with the sentence; a USB stick mounted at /media/RAW records.

**Risk.** None.

**Depends on.** APP-9

## APP-24. Downloads refused in Standby and without media, not only during a take

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| removed | minor | S | unknown | fix-now | App-3-F2 |

**Where.** `src/ApertarCoreApp.cpp:8683-8690@cinemate-port`; `src/ApertarCoreApp.cpp:8812-8819@cinemate-port`; `src/playback/PlaybackHold.hpp:52-66@cinemate-port`

**Problem.** Both download routes return 409 whenever playbackHoldReason() is non-empty, a rule written for playback: it includes Standby (confirmed, PlaybackHold.hpp:64) and 'media not usable'. An operator offloading clips from a sleeping camera gets 'Playback held: standby. Downloads wait.' after the toast 'Preparing ... for download.', seen only as a failed browser download.

**Apertar way.** GET /api/media/download (App:7197@upstream-1.6.0) and download-selected (:7318) have no guard, so downloads work in Standby. Upstream counts timelapse as a take (App:7514), so holding downloads during a take, sound, timelapse, pending writes and the speed test matches the commit's stated reason.

**Rework.**

1. Add downloadHoldReason() beside playbackHoldReason(): recording, sound, timelapse, yield window, pending writes, speed test; Standby only while standbyUsbPoweredOff_.
2. Use it in both download routes; the route's own 404 covers missing media.
3. 409 + errorReply(-1, holdSentence(...)) per APP-5.

**Owner decision.** None.

**Check here.** check_core.sh /home/user/wt/core-work core-work both tests; --simulate enter_standby then curl -I /api/media/download?... returns 200.

**Needs the Pi.** Enter Standby with USB power kept, download a clip from the WebUI: it completes.

**Risk.** None.

**Depends on.** APP-5

## APP-25. /api/media hides folders during a hold; cDNG size_bytes and file_count change meaning

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| removed | minor | S | yes | fix-now | App-2-F6 |

**Where.** `src/ApertarCoreApp.cpp:7451-7454@cinemate-port`; `src/ApertarCoreApp.cpp:7488-7520@cinemate-port`; `src/playback/ClipProbe.hpp:120-130@cinemate-port`

**Problem.** During a hold, ProRes, H.264, MLV, timelapse and uncached cDNG folders are skipped with continue, so clips vanish from the WebUI list during a take; the comment promises 'the bare entry' but else if (!held) is always true. For cDNG, size_bytes counts only frames, WAVs and fps-ramp.txt (a .gcsv sidecar is missed) and file_count becomes the frame count.

**Apertar way.** discoverMediaLibraryItems lists every folder and mediaStatsForPath sums all files (App:6282-6448, :5915@upstream-1.6.0).

**Rework.**

1. In a hold push the bare entry (id, kind, name, type, size '--') from the root iterator instead of continue; no card read.
2. Delete the dead branch and the duplicate comment.
3. The facts cache sums all files for size_bytes; file_count stays a count of files.

**Owner decision.** None.

**Check here.** check_core.sh /home/user/wt/core-work core-work both tests; --simulate: start a take, GET /api/media lists every folder with size '--'.

**Needs the Pi.** During a take the WebUI media list keeps all clips; after it, sizes match du -sb.

**Risk.** Low.

## APP-26. audio_url is JSON-escaped, not URL-encoded

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| bug | minor | S | no | fix-now | App-2-F7 |

**Where.** `src/ApertarCoreApp.cpp:7387@cinemate-port`

**Problem.** "/api/media/file?kind=folder&id=" + escapeJson(id) + "&name=" + escapeJson(f.name) + ".wav" (confirmed). A clip named A&B_001 (clip names are composable since 014a2bf) gives id=A and a 404; '#', '%', '+' and space break the URL the same way.

**Apertar way.** mediaDownloadUrl uses urlEncodeComponent (App:5971, :7147-7150@cinemate-port; same helper at upstream-1.6.0).

**Rework.**

1. escapeJson("/api/media/file?kind=folder&id=" + urlEncodeComponent(id) + "&name=" + urlEncodeComponent(f.name + ".wav"))

**Owner decision.** None.

**Check here.** check_core.sh /home/user/wt/core-work core-work both tests; --simulate clip folder 'A&B_001' with a WAV: the audio_url fetches 200.

**Needs the Pi.** Nothing beyond the general smoke test.

**Risk.** None.

## APP-27. /api/buffer 'recording' means something else than /api/state 'recording'

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| protocol | minor | S | no | fix-now | App-3-F10 |

**Where.** `src/ApertarCoreApp.cpp:8423-8424@cinemate-port`; `src/ApertarCoreApp.cpp:9454@cinemate-port`; `src/web/WebControlPage.cpp:16514@cinemate-port`

**Problem.** The /api/buffer route appends recording = buffer.recording && !safetyStopState().active; /api/state sends recording = camera_.isRecording() || soundRecording. A sound-only take or a safety stop makes the same key disagree.

**Apertar way.** One key has one meaning across state copies (/api/state recording at App:7841@upstream-1.6.0; CMD-10).

**Rework.**

1. Rename the key in the /api/buffer route (App:8424) to buffer_recording.
2. Update the reader at WCP:16514 (WCP editor, same commit).

**Owner decision.** None.

**Check here.** check_core.sh /home/user/wt/core-work core-work both tests; --simulate sound-only take: /api/buffer buffer_recording false, /api/state recording true.

**Needs the Pi.** Nothing beyond the general smoke test.

**Risk.** None.

## APP-28. set_storage_preroll takes value=on|off and the action is the bare noun storage_preroll

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| protocol | minor | S | no | fix-now | App-5-F2, App-5-F8 |

**Where.** `src/ApertarCoreApp.cpp:12900-12906@cinemate-port`; `src/ApertarCoreApp.cpp:14603-14617@cinemate-port`; `src/ApertarCoreApp.cpp:12591@cinemate-port`

**Problem.** set_storage_preroll lower-cases value and accepts on/off/true/false/1/0; it is the only on/off command that takes value= instead of enabled=. The manual action is storage_preroll, with no verb. set_media_trim, set_preview_tdn, set_fps_phase_lock and set_fps_speed_ramp take enabled= but are not named *_enabled.

**Apertar way.** A lone boolean is enabled=, tested *enabled == "true" || "1", and the command is set_<thing>_enabled; actions carry a verb: record_start, timelapse_start (App:9482-9486@upstream-1.6.0; CMD-7, CMD-8).

**Rework.**

1. Rename to set_storage_preroll_enabled enabled= with the strict CMD-8 test; delete the tolower loop.
2. Rename storage_preroll to storage_preroll_start; update the head gate App:12591, help, Apertar-UI ApertarControlBridge.cpp:621-627 and WCP:14030, :15843.
3. Keep the record_stop branch that ends a running pre-roll (matches 'one stop button', App:10783-10794@upstream-1.6.0).
4. Leave the four camera switch names as they are unless the owner wants a protocol change for both clients.

**Owner decision.** None.

**Check here.** check_core.sh /home/user/wt/core-work core-work both tests; UI build (check_ui.sh); --simulate set_storage_preroll_enabled enabled=on is refused, enabled=true works.

**Needs the Pi.** Nothing beyond the general smoke test.

**Risk.** Touch UI and WebUI must change in the same merge.

**Depends on.** APP-11

## APP-29. Eject-intent flag file has no reader

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| slop | minor | S | yes | fix-now | App-1-F14, X-knobs-11 |

**Where.** `src/util/MediaIntent.hpp:10-58@cinemate-port`; `src/ApertarCoreApp.cpp:4355@cinemate-port`; `src/ApertarCoreApp.cpp:4386-4391@cinemate-port`; `src/ApertarCoreApp.cpp:10917@cinemate-port`; `config/apertar-media.tmpfiles.conf:4@cinemate-port`

**Problem.** writeEjectIntent writes /run/apertar-media/eject/<dev> before an eject and clearEjectIntent removes it after a mount or removal, 'for an automounter that honours it' (Cinemate f01b6cd). Nothing in Core or Apertar-UI (CfeAutomounter, the Python watcher, systemd, scripts) reads it; its directory needs a tmpfiles install step.

**Apertar way.** The upstream automounters (Apertar-UI/src/CfeAutomounter.cpp, Core's embedded Python watcher App:3391+@upstream-1.6.0) use no such flag.

**Rework.**

1. Delete src/util/MediaIntent.hpp, the three calls and APERTAR_MEDIA_RUN_DIR.
2. Delete config/apertar-media.tmpfiles.conf (its tune line goes with APP-13).

**Owner decision.** None.

**Check here.** check_core.sh /home/user/wt/core-work core-work both tests; git grep -n MediaIntent returns nothing.

**Needs the Pi.** Eject and reinsert a card: it remounts as before.

**Risk.** None.

**Depends on.** APP-13

## APP-30. Worker lifecycle: three start styles, stopMediaWatcher stops five more threads, five idle predicates, three clocks, record_start waits 4.5 s under the lock

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| mismatch | minor | M | unknown | fix-later | App-2-F4, App-4-F12, App-4-F15, App-4-F16, App-2-F15, App-4-F20 |

**Where.** `src/ApertarCoreApp.cpp:8027-8052@cinemate-port`; `src/ApertarCoreApp.cpp:8185-8189@cinemate-port`; `src/ApertarCoreApp.cpp:11054-11077@cinemate-port`; `src/ApertarCoreApp.cpp:11121@cinemate-port`; `src/ApertarCoreApp.cpp:11341-11357@cinemate-port`; `src/ApertarCoreApp.cpp:11471@cinemate-port`; `src/ApertarCoreApp.cpp:11697@cinemate-port`; `src/ApertarCoreApp.cpp:11905-11964@cinemate-port`; `src/ApertarCoreApp.cpp:12614-12619@cinemate-port`; `src/ApertarCoreApp.cpp:6337@cinemate-port`; `src/ApertarCoreApp.cpp:6394@cinemate-port`; `src/ApertarCoreApp.cpp:11630@cinemate-port`

**Problem.** Six workers start with three guard styles that never fire. stopMediaWatcher() also stops pre-roll, merge, trim and inlines the buffer-events and safety-stop joins. storagePrerollGuard, playbackHoldReason, mediaTrimMayRun, clipMergeMayRun and recordingGateActive each list a different subset of busy states (trim ignores the safety-stop flush merge checks). playbackNowMs, trimNowMs and clipMergeNowMs are the same function. waitForMediaTrim waits 2 s + SIGTERM 1 s + SIGKILL 0.5 s under commandMutex_ before a take. The media watcher also renews the playback yield window and trims idle frame slots; playbackHoldReason returns a string that five if lines map back to an enum. buildHardwareConfigFileJson types the /boot paths again.

**Apertar way.** Start sets the flag under the group mutex, then std::thread(&ApertarCoreApp::runX, this); one stopX() per worker, called from stop() in fixed order (App:6821-6825, :10988-11014@upstream-1.6.0; CMD-19, CMD-24). Shared busy checks are one || list at the head of handleCommand (App:9095-9110@upstream-1.6.0; CMD-4). One inline clock idiom (App:9112-9114@upstream-1.6.0). hardwareConfigCandidatePaths() already lists the /boot copies (App:4251-4259@upstream-1.6.0).

**Rework.**

1. Add stopBufferEvents() and stopBufferSafetyStop(); stopMediaWatcher() stops only the watcher; stop() calls every stopX() once, pre-roll before camera_.stop().
2. One start style: flag under the group mutex, no guard.
3. One bool mediaIdle(std::string *why) const for trim, merge and pre-roll; playbackHoldReason and recordingGateActive call it where they overlap.
4. One steady-clock ms helper; monotonicMicros stays (compared with systemd timestamps, App:12343).
5. On a take command SIGTERM the trim at once with no 2 s grace; keep the single-rename wait.
6. playbackHoldReason returns playback::Hold; holdName only at the JSON edge. The slot trim moves to the playback call sites.
7. buildHardwareConfigFileJson iterates hardwareConfigCandidatePaths() and skips the home path.

**Owner decision.** None.

**Check here.** check_core.sh /home/user/wt/core-work core-work both tests; --simulate start/stop under valgrind --tool=helgrind or a plain start+SIGTERM loop: clean exit, no hang.

**Needs the Pi.** Start an idle trim on NVMe and press record at once: the take starts within 0.5 s.

**Risk.** Stop order matters for pre-roll before camera_.stop().

**Depends on.** APP-10, APP-12

## APP-31. Buffer level pushed by an App polling thread; two identical events in one turn

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| mismatch | minor | M | yes | fix-later | App-4-F9, App-4-F10 |

**Where.** `src/ApertarCoreApp.cpp:10986-11052@cinemate-port`

**Problem.** runBufferEvents polls camera_.frameBufferStatus() and nine global flags every 250 ms (1 s idle) and publishes 'buffer'. Its first branch publishes on a setting, pre-roll or dropped-frame change without updating sentUsed/sentCapacity, so the busy branch publishes the same event again in the same turn.

**Apertar way.** The producer emits on change through its callback: emitMediaWriteState, 'Serialize edges' (CC:7551-7563@upstream-1.6.0); audio_level from the recorder's level callback (App:8380-8384@upstream-1.6.0); events built at the emit site (CMD-17).

**Rework.**

1. Now (S): in runBufferEvents set sentUsed/sentCapacity/open in the first branch so one turn publishes once.
2. Later: the write queue emits 'buffer' on a level change through the camera event callback, rate-limited in the queue and never under the controller mutex, as emitMediaWriteState; pre-roll and safety-stop flags travel in the events that change them; delete runBufferEvents.

**Owner decision.** None.

**Check here.** check_core.sh /home/user/wt/core-work core-work both tests; --simulate cDNG take: socat on the socket counts one buffer event per 250 ms at most.

**Needs the Pi.** cDNG take: the WebUI buffer bar moves as before.

**Risk.** Event rate must stay bounded on the socket.

**Depends on.** APP-10

## APP-32. Controls worker polls the hardware file every 2 s

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| mismatch | minor | S | yes | fix-later | App-4-F7 |

**Where.** `src/ApertarCoreApp.cpp:12242-12268@cinemate-port`

**Problem.** runControlsWorker wakes on a save or every 2 s, compares file text with the applied text and applies ssh edits. The KB contradicts itself (design-controls.md:93-95 'never applied on the side', decisions.md:47 'polled every 2 s').

**Apertar way.** 'A file watcher in Core' is the listed violation (CMD-13/C1-S08). Upstream applies hardware changes by restart (WCP:3869@upstream-1.6.0).

**Rework.**

1. Keep the worker (deadlock reason is sound).
2. Wake it on set_controls, POST /api/config and at take end where syncRecordingTracking(false) runs; drop the 2 s timeout.
3. An ssh edit applies at the next save or restart, as upstream; fix the KB design page.

**Owner decision.** None.

**Check here.** check_core.sh /home/user/wt/core-work core-work both tests; --simulate: edit the file by hand, nothing applies until a save.

**Needs the Pi.** Change a button in the WebUI during a take: it applies at take end.

**Risk.** Deferred applies must still run at take end.

## APP-33. Delete gate is not atomic with record_start

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| bug | minor | S | no | fix-later | App-3-F9 |

**Where.** `src/ApertarCoreApp.cpp:9015-9029@cinemate-port`; `src/ApertarCoreApp.cpp:9099-9112@cinemate-port`; `src/ApertarCoreApp.cpp:12587@cinemate-port`

**Problem.** The delete routes check isRecording, sound, timelapse and pending writes, then construct MediaDeleteScope, without commandMutex_. record_start can pass its 'Deleting media.' check, the route then sees isRecording false and deletes during the start of the take. Upstream had the same race without the flag, so this is a hole in the port's new guarantee, not a regression.

**Apertar way.** Upstream serialises with commandMutex_, which handleCommand holds for the whole command (CMD-3).

**Rework.**

1. In both delete routes hold a std::lock_guard on commandMutex_ around the checks and the MediaDeleteScope construction; keep the scope in a std::optional declared before the block; release the lock before the delete itself.

**Owner decision.** None.

**Check here.** check_core.sh /home/user/wt/core-work core-work both tests.

**Needs the Pi.** Delete a large folder and press record at once: either the take starts and the delete is refused, or the delete runs and record waits with the sentence.

**Risk.** None.

## APP-34. State and protocol fields with no reader

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| slop | minor | S | unknown | fix-later | App-1-F17, App-3-F12, X-state-consistency-9, X-knobs-12, App-2-F15 |

**Where.** `src/ApertarCoreApp.cpp:224-231@cinemate-port`; `src/ApertarCoreApp.cpp:304-331@cinemate-port`; `src/ApertarCoreApp.cpp:7359@cinemate-port`; `src/ApertarCoreApp.cpp:9285@cinemate-port`; `src/ApertarCoreApp.cpp:6221@cinemate-port`; `include/apertar/core/Types.hpp:137@cinemate-port`

**Problem.** conform_fps (a setting with a command, state lines and a preset key but no consumer and no UI), ladder_override, buffer_used/capacity/unit, sensor_binning/_source, sensor_crop, play_reason (always ''), boot_copy and the fps_phase_lock_* / media_device/fstype/class/profile / recording_fault diagnostics have no reader in WCP or Apertar-UI; only the KB test rig reads some.

**Apertar way.** Every camera field costs a line in three serialisers and has a reader (CMD-10, recipe R4). Upstream also publishes a few diagnostics nobody reads (wb_measured, wb_actual_*), so a short documented diagnostic list is not foreign.

**Rework.**

1. Delete conform_fps, set_conform_fps and cameraConformFps (Types.hpp:137, CC, App, presets).
2. Delete play_reason at App:7359 and :9285, and boot_copy at App:6221.
3. Delete ladder_override and buffer_used/capacity/unit unless the owner names a reader.
4. Keep the media_*, recording_fault and fps_phase_lock_* diagnostics and list them as diagnostic in one README state sentence.
5. hold_ms/double_ms (HardwareConfigText) and directIo (MediaProfile) are for the HW and media editors.

**Owner decision.** Do socket tools outside the repos (the KB test rig) read sensor_binning, sensor_binning_source and sensor_crop? Recommendation: keep them only if a tool you use reads them; otherwise delete. Keeping costs three serialiser lines each; deleting costs the rig script a change.

**Check here.** check_core.sh /home/user/wt/core-work core-work both tests; smoke_core.sh <build>/apertar-core 8011 before/after and diff; browser on http://localhost:8011 against --simulate: the deleted keys are gone, no other key changed.

**Needs the Pi.** Nothing beyond the general smoke test.

**Risk.** An outside script that reads a deleted key.

## APP-35. [cfexpress_hat]: two parsers, defaults in two places, C++ reader off where upstream's is on, status row on boards without the HAT

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| duplication | minor | S | yes | fix-later | App-2-F10, App-4-F13, App-4-F19 |

**Where.** `src/ApertarCoreApp.cpp:5296-5346@cinemate-port`; `src/util/CfeHat.hpp:19-20@cinemate-port`; `src/ApertarCoreApp.cpp:12085-12123@cinemate-port`; `src/ApertarCoreApp.cpp:12439-12447@cinemate-port`

**Problem.** CfeHatConfig::enabled=false and loadCfeHatConfig turns it on only when the section exists, while the embedded Python helper defaults CFE_HAT_ENABLED = True (App:4056@cinemate-port). cfeHatPeripheralJson parses the section a second time through hwconf with literal defaults '10' and '0x34', and get_controls parses the file 8 times. Config > Hardware shows 'Bus 10 does not exist on this Pi.' on Pi 4/CM4 for an accessory the user does not have.

**Apertar way.** One owner per section (CMD-12). The embedded helper is upstream's only reader and defaults on (App:3393, :3451@upstream-1.6.0). loadCfeHatConfig's shape copies loadIna219HardwareConfig (App:4450-4506@upstream-1.6.0), which conforms.

**Rework.**

1. CfeHat.hpp:19 bool enabled = true; drop the switch that turns it on when the section exists.
2. cfeHatPeripheralJson uses loadCfeHatConfig's result; delete the literal defaults.
3. Emit the HAT row only when the section exists (in_file is already computed).
4. Parse the document once in the builder (with APP-7).

**Owner decision.** None.

**Check here.** check_core.sh /home/user/wt/core-work core-work both tests; --simulate without [cfexpress_hat]: no HAT row in GET /api/config.

**Needs the Pi.** Pi 5 with the HAT and no section: pulling the card is seen by the C++ watcher (journalctl | grep -i cfe).

**Risk.** Cameras without a HAT poll i2c bus 10 at 0x34, as the Python helper already does.

**Depends on.** APP-7

## APP-36. clipInfoJson nests meta/extra objects that repeat top-level values

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| new-ground | minor | S | yes | fix-later | App-2-F9 |

**Where.** `src/ApertarCoreApp.cpp:7354-7405@cinemate-port`; `src/web/WebControlPage.cpp:12743@cinemate-port`

**Problem.** A flat top level plus holes (array of pairs), ramp ({"present":true} or null), meta{...} and extra{...}; meta.frame_rate repeats fps_badge, meta.frames repeats frame_count, extra.sound repeats sound_text.

**Apertar way.** Flat replies with fixed keys and Core-formatted *_text strings (size_text, duration_text, App:7697, :7700@upstream-1.6.0; CMD-9).

**Rework.**

1. Flatten to captured_text, resolution_text, bit_depth_text, duration_text, clip_size_text, path, format_text, dropped_text.
2. Drop meta.frame_rate, meta.frames and extra.sound; ramp becomes a boolean; holes stays the only array.
3. Update the WCP reader at :12743 in the same commit (WCP editor).

**Owner decision.** None.

**Check here.** check_core.sh /home/user/wt/core-work core-work both tests; --simulate Clip Viewer info panel shows the same lines.

**Needs the Pi.** Nothing beyond the general smoke test.

**Risk.** WCP reader must change together.

## APP-37. set_value_steps: range table inside the branch, repeated in the snapshot reader; nested ui reply

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| mismatch | minor | S | yes | fix-later | App-5-F5 |

**Where.** `src/ApertarCoreApp.cpp:14110-14162@cinemate-port`; `src/ApertarCoreApp.cpp:2160@cinemate-port`

**Problem.** A static constexpr ListKeys table with ranges sits inside the command branch; the UI.conf snapshot reader repeats the ranges (parseValueStepsList(value, 50.0, 51200.0)). The reply is "ui":{valueStepsJson(...)}.

**Apertar way.** Tables of allowed values are free functions in the anonymous namespace (favoriteCandidateOrder(), App:727-763@upstream-1.6.0); UI.conf commands echo flat keys (set_sleep_mode, App:10206-10216; set_favorites_order, App:10227@upstream-1.6.0).

**Rework.**

1. Move the table to a free valueStepsKeys(name) beside parseValueStepsList; use it in the snapshot reader too.
2. Reply with the chosen list's flat key, or a plain okReply.
3. Keep one command for the four lists.

**Owner decision.** None.

**Check here.** check_core.sh /home/user/wt/core-work core-work both tests; --simulate set_value_steps name=fps value=24,25,30 echoes fps_steps.

**Needs the Pi.** Nothing beyond the general smoke test.

**Risk.** None.

## APP-38. Clip name template parsed in App and again in CameraController; dead out-parameter

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| duplication | minor | S | no | fix-later | App-5-F4 |

**Where.** `src/ApertarCoreApp.cpp:13241-13268@cinemate-port`; `src/camera/CameraController.cpp:11835-11866@cinemate-port`; `src/camera/CameraController.hpp:92@cinemate-port`

**Problem.** set_clip_name_template calls apertar::clipname::parse in App, then camera_.setClipNameTemplate parses again; std::string stored is passed and never read. preview_clip_name parses twice. App's parse error comes before CC's 'while recording' refusal.

**Apertar way.** App checks that the argument is present; the CC setter validates and reports through lastError() (App:9251-9258, CC:7835-7849@upstream-1.6.0).

**Rework.**

1. App checks presence and calls camera_.setClipNameTemplate(*value); corrected = (settings.clipNameTemplate != *value).
2. previewClipName returns the normalized template and the corrected flag with the example.
3. Remove the stored parameter from the signature.

**Owner decision.** None.

**Check here.** check_core.sh /home/user/wt/core-work core-work both tests; tools/clip_name_test.cpp passes.

**Needs the Pi.** Nothing beyond the general smoke test.

**Risk.** None.

## APP-39. IMX585 Clear HDR fallback fps cap disagrees with Core's table

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| bug | minor | S | no | fix-later | App-1-F19 |

**Where.** `src/ApertarCoreApp.cpp:1386-1389@cinemate-port`; `src/camera/CameraController.cpp:3376-3380@cinemate-port`

**Problem.** App's fallback, used while fps_max is 0, caps only 16-bit Clear HDR at 25 ('as in Core's tableMaximumFpsForResolution()'); CC's table caps any Clear HDR at 25 when the sensor limit is unknown (confirmed). The dial can offer 30 in 12-bit Clear HDR where CC says 25, and the comment points at a rule that no longer exists.

**Apertar way.** App's per-sensor fallback (maximumPcfFpsForSettings, App:1150-1167@upstream-1.6.0) equals CC's table (recipe R5 step 7).

**Rework.**

1. App:1389: return settings.clearHdr ? 25.0 : 30.0;
2. Delete the comment or say 'Same as the unknown-limit row of CC's table.'

**Owner decision.** None.

**Check here.** check_core.sh /home/user/wt/core-work core-work both tests.

**Needs the Pi.** Nothing beyond the general smoke test.

**Risk.** None.

## APP-40. Hardware-file checker reads config.txt for [all] and [pi5] only

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| board | minor | S | no | fix-later | App-2-F12 |

**Where.** `src/ApertarCoreApp.cpp:4965-4978@cinemate-port`; `src/hardware/HardwareConfigText.hpp:1037-1051@cinemate-port`

**Problem.** hardwareConfigFacts() passes /boot/firmware/config.txt to parseConfigTxt, which applies only [all] and [pi5]. On Pi 4/CM4 a DPI overlay under [pi4]/[cm4] is missed and [pi5] lines are applied; on CM5 [cm5] lines are missed. Pin warnings are wrong on those boards.

**Apertar way.** No precedent (upstream has no checker). Board support: Pi 5 first, other models must not get wrong output (conventions section 6).

**Rework.**

1. Read /proc/device-tree/model in hardwareConfigFacts() and pass the board to parseConfigTxt.
2. Honour [pi4], [pi5], [cm4], [cm5] and [all] by board ([pi5] also matches CM5).

**Owner decision.** None.

**Check here.** Host test with a config.txt that has [pi4] dtoverlay=vc4-kms-dpi... and board=pi4: dpiLines non-empty.

**Needs the Pi.** On a CM5: GET /api/config dpi_lines matches vcgencmd get_config dtoverlay.

**Risk.** None.

## APP-41. ApertarCoreApp.hpp: methods among members, split member groups, 37 comment lines

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| mismatch | minor | S | no | fix-later | Build-scripts-docs-F8 |

**Where.** `src/ApertarCoreApp.hpp:145@cinemate-port`; `src/ApertarCoreApp.hpp:171-200@cinemate-port`; `src/ApertarCoreApp.hpp:255-330@cinemate-port`

**Problem.** Method declarations sit among data members (runControlsWorker :179, noteInputSeen :196); media-trim members (:324) are split from their group by clip-merge members (:323); enum class ClipMergeOutcome is in the method list; 37 '//' lines (upstream header has 1).

**Apertar way.** Owned components by value first, then state groups split by blank lines, mutex first (AppH:110-124@upstream-1.6.0; CMD-20, STY-8).

**Rework.**

1. Move all new methods into the private method block after joinMediaSpeedTest().
2. One contiguous group per worker: mutex, thread, flag, cv, state.
3. At most one lock-rule comment per group.

**Owner decision.** None.

**Check here.** check_core.sh /home/user/wt/core-work core-work both tests.

**Needs the Pi.** Nothing beyond the general smoke test.

**Risk.** None; do after APP-10/APP-30 so groups are final.

**Depends on.** APP-10, APP-30

## APP-42. Host tests in tools/ outside CMake, with build lines that disagree

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| new-ground | minor | S | unknown | keep-and-document | Build-scripts-docs-F9 |

**Where.** `tools/*_test.cpp header comments@cinemate-port`; `src/util/MediaTune.hpp:5@cinemate-port`; `README.md:325,335@cinemate-port`

**Problem.** 15 C++ tests, 3 sh tests, 2 Python tools. Build lines mix g++ and c++, c++17 and c++20, with and without warnings and -I include. MediaTune.hpp:5 names tools/media_tune_test.cpp, which does not exist. Test lines sit in operator README sections.

**Apertar way.** No precedent: upstream Core has no tests and no tools/ (PLT-12). Outside CMake is the least foreign shape. Core is C++20.

**Rework.**

1. One header line form in each test: g++ -std=c++20 -O2 -Wall -Wextra -I src -I include tools/<name>.cpp -o /tmp/<name> && /tmp/<name>.
2. Delete tests that go with removed code (media_trim_test.sh, boot_config_helper_test.sh, the dangling media_tune_test reference).
3. Move the test lines out of operator README sections into one sentence under For Developers.
4. Handoff: tell the original developer the tests are optional, host-only, and need no CMake change.

**Owner decision.** None.

**Check here.** for t in tools/*_test.cpp; do head -3 $t; done shows one form; check_core.sh ... tests passes.

**Needs the Pi.** Nothing beyond the general smoke test.

**Risk.** None.

**Depends on.** APP-13, APP-14

## APP-43. HardwareConfigStore replaces upstream's one save function

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| new-ground | minor | S | yes | keep-and-document | App-2-F11 |

**Where.** `src/ApertarCoreApp.cpp:6181-6252@cinemate-port`; `src/ApertarCoreApp.cpp:8136-8154@cinemate-port`; `src/hardware/HardwareConfigStore.cpp:451-463@cinemate-port`

**Problem.** Every writer of apertar-hardware.conf goes through a store with revisions, history files, adopt() (writes adopted-<rev>.conf once), merge review and 409 codes. Upstream's three checks remain as checkHardwareConfigText. History and adopt back the restore-a-replaced-file feature (014fa22), which is why the UI writer was dropped (c9d841f).

**Apertar way.** saveHardwareConfigFile: checks, .bak, .tmp plus rename (App:5323-5386@upstream-1.6.0).

**Rework.**

1. Keep revisions, the atomic write, .bak, history and adopt.
2. Drop the merge-review path if no caller needs it (HW-config-text-store editor decides).
3. 409 codes go per APP-5: sentence plus status.
4. One handoff paragraph for the original developer: what the store owns, where history lives, how a replaced file is reported.

**Owner decision.** None.

**Check here.** check_core.sh /home/user/wt/core-work core-work both tests.

**Needs the Pi.** Nothing beyond the general smoke test.

**Risk.** Low.

**Depends on.** APP-5

## APP-44. Socket request line raised from 64 KiB to 1 MiB for whole-file set_controls

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| protocol | minor | S | yes | fix-later | Build-scripts-docs-F10 |

**Where.** `src/ipc/ControlServer.cpp:15-16,264@cinemate-port`

**Problem.** kMaxRequestLineBytes = 1024 * 1024 because a set_controls text carries the whole hardware file; it serves only external socket clients (the touch UI never sends set_controls) and grows memory per stalled client 16x.

**Apertar way.** Socket line limited to 64 KiB (ControlServer.cpp:261@upstream-1.6.0); whole hardware-file text travels over POST /api/config under WebServer's 1 MiB cap (App:7175@upstream-1.6.0; WEB-6).

**Rework.**

1. Follow the HW-config-text-store decision: if the Controls card's set_controls text gives way to POST /api/config, revert to the 64 KiB literal.
2. Otherwise keep the constant with one why-line and no history.

**Owner decision.** None.

**Check here.** check_core.sh /home/user/wt/core-work core-work both tests.

**Needs the Pi.** Nothing beyond the general smoke test.

**Risk.** None.

## APP-45. set_timecode_mode target= sets screen and file timecode apart

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| new-ground | minor | S | yes | keep-and-document | App-5-F7 |

**Where.** `src/ApertarCoreApp.cpp:13279-13300@cinemate-port`; `src/ApertarCoreApp.cpp:14348-14352@cinemate-port`; `src/ApertarCoreApp.cpp:14428-14433@cinemate-port`

**Problem.** Optional target=both|ui|files, default both; preset key cameraTimecodeMode sets the file copy; the legacy timecodeMode sets both only when the new key is absent. UI.conf timecodeMode and camera timecode_mode can now differ. Commit 909aaa5: 'Pi build pending'. The stock-behaviour half (the touch UI now sends target=ui from the tap, X-stock-behaviour-8) is in the UI editor's list.

**Apertar way.** Upstream writes the camera value and UI.conf together (App:9424-9436@upstream-1.6.0; CMD-26). An absent field gives the old behaviour (CMD-30).

**Rework.**

1. Keep the Core shape: an optional field with the old default is the least foreign form.
2. Run on a Pi before merge.
3. Handoff: one paragraph naming the exception to CMD-26 and why (screen and file timecode apart).

**Owner decision.** None.

**Check here.** check_core.sh /home/user/wt/core-work core-work both tests; --simulate set_timecode_mode value=rec_run (no target) changes both.

**Needs the Pi.** Tap the timecode on the touch screen, record, check the DNG/WAV timecode follows (after the UI fix).

**Risk.** Depends on the UI fix for X-stock-behaviour-8.

## APP-46. Serialiser nits: leading-comma fragments, two ladder_tops precisions, help lacks test_input, start logs every success

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| mismatch | nit | S | no | fix-later | App-3-F11, X-state-consistency-12, X-state-consistency-13, App-2-F14 |

**Where.** `src/ApertarCoreApp.cpp:11593-11602@cinemate-port`; `src/ApertarCoreApp.cpp:11917-11925@cinemate-port`; `src/ApertarCoreApp.cpp:486-496@cinemate-port`; `src/camera/CameraController.cpp:153-161@cinemate-port`; `src/ApertarCoreApp.cpp:12930@cinemate-port`; `src/ApertarCoreApp.cpp:8146-8148@cinemate-port`; `src/ApertarCoreApp.cpp:10861@cinemate-port`

**Problem.** mediaTrimStateJson() and clipMergeStateJson() return text starting with ','; ladder_tops prints with 6 significant digits in the event and 10 in the reply; test_input is dispatched but not in help; every start logs '<path> <rev>: N errors, M warnings' and the CFE HAT settings.

**Apertar way.** Fragments carry no separator: "," << exposureMeteringJson(settings) (App:7867@upstream-1.6.0). App logs failures and ignored input only (App:1863, :8954@upstream-1.6.0; STY-7).

**Rework.**

1. Drop the leading comma in both functions; callers write << "," << ...
2. One number-array helper beside escapeJson used by settingsEvent and settingsBody (precision 10).
3. Add "test_input" next to "test_output" in help.
4. Log the store summary only with issues or a replaced file; log the HAT line only when it changes.

**Owner decision.** None.

**Check here.** check_core.sh /home/user/wt/core-work core-work both tests; smoke_core.sh <build>/apertar-core 8011 before/after and diff; browser on http://localhost:8011 against --simulate.

**Needs the Pi.** Nothing beyond the general smoke test.

**Risk.** None.

## APP-47. preview_tdn and media_trim are persisted but not preset fields

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| mismatch | nit | S | unknown | ask-owner | X-state-consistency-14 |

**Where.** `src/camera/CameraController.cpp:887,975@cinemate-port`; `src/ApertarCoreApp.cpp:7697@cinemate-port`

**Problem.** Both are camera_settings.conf keys kept across format changes; neither is in any preset copy, while cameraCdngPreviewColorProfile (upstream) is.

**Apertar way.** A persisted camera setting gets a preset writer and reader line and a WCP allow-list entry (recipe R2 step 10).

**Rework.**

1. Answer yes: add cameraPreviewTdn and cameraMediaTrim to buildCurrentPresetPayload, apply_preset and the WCP allow-list.
2. Answer no: one comment line in buildCurrentPresetPayload: 'preview_tdn and media_trim are camera-wide, not preset fields.'

**Owner decision.** Should a preset restore preview denoise and media trim? Recommendation: no; they are camera-wide switches like the hardware file, and a comment costs one line.

**Check here.** check_core.sh /home/user/wt/core-work core-work both tests.

**Needs the Pi.** Nothing beyond the general smoke test.

**Risk.** None.

## APP-48. set_iso_auto gains enabled=false (lock at the measured gain)

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| new-ground | nit | S | yes | keep-and-document | App-5-F9 |

**Where.** `src/ApertarCoreApp.cpp:12995-13001@cinemate-port`; `src/camera/CameraController.cpp:11146-11166@cinemate-port`

**Problem.** An optional enabled= field; false switches auto off at the gain measured inside CC. With no field the command still means auto on. Against a 1.6.0 Core the UI's Lock does nothing (X-protocol-security-3, UI editor).

**Apertar way.** Auto variants take no fields (App:9269, :9293, :9308@upstream-1.6.0; CMD-7).

**Rework.**

1. Keep: reading the gain under CC's mutex is the sound place.
2. Handoff: one line naming the extension.

**Owner decision.** None.

**Check here.** check_core.sh /home/user/wt/core-work core-work both tests.

**Needs the Pi.** Auto ISO, press Lock: iso equals the last iso_actual.

**Risk.** None.

## APP-49. Second include block after the JPEG #if; util/ headers ahead of public headers

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| mismatch | nit | S | no | fix-later | App-1-F20 |

**Where.** `src/ApertarCoreApp.cpp:2-5@cinemate-port`; `src/ApertarCoreApp.cpp:71-79@cinemate-port`

**Problem.** util/ includes come before <apertar/core/...>; <csignal>, <functional> and playback/, cdng/ headers sit in a separate block after the JPEG #if. It is the first thing the original developer sees.

**Apertar way.** Own header, public headers, project headers, std, system, then the #if blocks (App:1-55@upstream-1.6.0).

**Rework.**

1. Move each include into its upstream group.

**Owner decision.** None.

**Check here.** check_core.sh /home/user/wt/core-work core-work both tests.

**Needs the Pi.** Nothing beyond the general smoke test.

**Risk.** None.

## APP-50. Core's liblj92 README.apertar.md says 'in the UI'

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| docs | nit | S | no | fix-later | Build-scripts-docs-F13 |

**Where.** `third_party/liblj92/README.apertar.md:7-8@cinemate-port`

**Problem.** Byte-identical copy of the UI's file: 'Used to decode lossless JPEG tiles in the UI'. In Core the users are src/playback/DngFrameReader.hpp and DngTags.hpp.

**Apertar way.** README.apertar.md names the purpose (UI/third_party/liblj92/README.apertar.md:1-11@upstream-1.6.0; PLT-17).

**Rework.**

1. 'Used by Core playback (src/playback/) to decode lossless JPEG tiles of recorded DNGs.'

**Owner decision.** None.

**Check here.** -

**Needs the Pi.** Nothing beyond the general smoke test.

**Risk.** None.

## What conforms well (for the handoff)

- applyFanMode keeps the upstream sentence and its bool f(..., std::string *errorMessage) shape (App:3620-3649@cinemate-port)
- get_boot_config / set_boot_config also exist as ordinary handleCommand blocks under commandMutex_ (App:14586-14590@cinemate-port); only the HTTP door bypasses the lock
- jsonNumberArray sits next to jsonStringArray in the same shape (App:485-496@cinemate-port)
- UI.conf keys follow the struct-default plus else-if-branch pattern of SharedUiSettingsSnapshot (App:1903-2191@cinemate-port; recipe R3 step 7)
- set_controls restore= uses upstream's parseBooleanToken with a refusal sentence (App:2936@upstream-1.6.0)
- set_mode_ladder's boolField lambda and set_value_steps' parseUiSettingsBool follow apply_preset's addBoolUpdate lambda (App:10231-10237@upstream-1.6.0)
- set_media_trim, set_preview_tdn, set_fps_phase_lock, set_conform_fps are plain setter blocks replying settingsBody (App:13194-13240@cinemate-port)
- set_timecode_mode and set_iso_auto: an absent new field gives the 1.6.0 behaviour (CMD-30)
- The buffer safety stop ends a take by dispatching record_stop through handleCommand (App:11107-11109@cinemate-port), as the idle timer does
- record_stop also ends a running pre-roll, matching upstream's one-stop-button rule (App:10783-10794@upstream-1.6.0)
- The record gate extends upstream's own 'no media mounted' rule from the speed test and library (App:8970, :7676@upstream-1.6.0)
- loadCfeHatConfig copies loadIna219HardwareConfig's shape (App:4450-4506@upstream-1.6.0)
- clipFactsCache() is a function-local static cache, as upstream's caches (App:2269-2272@upstream-1.6.0)
- test_input stays outside the lock for a stated reason: its actions re-enter handleCommand
- Host tests live outside CMake, the least foreign shape for a code base without tests
- The display defaults are 720x720/square/false again in Core's template and the UI fallback (Core 7dc6f7a, UI 6a59d83); the GPIO chip is a Controls setting again with per-chip checks (Core 04fe197)

## Findings not taken, with the reason

- App-2-F1, X-knobs-2, X-stock-behaviour-1: done (Core 7dc6f7a, UI 6a59d83); noted in APP-16
- App-3-F5 rework (reuse errorReplyBody for hold replies): contradicts App-1-F5 and CMD-9; replaced by the sentence-plus-status rework in APP-5
- X-protocol-security-3, X-protocol-security-4, X-protocol-security-8: UI bridge domain
- X-state-consistency-1, X-state-consistency-2, X-state-consistency-3, X-state-consistency-4, X-state-consistency-6: UI and WCP domains; X-state-consistency-5: WCP/QML copies, App fallback part covered by APP-39; X-state-consistency-8: camera event (CC)
- X-knobs-1: hardware-config domain (knownKey); X-knobs-13: camera domain (CC loadCameraSection), the template lines follow that fix; X-knobs-14, X-knobs-19: camera; X-knobs-17: imx283 driver; X-knobs-18: UI commit series
- X-knobs-9: only the App, start-script and README names taken (APP-9, APP-15, APP-18); CC, encoder, driver, playback and audio names left to their editors
- X-knobs-12: conform_fps taken (APP-34); hold_ms/double_ms (hardware) and directIo (media) left
- X-stock-behaviour-3, X-stock-behaviour-4, X-stock-behaviour-9, X-stock-behaviour-10: camera domain; X-stock-behaviour-7: encoders; X-stock-behaviour-8: UI (referenced in APP-45); X-stock-behaviour-12, X-stock-behaviour-13: done in UI (U3 ac1fc28, U2 2d9cf94); Core's half of -13 is APP-19
- App-4-F14, App-4-F18, App-2-F13, App-3-F13, App-1-F10, App-1-F21: already dropped by the unit skeptics
