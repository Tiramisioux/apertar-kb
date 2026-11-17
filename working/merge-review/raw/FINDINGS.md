# All review findings, one line each

Built from the agents' structured results (after the skeptic where it ran). Full text: the report named per group.

## Unit App-1 (verified; /home/user/apertar-kb/working/merge-review/raw/rev-App-1.md)

| id | sev | category | effort | deliberate | title | where |
| --- | --- | --- | --- | --- | --- | --- |
| App-1-F2 | major | mismatch | M | no | [storage] parsed twice; live buffer state shared through header singletons and a global hook | src/ApertarCoreApp.cpp:273-286@cinemate-port; src/ApertarCoreApp.cpp:7988@cinemate-port |
| App-1-F3 | major | mismatch | S | no | Env-var knobs in the command plane, overriding hardware.conf keys and exposed as *_env state | src/ApertarCoreApp.cpp:88-106@cinemate-port; src/ApertarCoreApp.cpp:262-268@cinemate-port |
| App-1-F4 | major | mismatch | M | yes | Boot Config field command has a second HTTP entry with its own lock, header protocol and 403/409 codes | src/ApertarCoreApp.cpp:9161-9196@cinemate-port; src/ApertarCoreApp.cpp:3512-3516@cinemate-port |
| App-1-F5 | major | mismatch | M | yes | errorReplyBody adds machine error codes and extra members to error replies | src/ApertarCoreApp.cpp:173-184@cinemate-port; src/ApertarCoreApp.cpp:3787-3841@cinemate-port |
| App-1-F6 | major | new-ground | L | yes | apertar::bootconf: 1355-line header-only config.txt editor with free-text edit | src/hardware/BootConfigText.hpp:1-1355@cinemate-port; src/ApertarCoreApp.cpp:3651-3841@cinemate-port |
| App-1-F7 | major | security | M | yes | LAN client can write arbitrary config.txt text as root | src/ApertarCoreApp.cpp:3804-3812@cinemate-port; scripts/apertar-boot-config:39-53@cinemate-port |
| App-1-F1 | minor | mismatch | S | unknown | Storage/buffer state appended to settingsBody, not to settingsEvent | src/ApertarCoreApp.cpp:393@cinemate-port; src/ApertarCoreApp.cpp:252-269@cinemate-port |
| App-1-F8 | minor | mismatch | S | no | Boot Config error sentences carry install commands and wire field names | src/ApertarCoreApp.cpp:3605-3607@cinemate-port; src/ApertarCoreApp.cpp:3824-3827@cinemate-port |
| App-1-F9 | minor | mismatch | S | yes | Nested Boot Config replies | src/ApertarCoreApp.cpp:3701-3706@cinemate-port; src/ApertarCoreApp.cpp:3817-3822@cinemate-port |
| App-1-F11 | minor | new-ground | S | yes | Three write routes for config.txt, one of them a second atomic-write implementation | src/ApertarCoreApp.cpp:3519-3610@cinemate-port |
| App-1-F12 | minor | pi-compat | S | no | With the helper installed, fan mode fails on a config.txt without [pi5]/[pi4]/[all] | scripts/apertar-boot-config:51-53@cinemate-port; src/ApertarCoreApp.cpp:3588-3590@cinemate-port |
| App-1-F13 | minor | new-ground | M | yes | abortSafetyStopFlushForRecord runs before the command lock | src/ApertarCoreApp.cpp:291-299@cinemate-port; src/ApertarCoreApp.cpp:12567-12571@cinemate-port |
| App-1-F14 | minor | new-ground | S | yes | Eject-intent flag file has no reader in Apertar | src/ApertarCoreApp.cpp:4355@cinemate-port; src/ApertarCoreApp.cpp:4386-4391@cinemate-port |
| App-1-F15 | minor | removed-upstream-behaviour | S | yes | FPS/ISO step lists now end on the mode's odd ceiling | src/ApertarCoreApp.cpp:1272-1289@cinemate-port; src/ApertarCoreApp.cpp:1398-1416@cinemate-port |
| App-1-F16 | minor | slop | S | no | Tutorial numbers, KB paths, Cinemate history, banner and run-on comments | src/ApertarCoreApp.cpp:88-92@cinemate-port; src/ApertarCoreApp.cpp:243-251@cinemate-port |
| App-1-F17 | minor | slop | S | no | State fields with no reader | src/ApertarCoreApp.cpp:224-231@cinemate-port; src/ApertarCoreApp.cpp:304-308@cinemate-port |
| App-1-F18 | minor | mismatch | S | no | boolFieldValue: a second boolean parser accepting on/yes/off/no | src/ApertarCoreApp.cpp:3709-3718@cinemate-port |
| App-1-F19 | minor | bug | S | no | IMX585 Clear HDR fallback fps cap and its comment disagree with Core's table | src/ApertarCoreApp.cpp:1386-1389@cinemate-port; src/camera/CameraController.cpp:3376-3380@cinemate-port |
| App-1-F20 | nit | mismatch | S | no | Second include block after the JPEG #if; util/ headers ahead of public headers | src/ApertarCoreApp.cpp:2-5@cinemate-port; src/ApertarCoreApp.cpp:71-79@cinemate-port |

## Unit App-2 (verified; /home/user/apertar-kb/working/merge-review/raw/rev-App-2.md)

| id | sev | category | effort | deliberate | title | where |
| --- | --- | --- | --- | --- | --- | --- |
| App-2-F1 | blocker | removed-upstream-behaviour | S | yes | Template [display] defaults are an HDMI 1080p rig, not the stock 720x720 panel | src/ApertarCoreApp.cpp:5081-5098@cinemate-port; Apertar-UI/src/DisplayConfigBridge.cpp:11-12@cinemate-port |
| App-2-F2 | major | removed-upstream-behaviour | S | no | With the UI first-run writer gone, the only default lacks chip=auto, input tuning and [mpu6050] | src/ApertarCoreApp.cpp:5112-5116@cinemate-port; src/ApertarCoreApp.cpp:5137-5151@cinemate-port |
| App-2-F3 | major | mismatch | M | unknown | Buffer safety stop wired through a process-global std::function hook | src/ApertarCoreApp.cpp:7987-7994@cinemate-port; src/util/BufferBudget.hpp:262-266@cinemate-port |
| App-2-F5 | major | mismatch | L | unknown | Env knobs surface in state and WebUI; storage switches split over three stores; App keeps a settings copy | src/ApertarCoreApp.cpp:260-285@cinemate-port; src/ApertarCoreApp.cpp:6399-6404@cinemate-port |
| App-2-F4 | minor | mismatch | S | unknown | Worker start styles differ and stopMediaWatcher() also stops five other workers | src/ApertarCoreApp.cpp:8027-8052@cinemate-port; src/ApertarCoreApp.cpp:8185-8189@cinemate-port |
| App-2-F6 | minor | removed-upstream-behaviour | S | yes | /api/media in a hold hides folders; cDNG size_bytes/file_count change meaning | src/ApertarCoreApp.cpp:7451-7454@cinemate-port; src/ApertarCoreApp.cpp:7488-7520@cinemate-port |
| App-2-F7 | minor | bug | S | no | audio_url is JSON-escaped, not URL-encoded | src/ApertarCoreApp.cpp:7387@cinemate-port |
| App-2-F8 | minor | slop | S | no | Ticket tags, Cinemate names and a Cinemate tool in comments and operator text | src/ApertarCoreApp.cpp:7381@cinemate-port; src/ApertarCoreApp.cpp:5052@cinemate-port |
| App-2-F9 | minor | new-ground | S | yes | clipInfoJson nests meta/extra objects that repeat top-level values | src/ApertarCoreApp.cpp:7354-7405@cinemate-port; src/web/WebControlPage.cpp:12743@cinemate-port |
| App-2-F10 | minor | mismatch | S | yes | C++ [cfexpress_hat] reader defaults to off; upstream's reader defaults to on | src/ApertarCoreApp.cpp:5296-5346@cinemate-port; src/util/CfeHat.hpp:19@cinemate-port |
| App-2-F11 | minor | new-ground | S | yes | HardwareConfigStore replaces one save function; keep it, document it, trim merge review | src/ApertarCoreApp.cpp:6181-6252@cinemate-port; src/ApertarCoreApp.cpp:8136-8154@cinemate-port |
| App-2-F12 | minor | pi-compat | S | no | Validator parses config.txt for [all] and [pi5] only | src/ApertarCoreApp.cpp:4965-4978@cinemate-port; src/hardware/HardwareConfigText.hpp:1037-1051@cinemate-port |
| App-2-F14 | nit | mismatch | S | unknown | Success lines logged at every start | src/ApertarCoreApp.cpp:8146-8148@cinemate-port; src/ApertarCoreApp.cpp:10861@cinemate-port |
| App-2-F15 | nit | duplication | S | no | Three now-ms helpers, second /boot list, refreshBufferRequest twice, unread boot_copy | src/ApertarCoreApp.cpp:6337@cinemate-port; src/ApertarCoreApp.cpp:6394@cinemate-port |

## Unit App-3 (verified; /home/user/apertar-kb/working/merge-review/raw/rev-App-3.md)

| id | sev | category | effort | deliberate | title | where |
| --- | --- | --- | --- | --- | --- | --- |
| App-3-F1 | minor | mismatch | S | no | POST /api/boot-config is a second door for set_boot_config; splices "cmd" into the body | src/ApertarCoreApp.cpp:9170-9195@cinemate-port; src/ApertarCoreApp.cpp:14589@cinemate-port |
| App-3-F2 | minor | removed-upstream-behaviour | S | unknown | Downloads refused in Standby (and without media), not only during a take | src/ApertarCoreApp.cpp:8683-8690@cinemate-port; src/ApertarCoreApp.cpp:8812-8819@cinemate-port |
| App-3-F3 | minor | slop | S | yes | APERTAR_WEB_PREVIEW_RECORDING_FPS env knob left from an experiment | src/ApertarCoreApp.cpp:89-105@cinemate-port; src/ApertarCoreApp.cpp:9778-9784@cinemate-port |
| App-3-F4 | minor | new-ground | S | yes | Revision in an X-Apertar-Revision header, plus an old_page refusal | src/ApertarCoreApp.cpp:8633-8641@cinemate-port; src/ApertarCoreApp.cpp:9190-9193@cinemate-port |
| App-3-F5 | minor | mismatch | S | no | 409 hold replies hand-built at five sites; sibling routes differ; busy and gone replies without error key | src/ApertarCoreApp.cpp:8460@cinemate-port; src/ApertarCoreApp.cpp:8499@cinemate-port |
| App-3-F7 | minor | slop | S | no | Ticket numbers and history narration in comments | src/ApertarCoreApp.cpp:8476@cinemate-port; src/ApertarCoreApp.cpp:8551@cinemate-port |
| App-3-F8 | minor | mismatch | S | yes | Playback yield window is a file-scope singleton | src/ApertarCoreApp.cpp:6335-6352@cinemate-port |
| App-3-F9 | minor | bug | S | no | Delete gate is not atomic with record_start | src/ApertarCoreApp.cpp:9015-9029@cinemate-port; src/ApertarCoreApp.cpp:9099-9112@cinemate-port |
| App-3-F10 | minor | protocol | S | no | /api/buffer 'recording' differs from /api/state 'recording' | src/ApertarCoreApp.cpp:8423-8424@cinemate-port; src/ApertarCoreApp.cpp:9454@cinemate-port |
| App-3-F6 | nit | mismatch | S | no | Hold sentences carry internal hold tokens | src/ApertarCoreApp.cpp:8687@cinemate-port; src/ApertarCoreApp.cpp:8816@cinemate-port |
| App-3-F11 | nit | mismatch | S | no | State fragment helpers return a leading comma | src/ApertarCoreApp.cpp:11593-11602@cinemate-port; src/ApertarCoreApp.cpp:11917-11925@cinemate-port |
| App-3-F12 | nit | slop | S | no | Constant "play_reason":"" read by nobody | src/ApertarCoreApp.cpp:9285@cinemate-port; src/ApertarCoreApp.cpp:7359@cinemate-port |

## Unit App-4 (verified; /home/user/apertar-kb/working/merge-review/raw/rev-App-4.md)

| id | sev | category | effort | deliberate | title | where |
| --- | --- | --- | --- | --- | --- | --- |
| App-4-F1 | major | mismatch | M | yes | Second dispatcher before the command lock; get_controls/controls_history duplicate GET /api/config | src/ApertarCoreApp.cpp:12418@cinemate-port; src/ApertarCoreApp.cpp:12562-12565@cinemate-port |
| App-4-F2 | major | mismatch | L | yes | Storage pre-roll worker starts and finishes a camera take outside handleCommand | src/ApertarCoreApp.cpp:11254-11275@cinemate-port; src/ApertarCoreApp.cpp:11297@cinemate-port |
| App-4-F4 | major | new-ground | S | yes | Automatic storage pre-roll on by default: a raw take at every boot, card insert and format | src/util/StoragePreroll.hpp:98@cinemate-port; src/ApertarCoreApp.cpp:10945-10960@cinemate-port |
| App-4-F8 | major | slop | M | no | Ticket numbers, critic ids, KB paths, banners and about 140 comment lines in the slice | src/ApertarCoreApp.cpp:10870@cinemate-port; src/ApertarCoreApp.cpp:10897@cinemate-port |
| App-4-F3 | minor | removed-upstream-behaviour | S | yes | Record gate refuses a --media PATH that is not a mount point; the bypass is an env variable | src/ApertarCoreApp.cpp:11373-11374@cinemate-port; src/ApertarCoreApp.cpp:12596-12600@cinemate-port |
| App-4-F5 | minor | mismatch | M | yes | APERTAR_* environment knobs override saved settings and are re-read per call in App | src/ApertarCoreApp.cpp:11335@cinemate-port; src/ApertarCoreApp.cpp:11379@cinemate-port |
| App-4-F6 | minor | mismatch | L | unknown | Cross-part state in header-level function-static singletons | src/util/BufferBudget.hpp:231-234@cinemate-port; src/util/BufferBudget.hpp:330-333@cinemate-port |
| App-4-F7 | minor | mismatch | S | yes | Controls worker polls the hardware file every 2 s (a file watcher in Core) | src/ApertarCoreApp.cpp:12242-12268@cinemate-port |
| App-4-F9 | minor | mismatch | M | yes | Buffer level pushed by an App polling thread instead of emitted by the camera | src/ApertarCoreApp.cpp:10986-11052@cinemate-port |
| App-4-F10 | minor | bug | S | no | Two identical buffer events in one loop turn | src/ApertarCoreApp.cpp:11021-11039@cinemate-port |
| App-4-F11 | minor | mismatch | S | no | Media tuning helper runs sudo -n without /usr/bin/timeout or absolute paths, on the watcher thread | src/ApertarCoreApp.cpp:11422-11425@cinemate-port |
| App-4-F12 | minor | duplication | M | no | Five idle predicates that drift, three identical ms clocks | src/ApertarCoreApp.cpp:11121@cinemate-port; src/ApertarCoreApp.cpp:11341@cinemate-port |
| App-4-F13 | minor | duplication | S | no | [cfexpress_hat] parsed by two parsers with defaults in two places; get_controls parses the file 8 times | src/ApertarCoreApp.cpp:5298@cinemate-port; src/ApertarCoreApp.cpp:12087-12091@cinemate-port |
| App-4-F15 | minor | bug | S | yes | record_start may wait about 4.5 s under the command lock for a trim and a rename | src/ApertarCoreApp.cpp:12614-12619@cinemate-port; src/ApertarCoreApp.cpp:11941-11964@cinemate-port |
| App-4-F16 | minor | slop | S | no | Media watcher runs playback chores; hold reason round-trips string to enum | src/ApertarCoreApp.cpp:10970-10979@cinemate-port; src/ApertarCoreApp.cpp:11341-11357@cinemate-port |
| App-4-F17 | minor | mismatch | M | yes | Kernel tuning switch read from a fourth config file ~/apertar-media-tune.conf | src/ApertarCoreApp.cpp:11400-11408@cinemate-port; src/util/MediaTune.hpp:8-28@cinemate-port |
| App-4-F19 | nit | pi-compat | S | no | Config > Hardware shows a CFexpress hat row on boards without one | src/ApertarCoreApp.cpp:12085-12123@cinemate-port |
| App-4-F20 | nit | slop | S | no | Wording and shape nits | src/ApertarCoreApp.cpp:12493@cinemate-port; src/ApertarCoreApp.cpp:11372@cinemate-port |

## Unit App-5 (verified; /home/user/apertar-kb/working/merge-review/raw/rev-App-5.md)

| id | sev | category | effort | deliberate | title | where |
| --- | --- | --- | --- | --- | --- | --- |
| App-5-F1 | major | mismatch | M | unknown | Storage switches inline the hardware-store edit three times in handleCommand | src/ApertarCoreApp.cpp:12827-12855@cinemate-port; src/ApertarCoreApp.cpp:12857-12898@cinemate-port |
| App-5-F2 | minor | mismatch | S | no | set_storage_preroll takes value=on/off with its own parse; camera switches lack _enabled | src/ApertarCoreApp.cpp:12900-12906@cinemate-port; src/ApertarCoreApp.cpp:13194-13230@cinemate-port |
| App-5-F3 | minor | bug | S | no | get_state writes media_state twice from two snapshots | src/ApertarCoreApp.cpp:12944@cinemate-port; src/ApertarCoreApp.cpp:12961@cinemate-port |
| App-5-F4 | minor | duplication | S | no | Clip name template parsed in App and again in CC; unused out-parameter | src/ApertarCoreApp.cpp:13241-13268@cinemate-port; src/camera/CameraController.cpp:11835-11866@cinemate-port |
| App-5-F5 | minor | mismatch | S | yes | set_value_steps: range table inside the branch, nested ui reply | src/ApertarCoreApp.cpp:14110-14162@cinemate-port; src/ApertarCoreApp.cpp:2160@cinemate-port |
| App-5-F6 | minor | slop | S | no | Tutorial codes and history narration in handleCommand comments | src/ApertarCoreApp.cpp:12746@cinemate-port; src/ApertarCoreApp.cpp:12810@cinemate-port |
| App-5-F7 | minor | new-ground | S | yes | set_timecode_mode target= sets the UI timecode and the file timecode apart; not run on a Pi | src/ApertarCoreApp.cpp:13279-13300@cinemate-port; src/ApertarCoreApp.cpp:14348-14352@cinemate-port |
| App-5-F8 | nit | new-ground | S | yes | record_stop also ends a storage pre-roll; manual command named storage_preroll | src/ApertarCoreApp.cpp:14832-14836@cinemate-port; src/ApertarCoreApp.cpp:14603-14617@cinemate-port |
| App-5-F9 | nit | new-ground | S | yes | set_iso_auto gains an enabled field (false = lock at measured gain) | src/ApertarCoreApp.cpp:12995-13001@cinemate-port; src/camera/CameraController.cpp:11146-11166@cinemate-port |

## Unit CC-1 (verified; /home/user/apertar-kb/working/merge-review/raw/rev-CC-1.md)

| id | sev | category | effort | deliberate | title | where |
| --- | --- | --- | --- | --- | --- | --- |
| CC-1-F1 | blocker | removed-upstream-behaviour | M | yes | IMX585 1.85:1 crops rewritten to forked-driver sizes; Core tied to the cinemate-port driver | src/camera/CameraController.cpp:441-462@cinemate-port; src/camera/CameraController.cpp:703@cinemate-port |
| CC-1-F2 | minor | mismatch | M | yes | Raw buffer count reads the media tuning file and the sysfs media class | src/camera/CameraController.cpp:1456-1470@cinemate-port; src/util/MediaTune.hpp:27-28@cinemate-port |
| CC-1-F3 | minor | removed-upstream-behaviour | S | yes | kActiveRequestCount removed: one request per buffer in every raw take; 135 MB of Clear HDR buffers without a board check | src/camera/CameraController.cpp:1334-1338@cinemate-port; src/camera/CameraController.cpp:8379-8381@cinemate-port |
| CC-1-F4 | minor | mismatch | S | no | New persisted booleans written true/false and parsed by string compare | src/camera/CameraController.cpp:885-898@cinemate-port; src/camera/CameraController.cpp:974-980@cinemate-port |
| CC-1-F6 | minor | slop | S | yes | conform_fps: stored, published, clamped and carried, but never read | src/camera/CameraController.cpp:172@cinemate-port; src/camera/CameraController.cpp:696-697@cinemate-port |
| CC-1-F7 | minor | slop | S | no | Ticket numbers, other-project names and history in comments and in the written ladder file | src/camera/CameraController.cpp:403@cinemate-port; src/camera/CameraController.cpp:441-445@cinemate-port |
| CC-1-F9 | minor | new-ground | S | unknown | ladder_text: a pre-formatted display line built by Core | src/camera/CameraController.cpp:185@cinemate-port; src/camera/CameraController.cpp:10911-10935@cinemate-port |
| CC-1-F11 | minor | bug | S | no | {res} clip-name token labels by width only | src/camera/CameraController.cpp:1123-1130@cinemate-port |
| CC-1-F5 | nit | duplication | S | no | modeLadderPath is a line-for-line copy of persistedSettingsPath | src/camera/CameraController.cpp:403-415@cinemate-port |
| CC-1-F10 | nit | duplication | S | no | applyCdngLogFrame repeats the row loop of compressClearHdrFrame | src/camera/CameraController.cpp:1647-1656@cinemate-port; src/camera/CameraController.cpp:1671-1680@cinemate-port |
| CC-1-F12 | nit | mismatch | S | no | Three includes above the file's own header | src/camera/CameraController.cpp:1-3@cinemate-port |
| CC-1-F13 | nit | slop | S | no | Small inconsistencies: namespace spelling, member/key names, constant token, lone assert | src/camera/CameraController.cpp:660@cinemate-port; src/camera/CameraController.cpp:180@cinemate-port |

## Unit CC-2 (verified; /home/user/apertar-kb/working/merge-review/raw/rev-CC-2.md)

| id | sev | category | effort | deliberate | title | where |
| --- | --- | --- | --- | --- | --- | --- |
| CC-2-F1 | major | mismatch | S | yes | Camera side reads apertar-hardware.conf ([camera] Clear HDR ISO caps) | src/camera/CameraController.cpp:2933-2984@cinemate-port; src/camera/CameraController.cpp:3009-3023@cinemate-port |
| CC-2-F2 | major | mismatch | M | yes | DngRecordingQueue re-reads [storage] from disk at each take; App already publishes the same value | src/camera/CameraController.cpp:2986-3007@cinemate-port; src/camera/CameraController.cpp:4285-4313@cinemate-port |
| CC-2-F3 | major | removed-upstream-behaviour | S | yes | Upstream lossless cDNG limits changed (ISO 800->1600, auto ISO kept on IMX585, IMX585 fps 30 -> mode max) | src/camera/CameraController.cpp:3098-3158@cinemate-port |
| CC-2-F6 | major | mismatch | M | yes | Media tuning file feeds per-take recorder knobs | src/camera/CameraController.cpp:4316-4327@cinemate-port; src/camera/CameraController.cpp:4364-4365@cinemate-port |
| CC-2-F7 | major | mismatch | M | yes | Process-wide flush-abort callback registered by the queue | src/camera/CameraController.cpp:4211@cinemate-port; src/camera/CameraController.cpp:4271@cinemate-port |
| CC-2-F9 | major | bug | S | no | stop() joins copy workers without a bound; copy workers mkdir part folders on the medium | src/camera/CameraController.cpp:4453@cinemate-port; src/camera/CameraController.cpp:5164-5174@cinemate-port |
| CC-2-F5 | minor | new-ground | S | yes | Sync thread fsyncs clip frames once a second by default (deliberate departure from N10) | src/camera/CameraController.cpp:4353-4369@cinemate-port |
| CC-2-F8 | minor | mismatch | S | yes | FrameBufferGauge is a hidden function-local singleton | src/camera/CameraController.cpp:4169-4186@cinemate-port; src/camera/CameraController.cpp:4269@cinemate-port |
| CC-2-F10 | minor | slop | S | unknown | fps ceiling over-built: dead backendMaximumFps, FpsCeiling.hpp wrappers, experiment env switches | src/camera/CameraController.cpp:3389-3434@cinemate-port; src/camera/CameraController.cpp:3464-3491@cinemate-port |
| CC-2-F12 | minor | slop | S | no | Ticket numbers, names, dates, take ids and KB paths in comments | src/camera/CameraController.cpp:3025@cinemate-port; src/camera/CameraController.cpp:3034@cinemate-port |
| CC-2-F13 | minor | slop | S | no | Stale comments contradict the code | src/camera/CameraController.cpp:3378@cinemate-port; src/camera/CameraController.cpp:3481-3485@cinemate-port |
| CC-2-F14 | minor | mismatch | S | no | Ladder refusal texts as constexpr constants with a wrong menu path | src/camera/CameraController.cpp:3061-3067@cinemate-port |
| CC-2-F15 | minor | mismatch | M | no | Ladder compression handled as strings, not enums | src/camera/CameraController.cpp:3034-3049@cinemate-port; src/camera/ModeLadder.hpp:17-44@cinemate-port |
| CC-2-F17 | minor | removed-upstream-behaviour | S | yes | Uncompressed cDNG writer count and queue depth follow the filesystem on vfat/NTFS/other | src/camera/CameraController.cpp:4316-4327@cinemate-port; src/util/MediaProfile.hpp:136-150@cinemate-port |
| CC-2-F11 | nit | mismatch | S | no | New env knobs in CC parsed by hand, read once, logged | src/camera/CameraController.cpp:3115-3130@cinemate-port; src/camera/CameraController.cpp:3397-3408@cinemate-port |
| CC-2-F16 | nit | bug | S | no | wavSampleRate rejects RF64 | src/camera/CameraController.cpp:2894-2917@cinemate-port |
| CC-2-F18 | nit | mismatch | S | no | static bool warned inside a member function | src/camera/CameraController.cpp:4371-4373@cinemate-port |
| CC-2-F19 | nit | slop | S | no | 'CineMate Log' product name in Core log text | src/camera/CameraController.cpp:3963@cinemate-port; src/camera/CameraController.cpp:3985@cinemate-port |
| CC-2-F20 | nit | slop | S | no | Detached isoForMeasuredGain comment; optional round-trip in buildCdngLogTake | src/camera/CameraController.cpp:2892-2893@cinemate-port; src/camera/CameraController.cpp:4023-4028@cinemate-port |

## Unit CC-3 (verified; /home/user/apertar-kb/working/merge-review/raw/rev-CC-3.md)

| id | sev | category | effort | deliberate | title | where |
| --- | --- | --- | --- | --- | --- | --- |
| CC-3-F1 | major | mismatch | M | yes | Safety stop, flush abort, buffer gauge and buffer setting are process-wide globals and std::function registries shared by CC and App | src/camera/CameraController.cpp:4182@cinemate-port; src/camera/CameraController.cpp:4594@cinemate-port |
| CC-3-F2 | major | mismatch | M | yes | Recorder reads apertar-hardware.conf [storage] at every take, and a media tune file | src/camera/CameraController.cpp:2988-3006@cinemate-port; src/camera/CameraController.cpp:4297@cinemate-port |
| CC-3-F7 | major | removed-upstream-behaviour | S | yes | Preview temporal denoise off by default: the stock tuning is no longer loaded as is, and recorded H.264 and ProRes change too | src/camera/CameraController.cpp:7306-7320@cinemate-port; src/camera/CameraController.cpp:7326@cinemate-port |
| CC-3-F5 | minor | removed-upstream-behaviour | S | yes | Raw copy pool kept between takes; upstream freed it at stop | src/camera/CameraController.cpp:4502@cinemate-port; src/camera/CameraController.cpp:4596-4606@cinemate-port |
| CC-3-F3 | minor | bug | S | no | Sync thread waits on the writers' cv_; enqueue's notify_one can wake it instead of a writer | src/camera/CameraController.cpp:4743-4746@cinemate-port; src/camera/CameraController.cpp:5010@cinemate-port |
| CC-3-F4 | minor | bug | S | no | Detached writers outlive the queue: the destructor does not wait for liveWorkers_ | src/camera/CameraController.cpp:4208-4212@cinemate-port; src/camera/CameraController.cpp:4441-4446@cinemate-port |
| CC-3-F8 | minor | bug | S | unknown | Write-stall watchdog classes a slow but live medium as Removed | src/camera/CameraController.cpp:4834-4842@cinemate-port; src/camera/CameraController.cpp:4476-4483@cinemate-port |
| CC-3-F6 | minor | new-ground | S | yes | Per-file writeback, a 1 s fsync sweep and syncfs at stop reverse upstream's 'clip frames are not synced' | src/camera/CameraController.cpp:4715-4729@cinemate-port; src/camera/CameraController.cpp:4743-4790@cinemate-port |
| CC-3-F11 | minor | mismatch | S | yes | Probe identifies IMX585 by a properties::Model substring instead of SensorFamily | src/camera/CameraController.cpp:7152-7158@cinemate-port |
| CC-3-F12 | minor | new-ground | S | yes | Safety stop ends the take; record during the flush discards queued frames | src/camera/CameraController.cpp:5011-5022@cinemate-port; src/camera/CameraController.cpp:4611-4624@cinemate-port |
| CC-3-F9 | minor | slop | S | yes | A/B and experiment env knobs left in the recorder | src/camera/CameraController.cpp:4892-4899@cinemate-port; src/camera/CameraController.cpp:4715-4719@cinemate-port |
| CC-3-F10 | minor | slop | S | no | Comments with ticket numbers, clip ids, dates and a commit sha; misplaced member comment; assert | src/camera/CameraController.cpp:4674@cinemate-port; src/camera/CameraController.cpp:4678@cinemate-port |
| CC-3-F13 | nit | duplication | S | no | otherSensorSubdevPresent copies openImx585Subdev's sysfs walk | src/camera/CameraController.cpp:6955-6972@cinemate-port; src/camera/CameraController.cpp:6985-7002@cinemate-port |

## Unit CC-4 (verified; /home/user/apertar-kb/working/merge-review/raw/rev-CC-4.md)

| id | sev | category | effort | deliberate | title | where |
| --- | --- | --- | --- | --- | --- | --- |
| CC-4-F1 | major | mismatch | M | yes | DNG copy worker returns requests via set-once setRequestRelease(libcamera::Request*) instead of a per-frame release closure | src/camera/CameraController.cpp:8731-8739@cinemate-port; src/camera/CameraController.cpp:5032-5065@cinemate-port |
| CC-4-F2 | major | removed-upstream-behaviour | S | yes | Colour IMX585 raw12 crop sizes lost the auto sensor-config fallback | src/camera/CameraController.cpp:8295-8296@cinemate-port; src/camera/CameraController.cpp:8485-8530@cinemate-port |
| CC-4-F3 | major | mismatch | M | yes | Storage pre-roll pushes fps past the sanitiser and re-pins FrameDurationLimits on every request | src/camera/CameraController.cpp:7574-7576@cinemate-port; src/camera/CameraController.cpp:9074-9079@cinemate-port |
| CC-4-F4 | minor | slop | S | yes | Dead back-end fps cap wrapper around maximumSupportedFpsForResolution | src/camera/CameraController.cpp:8634-8639@cinemate-port; src/camera/CameraController.cpp:3426-3434@cinemate-port |
| CC-4-F5 | minor | slop | S | no | Internal vocabulary and history in comments | src/camera/CameraController.cpp:8902@cinemate-port; src/camera/CameraController.cpp:8907@cinemate-port |
| CC-4-F6 | minor | new-ground | S | yes | Frame-rate phase lock: servo fits the Apertar shape; socket telemetry does not | src/camera/CameraController.cpp:8887-8971@cinemate-port; src/camera/CameraController.cpp:9054-9070@cinemate-port |
| CC-4-F7 | minor | new-ground | M | yes | Speed ramp: frames numbered by count, fps free during a take, shelled rubberband stretch | src/camera/CameraController.cpp:9451-9479@cinemate-port; src/camera/CameraController.cpp:7589-7593@cinemate-port |
| CC-4-F8 | minor | duplication | S | no | IMX585 and IMX283 exact-mode checks duplicate the depth/PISP_COMP1 logic | src/camera/CameraController.cpp:8485-8530@cinemate-port; src/camera/CameraController.cpp:8531-8560@cinemate-port |
| CC-4-F9 | minor | pi-compat | S | unknown | Raw buffer count evaluated three times from live media state | src/camera/CameraController.cpp:8381@cinemate-port; src/camera/CameraController.cpp:8736@cinemate-port |
| CC-4-F10 | minor | new-ground | S | yes | syncfs at every take stop reverses 'clip frames are not synced' | src/camera/CameraController.cpp:7813-7814@cinemate-port; src/camera/CameraController.cpp:4795-4809@cinemate-port |
| CC-4-F11 | minor | slop | S | yes | Two real-time scheduling knobs for one experiment | src/camera/CameraController.cpp:9109-9133@cinemate-port; scripts/start-apertar-core.sh:20-39@cinemate-port |
| CC-4-F12 | nit | mismatch | S | no | Session data members declared in the public section | src/camera/CameraController.cpp:8186-8187@cinemate-port |

## Unit CC-5 (verified; /home/user/apertar-kb/working/merge-review/raw/rev-CC-5.md)

| id | sev | category | effort | deliberate | title | where |
| --- | --- | --- | --- | --- | --- | --- |
| CC-5-F1 | minor | new-ground | S | yes | Clear HDR ladder override kept by ten scattered writes and a 16-bit exception in setRawBitDepth | src/camera/CameraController.cpp:10679@cinemate-port; src/camera/CameraController.cpp:10711@cinemate-port |
| CC-5-F3 | minor | bug | S | no | rampNominalShutterUs_ survives a record-format switch | src/camera/CameraController.cpp:10751-10755@cinemate-port; src/camera/CameraController.cpp:11356@cinemate-port |
| CC-5-F4 | minor | bug | S | no | ladderOverride_ not persisted: after a restart a held Clear HDR mode sits outside the ladder and manual mode is refused (probable) | src/camera/CameraController.cpp:10508-10514@cinemate-port; src/camera/CameraController.hpp:245-249@cinemate-port |
| CC-5-F5 | minor | mismatch | S | unknown | setModeLadder returns JSON and error through out-parameters, bypasses setErrorLocked; dry run inside a setter | src/camera/CameraController.cpp:11045-11102@cinemate-port; src/ApertarCoreApp.cpp:14093-14107@cinemate-port |
| CC-5-F6 | minor | mismatch | S | yes | setResolution refuses an IMX585 size the current class lacks; upstream sanitises silently | src/camera/CameraController.cpp:10656-10664@cinemate-port |
| CC-5-F7 | minor | new-ground | M | yes | Experimental audio stretch needs uninstalled rubberband-cli and is launched as a detached double fork of sh -c | src/camera/CameraController.cpp:9933-10007@cinemate-port; include/apertar/core/Types.hpp:149@cinemate-port |
| CC-5-F8 | minor | mismatch | S | yes | Journal line per ramp setter call and per applied transition | src/camera/CameraController.cpp:10772-10775@cinemate-port; src/camera/CameraController.cpp:9847-9850@cinemate-port |
| CC-5-F9 | minor | new-ground | S | yes | Dropped-frame count published in recording_health | src/camera/CameraController.cpp:10490-10493@cinemate-port; src/camera/CameraController.cpp:10050@cinemate-port |
| CC-5-F10 | minor | mismatch | M | yes | configuredMediaRoot() is a mutable process-wide global written by CameraController::start | src/camera/CameraController.cpp:10543@cinemate-port; src/util/MediaProfile.hpp:214-234@cinemate-port |
| CC-5-F11 | minor | slop | S | no | Ticket numbers, Cinemate references, commit ids and dates in comments; // ---- banners | src/camera/CameraController.cpp:9742@cinemate-port; src/camera/CameraController.cpp:9931@cinemate-port |
| CC-5-F2 | nit | bug | S | no | A mid-ramp FPS can be written to camera_settings.conf by another setter during a take | src/camera/CameraController.cpp:10777-10780@cinemate-port; src/camera/CameraController.cpp:10812-10815@cinemate-port |
| CC-5-F12 | nit | mismatch | S | no | FPS refusal names a socket command and offers ramping to H.264/ProRes takes | src/camera/CameraController.cpp:10691-10697@cinemate-port |
| CC-5-F13 | nit | duplication | S | no | Mono flag expression repeated at each sanitiser call | src/camera/CameraController.cpp:10655@cinemate-port; src/camera/CameraController.cpp:10669@cinemate-port |

## Unit CC-6 (verified; /home/user/apertar-kb/working/merge-review/raw/rev-CC-6.md)

| id | sev | category | effort | deliberate | title | where |
| --- | --- | --- | --- | --- | --- | --- |
| CC-6-F1 | major | bug | S | no | Clip-name example probes the media root on every settings read and settings event under mutex_ | src/camera/CameraController.cpp:12592@cinemate-port; src/camera/CameraController.cpp:12866@cinemate-port |
| CC-6-F2 | major | removed-upstream-behaviour | S | no | Preview TDN off by default also strips temporal denoise from recorded H.264 and ProRes | include/apertar/core/Types.hpp:139@cinemate-port; src/camera/CameraController.cpp:7306-7326@cinemate-port |
| CC-6-F3 | major | mismatch | M | yes | Storage pre-roll is a hidden second take kind; N17 exclusions split between CC and App; setTuningFile and enterStandby ungated in CC | src/camera/CameraController.cpp:12038-12194@cinemate-port; src/camera/CameraController.cpp:11993@cinemate-port |
| CC-6-F4 | minor | bug | S | no | Early safety-stop recording event carries a stale lastError_ | src/camera/CameraController.cpp:12440-12448@cinemate-port; Apertar-UI src/ApertarControlBridge.cpp:1350-1362@cinemate-port |
| CC-6-F6 | minor | slop | S | no | Ticket and project vocabulary, essay comment, duplicated comment | src/camera/CameraController.cpp:11943-11944@cinemate-port; src/camera/CameraController.cpp:12038-12050@cinemate-port |
| CC-6-F5 | nit | slop | S | unknown | `fault` field of the recording event has no consumer | src/camera/CameraController.cpp:12891@cinemate-port |
| CC-6-F8 | nit | new-ground | S | unknown | Unlocked public storagePrerollError and the atomic CC prerollTake_ it needs | src/camera/CameraController.cpp:12131-12136@cinemate-port; src/camera/CameraController.hpp:226@cinemate-port |
| CC-6-F9 | nit | new-ground | S | yes | recording event carries a dropped-frames count | src/camera/CameraController.cpp:12889@cinemate-port |
| CC-6-F10 | nit | duplication | S | no | clipNameSensorLocked duplicates sensorName | src/camera/CameraController.cpp:11816-11822@cinemate-port; src/camera/CameraController.cpp:12596-12603@cinemate-port |
| CC-6-F11 | nit | new-ground | S | yes | emitLogAppliedIfChangedLocked + lastEmittedLogApplied_ for one runtime field | src/camera/CameraController.cpp:12875-12879@cinemate-port; src/camera/CameraController.cpp:12778@cinemate-port |

## Unit Camera-headers (verified; /home/user/apertar-kb/working/merge-review/raw/rev-Camera-headers.md)

| id | sev | category | effort | deliberate | title | where |
| --- | --- | --- | --- | --- | --- | --- |
| Camera-headers-F1 | major | mismatch | M | yes | TDN strip: own JSON parser, atomic writer and sidecar where upstream derives tuning files with libyaml | src/camera/TuningTdnStrip.hpp:43-249@cinemate-port; src/camera/TuningTdnStrip.hpp:350-378@cinemate-port |
| Camera-headers-F2 | major | bug | S | unknown | preview_tdn defaults to off and the stripped tuning reaches H.264/ProRes recordings and processed stills | include/apertar/core/Types.hpp:139@cinemate-port; src/camera/CameraController.cpp:7306-7326@cinemate-port |
| Camera-headers-F3 | major | removed-upstream-behaviour | S | yes | IMX585 lossless cDNG 30 fps cap lifted by default | src/camera/FpsCeiling.hpp:27-45@cinemate-port; src/camera/CameraController.cpp:3115-3142@cinemate-port |
| Camera-headers-F4 | major | removed-upstream-behaviour | S | yes | FPS ceiling: the probe beats the hard-coded table by default | src/camera/FpsCeiling.hpp:12-19@cinemate-port; src/camera/CameraController.cpp:3397-3423@cinemate-port |
| Camera-headers-F5 | major | mismatch | M | yes | Mode ladder persists in its own mode_ladder.conf | src/camera/ModeLadder.hpp:316-342@cinemate-port; src/camera/CameraController.cpp:403-414@cinemate-port |
| Camera-headers-F6 | minor | mismatch | S | no | Rung::compression is a free string mixing record format and compression | src/camera/ModeLadder.hpp:22-44@cinemate-port; src/camera/ModeLadder.hpp:160-166@cinemate-port |
| Camera-headers-F7 | minor | mismatch | S | no | Ladder setters and clip-name preview return errors and data through out-params instead of bool + lastError() | src/camera/CameraController.hpp:92@cinemate-port; src/camera/CameraController.hpp:102-109@cinemate-port |
| Camera-headers-F9 | minor | mismatch | S | yes | Display text and redundant ladder fields in CaptureSettings | include/apertar/core/Types.hpp:181-189@cinemate-port |
| Camera-headers-F11 | minor | duplication | S | no | Env-var parsing re-implemented three times | src/camera/Imx585Modes.hpp:105-114@cinemate-port; src/camera/FpsCeiling.hpp:29-38@cinemate-port |
| Camera-headers-F12 | minor | slop | S | no | Ticket numbers, Cinemate narration and a stale comment in code and in the user's config file | src/camera/ModeLadder.hpp:1,319@cinemate-port; include/apertar/core/Types.hpp:141,181-189@cinemate-port |
| Camera-headers-F13 | minor | slop | S | yes | conformFps is persisted and settable but has no effect and no UI | include/apertar/core/Types.hpp:135-137@cinemate-port; src/camera/CameraController.cpp:172,696-697,817-818,942,11354,11364,11806-11812@cinemate-port |
| Camera-headers-F15 | minor | new-ground | S | yes | Host tests of this unit: three styles, no build hook; phase-lock simulator only in the KB | tools/fps_ceiling_test.cpp@cinemate-port; tools/imx283_modes_test.cpp@cinemate-port |
| Camera-headers-F10 | nit | duplication | S | no | Sensor tables: own Size types and two nearest-mode metrics | src/camera/Imx283Modes.hpp:19-22,114-135@cinemate-port; src/camera/Imx585Modes.hpp:34-38,236-252@cinemate-port |
| Camera-headers-F14 | nit | slop | S | yes | Compatibility for spellings that never shipped; CdngLog::Auto means On | include/apertar/core/Types.hpp:59-62,326-346@cinemate-port; src/camera/ModeLadder.hpp:168,337@cinemate-port |
| Camera-headers-F16 | nit | new-ground | S | yes | FpsCeiling.hpp splits one-line rules into a header for a test | src/camera/FpsCeiling.hpp:1-47@cinemate-port |

## Unit Driver-imx283 (verified; /home/user/apertar-kb/working/merge-review/raw/rev-Driver-imx283.md)

| id | sev | category | effort | deliberate | title | where |
| --- | --- | --- | --- | --- | --- | --- |
| Driver-imx283-F1 | major | slop | M | no | Comment mass and internal vocabulary (WP/DEC/REBUILD/ROUND2/GAP/development refs) | imx283.c:26-30@cinemate-port; imx283.c:61@cinemate-port |
| Driver-imx283-F2 | major | new-ground | S | yes | crop_vmax defaults to 1 (unmeasured per-crop VMAX floors on) while Apertar requires 0 | imx283.c:271-281@cinemate-port; imx283.c:2428-2433@cinemate-port |
| Driver-imx283-F3 | minor | slop | S | no | Residue of the reverted active-only experiment: identity wrappers, hand-rolled nearest-size, stale comments | imx283.c:399-412@cinemate-port; imx283.c:459-480@cinemate-port |
| Driver-imx283-F4 | minor | slop | S | yes | Dead macros IMX283_CROP_1X1 / IMX283_CROPPED_1X1_MODE and compile-time WINDOW_LEFT switch | imx283.c:709-742@cinemate-port; imx283.c:804-806@cinemate-port |
| Driver-imx283-F5 | minor | bug | S | no | Function-local statics shared by all driver instances | imx283.c:1926-1945@cinemate-port; imx283.c:2534-2550@cinemate-port |
| Driver-imx283-F6 | minor | new-ground | S | yes | IMX283_ASPECT_MODE takes 15 positional arguments; parent timing repeated in 51 rows | imx283.c:694-707@cinemate-port; imx283.c:1060-1111@cinemate-port |
| Driver-imx283-F7 | minor | new-ground | S | yes | Probe-time imx283_check_mode_table audits static data every boot | imx283.c:1757-1924@cinemate-port; imx283.c:3202-3207@cinemate-port |
| Driver-imx283-F9 | minor | bug | S | yes | MODE_1C window .top = 852 not centred on the corrected active area (784); .left 924 OB unchecked on raw | imx283.c:808-835@cinemate-port; imx283.c:2632-2652@cinemate-port |
| Driver-imx283-F10 | minor | slop | S | yes | Docs: stale EXPERIMENTAL_CROPS.md shipped; APERTAR.md and README name the fork branch and CineMate | EXPERIMENTAL_CROPS.md:1-25@cinemate-port; APERTAR.md:7-14@cinemate-port |
| Driver-imx283-F11 | minor | slop | M | no | Port history: reverted 11-commit experiment, WP numbers in subjects | git log origin/master..cinemate-port: 4350e3e..a852cfe (11 commits); 773c5bb, 4ef5277, 8f2b230 and 4 more WP-numbered subjects |
| Driver-imx283-F8 | nit | duplication | S | yes | Core Imx283Modes.hpp hand-copies the 57 driver rows; provenance is a branch name | Apertar-Core/src/camera/Imx283Modes.hpp:1-144@cinemate-port; Apertar-Core/src/camera/CameraController.cpp:656-686@cinemate-port |
| Driver-imx283-F12 | nit | new-ground | S | yes | Nine read-only Mode * geometry controls have no Apertar consumer | imx283.c:25-65@cinemate-port; imx283.c:2221-2300@cinemate-port |
| Driver-imx283-F13 | nit | removed-upstream-behaviour | S | yes | Base sizes 2784x1548 (MODE_2A) and 5568x3094 (MODE_1A) removed | imx283.c:1102-1111@cinemate-port; imx283.c:1168@cinemate-port |
| Driver-imx283-F14 | nit | slop | S | no | Lost final newline after MODULE_LICENSE | imx283.c:3354@cinemate-port |

## Unit Driver-imx585 (verified; /home/user/apertar-kb/working/merge-review/raw/rev-Driver-imx585.md)

| id | sev | category | effort | deliberate | title | where |
| --- | --- | --- | --- | --- | --- | --- |
| Driver-imx585-F1 | blocker | removed-upstream-behaviour | S | yes | 1.85:1 sizes renamed (3840x2076->3840x2072, 1920x1038->1920x1036); unmodified 1.6.0 Core cannot configure 1920x1038 on a colour sensor | imx585.c:867@cinemate-port; imx585.c:918@cinemate-port |
| Driver-imx585-F2 | major | slop | M | no | Mode table carries work-package history, 'Experimental' labels on shipping modes, references to absent files and stale comments | imx585.c:767-858@cinemate-port; imx585.c:860-1000@cinemate-port |
| Driver-imx585-F3 | minor | bug | S | yes | 1440x1080 has a different field of view in 12-bit (1x1 1440 window) and 10-bit (2x2 of a 2880 window) | imx585.c:1369-1374@cinemate-port; imx585.c:2125-2130@cinemate-port |
| Driver-imx585-F4 | minor | new-ground | S | yes | 42 entries at 960/1024 wide (44 under 1280) are advertised but hidden by Apertar Core by default | imx585.c enum IMX585_MODE_CROP_BIN_960X540..IMX585_MODE_CROP_BIN_1024X400 and 10-bit equivalents@cinemate-port; Apertar-Core src/camera/Imx585Modes.hpp:15,100-114@cinemate-port |
| Driver-imx585-F5 | minor | new-ground | S | yes | The clearhdr_windowed_binning module parameter and the tools/clearhdr-gate kit depend on CineMate and have no recorded run | imx585.c:1025-1042@cinemate-port; imx585.c:3083-3094@cinemate-port |
| Driver-imx585-F6 | minor | new-ground | S | yes | The probe-time table audit prints a known warning on every boot, and the window predicate exists four times | imx585.c:4478-4586@cinemate-port; imx585.c:2962-2966@cinemate-port |
| Driver-imx585-F8 | minor | duplication | S | yes | Core's Imx585Modes.hpp hand-copies the four driver tables; rows that do not match the driver are dropped without a log line | Apertar-Core src/camera/Imx585Modes.hpp:39-98@cinemate-port; Apertar-Core src/camera/CameraController.cpp:7158-7189@cinemate-port |
| Driver-imx585-F9 | minor | slop | S | no | Docs: the README CineMate section, the fork clone URL and the branch name cinemate-port | README.md:37@cinemate-port; README.md:148-270@cinemate-port |
| Driver-imx585-F10 | minor | removed-upstream-behaviour | S | yes | Colour 12-bit CCMP Clear HDR is default-on, overriding the driver author's opt-in ccmp gate | imx585.c:4641@cinemate-port (commit b6a6f5b) |
| Driver-imx585-F11 | minor | bug | S | unknown | 12-bit Clear HDR is offered on 27 1x1 windowed crops with no recorded hardware validation, while the 2x2 crops are gated for the same reason | imx585.c:3086-3094@cinemate-port; APERTAR.md:160-172@cinemate-port |
| Driver-imx585-F12 | minor | slop | M | no | 55 commits, with 9 'experimental:' subjects, about 7 fix-ups of earlier commits and WP numbers in 13 subjects | git log origin/apertar..cinemate-port (imx585-v4l2-driver) |
| Driver-imx585-F7 | nit | slop | S | no | Unused min_vmax_default override and two wrong min_vmax literals | imx585.c:384-387@cinemate-port; imx585.c:3289-3299@cinemate-port |
| Driver-imx585-F13 | nit | new-ground | S | yes | The read-only geometry controls (+10..+14) have no Apertar consumer | imx585.c:44-50@cinemate-port; imx585_update_mode_metadata imx585.c:3354-3367@cinemate-port |

## Unit Encoders-audio (verified; /home/user/apertar-kb/working/merge-review/raw/rev-Encoders-audio.md)

| id | sev | category | effort | deliberate | title | where |
| --- | --- | --- | --- | --- | --- | --- |
| Encoders-audio-F1 | major | mismatch | S | yes | DONTNEED policy read from a tuning file inside the cDNG encoder | src/cdng/CdngEncoder.cpp:84-108@cinemate-port; src/cdng/CdngEncoder.cpp:7,21@cinemate-port |
| Encoders-audio-F2 | major | removed-upstream-behaviour | M | yes | Writer-side DONTNEED default changed for cDNG and dropped for Lossy DNG | src/cdng/CdngEncoder.cpp:1897-1898@cinemate-port; src/lossydng/LossyDngEncoder.cpp:101-105@cinemate-port |
| Encoders-audio-F3 | minor | slop | S | no | Comments narrate history, dates, clip ids, tutorial numbers and Cinemate hashes | src/cdng/CdngEncoder.hpp:13-16@cinemate-port; src/cdng/CdngEncoder.hpp:44@cinemate-port |
| Encoders-audio-F4 | minor | slop | S | unknown | 'CineMate Log' product name in Core code and log lines | src/cdng/LogCurve.hpp:13,18,48,63@cinemate-port; src/lossydng/LossyDngEncoder.cpp:51@cinemate-port |
| Encoders-audio-F5 | minor | mismatch | S | no | Audio writer queue unbounded, heap block per read | src/audio/AudioRecordingSession.cpp:734-746@cinemate-port; src/audio/AudioRecordingSession.cpp:485@cinemate-port |
| Encoders-audio-F6 | minor | new-ground | S | yes | Clip name template: over-built token set, placed in src/util | src/util/ClipName.hpp:29-35@cinemate-port; src/util/ClipName.hpp:121,130-132@cinemate-port |
| Encoders-audio-F9 | minor | bug | S | no | After a writer failure the WAV is built from queued bytes that were never written (probable) | src/audio/AudioRecordingSession.cpp:534-536@cinemate-port; src/audio/AudioRecordingSession.cpp:771-779@cinemate-port |
| Encoders-audio-F8 | nit | new-ground | S | yes | Drift fit still resamples anywhere in 20..2000 ppm | src/audio/AudioRecordingSession.cpp:486-498@cinemate-port; src/audio/AudioRecordingSession.cpp:588-608@cinemate-port |
| Encoders-audio-F10 | nit | new-ground | S | yes | ALSA hw params set by hand; ring env knob left after the reverted 1 s experiment | src/audio/TimestampedAudioCapture.cpp:192-219@cinemate-port; src/audio/TimestampedAudioCapture.hpp:27-28@cinemate-port |
| Encoders-audio-F11 | nit | new-ground | S | yes | Dropped-frame running total added to RecordingDropWarning | src/util/RecordingDropWarning.hpp:11-27@cinemate-port |
| Encoders-audio-F12 | nit | removed-upstream-behaviour | S | yes | MLV declares a different black level than 1.6.0 at 12/16-bit | src/mlv/MlvEncoder.cpp:1151-1157@cinemate-port |
| Encoders-audio-F13 | nit | slop | S | no | Knob area names and include order | src/cdng/CdngEncoder.cpp:118@cinemate-port; src/cdng/CdngEncoder.cpp:137@cinemate-port |
| Encoders-audio-F14 | nit | new-ground | S | yes | Host tests in tools/ plus a Python golden-value generator | tools/gen_log_curve.py@cinemate-port; tools/log_curve_test.cpp:1-6@cinemate-port |

## Unit HW-config-text-store (verified; /home/user/apertar-kb/working/merge-review/raw/rev-HW-config-text-store.md)

| id | sev | category | effort | deliberate | title | where |
| --- | --- | --- | --- | --- | --- | --- |
| HW-config-text-store-F1 | major | removed-upstream-behaviour | S | yes | The Config page's text save is refused on new validator errors, and the WebUI has no override | src/hardware/HardwareConfigStore.cpp:336-342@cinemate-port; src/ApertarCoreApp.cpp:8640-8642@cinemate-port |
| HW-config-text-store-F2 | major | removed-upstream-behaviour | S | yes | The browser cannot change [run_script] paths, and the same check blocks Undo and restore | src/hardware/HardwareConfigStore.cpp:34-42@cinemate-port; src/hardware/HardwareConfigStore.cpp:330-335@cinemate-port |
| HW-config-text-store-F3 | major | new-ground | M | yes | hwconf is a second, table-driven model of every reader in one 1141-line header, and it has already drifted | src/hardware/HardwareConfigText.hpp:27-69@cinemate-port; src/hardware/HardwareConfigText.hpp:157-208@cinemate-port |
| HW-config-text-store-F4 | minor | bug | S | no | A key edit on a duplicated section writes the copy the readers ignore | src/hardware/HardwareConfigText.hpp:541-550@cinemate-port; src/hardware/HardwareConfigStore.cpp:298@cinemate-port |
| HW-config-text-store-F5 | minor | bug | S | no | set_controls text= skips the upstream empty, size and NUL checks | src/ApertarCoreApp.cpp:12763-12799@cinemate-port; src/ApertarCoreApp.cpp:6227-6248@cinemate-port |
| HW-config-text-store-F6 | minor | bug | S | yes | An IMU write on a /boot-only rig creates a partial /home/pi file that hides the /boot file from every reader | src/hardware/Mpu6050RecordingSession.cpp:605-623@cinemate-port; src/hardware/HardwareConfigStore.cpp:154-163@cinemate-port |
| HW-config-text-store-F7 | minor | new-ground | S | yes | The text merge-review path has no in-tree caller | src/hardware/HardwareConfigText.hpp:1103-1139@cinemate-port; src/hardware/HardwareConfigStore.hpp:21@cinemate-port |
| HW-config-text-store-F8 | minor | protocol | S | yes | POST /api/config from a browser without X-Apertar-Revision gets a 409 | src/ApertarCoreApp.cpp:8628-8638@cinemate-port |
| HW-config-text-store-F9 | minor | mismatch | M | unknown | StoreResult machine codes and issue arrays in error replies | src/hardware/HardwareConfigStore.hpp:25-38@cinemate-port; src/ApertarCoreApp.cpp:8650-8654@cinemate-port |
| HW-config-text-store-F10 | minor | mismatch | S | no | A src/hardware header includes capture-pipeline util headers | src/hardware/HardwareConfigText.hpp:5-6@cinemate-port; src/hardware/HardwareConfigText.hpp:800-815@cinemate-port |
| HW-config-text-store-F11 | minor | duplication | S | no | A second config.txt parser, mostly dead, duplicates BootConfigText | src/hardware/HardwareConfigText.hpp:1029-1101@cinemate-port; src/ApertarCoreApp.cpp:4976@cinemate-port |
| HW-config-text-store-F12 | minor | pi-compat | S | unknown | parseConfigTxt applies only [all] and [pi5] blocks | src/hardware/HardwareConfigText.hpp:1037@cinemate-port; src/hardware/HardwareConfigText.hpp:1051@cinemate-port |
| HW-config-text-store-F13 | minor | slop | S | no | Owner name, ticket numbers, an out-of-tree client and history narration in code and operator text | src/hardware/HardwareConfigText.hpp:1082@cinemate-port; src/hardware/HardwareConfigText.hpp:116@cinemate-port |
| HW-config-text-store-F14 | minor | duplication | S | no | Three storage blocks repeat the store.edit shape, and the post-write block appears twice more | src/ApertarCoreApp.cpp:12828-12925@cinemate-port; src/ApertarCoreApp.cpp:8655-8660@cinemate-port |
| HW-config-text-store-F15 | nit | bug | S | no | `by` is written raw into hardware-state.conf, and a 100 ms sleep runs under the store mutex | src/hardware/HardwareConfigStore.cpp:406-414@cinemate-port; src/hardware/HardwareConfigStore.cpp:101-114@cinemate-port |

## Unit HW-controls-model (verified; /home/user/apertar-kb/working/merge-review/raw/rev-HW-controls-model.md)

| id | sev | category | effort | deliberate | title | where |
| --- | --- | --- | --- | --- | --- | --- |
| HW-controls-model-F1 | major | removed-upstream-behaviour | S | yes | GPIO chip (and poll_ms) dropped from the Controls page | src/hardware/ControlsModel.hpp:257-271@cinemate-port; src/hardware/ControlsModel.hpp:381@cinemate-port |
| HW-controls-model-F2 | major | removed-upstream-behaviour | S | yes | A button that reads pressed at start is inverted for the whole session, overriding active_low | src/hardware/GpioInput.cpp:620-629@cinemate-port; src/hardware/Pcf8574Input.cpp:423-432@cinemate-port |
| HW-controls-model-F3 | minor | removed-upstream-behaviour | S | unknown | Upstream keys refused by set_controls or hidden from the page | src/hardware/HardwareConfigText.hpp:460-462,476-477,496-497@cinemate-port; src/hardware/HardwareConfigText.hpp:174-181@cinemate-port |
| HW-controls-model-F4 | minor | bug | S | no | hold_ms and double_ms accepted as known keys, read by nobody | src/hardware/HardwareConfigText.hpp:457,466,470@cinemate-port; src/hardware/ButtonGesture.hpp:16-18@cinemate-port |
| HW-controls-model-F5 | minor | mismatch | M | yes | Action aliases as a runtime CSV string table instead of flat if-chains | src/hardware/ActionCatalog.hpp:18-132@cinemate-port; src/hardware/GpioInput.cpp:114@cinemate-port |
| HW-controls-model-F6 | minor | mismatch | S | yes | Trigger events and analog targets moved into the catalog with no consumer | src/hardware/TriggerOutput.cpp:131-143@cinemate-port; src/hardware/GroveAnalogInput.cpp:126-129@cinemate-port |
| HW-controls-model-F7 | minor | duplication | M | yes | classify() is a second parser of the parametric action grammar; the validator turns it into save-blocking errors | src/hardware/ActionCatalog.hpp:134-246@cinemate-port; src/hardware/HardwareConfigText.hpp:964-968@cinemate-port |
| HW-controls-model-F8 | minor | slop | S | no | list_actions serves fields nobody reads; its gestures list is wrong | src/ApertarCoreApp.cpp:12534-12554@cinemate-port; src/web/WebControlPage.cpp:18265@cinemate-port |
| HW-controls-model-F9 | minor | mismatch | S | no | JSON built in the hardware header with string concatenation and its own escaper | src/hardware/ControlsModel.hpp:50-71,307-388@cinemate-port; src/hardware/ActionCatalog.hpp:336-358@cinemate-port |
| HW-controls-model-F10 | minor | duplication | S | no | The settings spec repeats each reader's defaults | src/hardware/ControlsModel.hpp:255-305@cinemate-port |
| HW-controls-model-F11 | minor | new-ground | M | yes | Remote-only buttons stored as remote<N> in [gpio_buttons], a section GpioInput owns | src/hardware/ControlsModel.hpp:141-149,203-207@cinemate-port; src/hardware/HardwareConfigText.hpp:459@cinemate-port |
| HW-controls-model-F13 | minor | new-ground | S | yes | GPIO input waits for kernel edge events instead of polling | src/hardware/GpioInput.cpp:518,735-856@cinemate-port; src/hardware/ButtonGesture.hpp:55-65@cinemate-port |
| HW-controls-model-F14 | minor | slop | S | no | Comments carry Cinemate references, ticket numbers, history and stale statements | src/hardware/ButtonGesture.hpp:2-3,20@cinemate-port; src/hardware/ControlsModel.hpp:32@cinemate-port |
| HW-controls-model-F15 | minor | bug | S | no | Status probes and scan_i2c read chips that the UI process polls (probable) | src/hardware/I2cProbe.hpp:2-3@cinemate-port; src/ApertarCoreApp.cpp:12097,12495-12521@cinemate-port |
| HW-controls-model-F12 | nit | duplication | S | no | gpioChipScore moved out of one of its three copies | src/hardware/GpioChipInfo.cpp:30-54@cinemate-port; src/hardware/GpioInput.cpp:475@cinemate-port |
| HW-controls-model-F16 | nit | slop | S | no | get_controls parses the hardware file eight times per call | src/ApertarCoreApp.cpp:12439-12447@cinemate-port |

## Unit HW-input-classes (verified; /home/user/apertar-kb/working/merge-review/raw/rev-HW-input-classes.md)

| id | sev | category | effort | deliberate | title | where |
| --- | --- | --- | --- | --- | --- | --- |
| HW-input-classes-F1 | major | removed-upstream-behaviour | S | no | Standby wake press seeds click/Hold gestures; upstream consumes the wake press | src/hardware/ButtonGesture.hpp:21-55@cinemate-port; src/hardware/GpioInput.cpp:641-653,565-570@cinemate-port |
| HW-input-classes-F2 | minor | bug | S | no | 1-0-1 inversion and switch start-apply re-run on every device reopen | src/hardware/Pcf8574Input.cpp:409-433@cinemate-port; src/hardware/GpioInput.cpp:742-815,620-668@cinemate-port |
| HW-input-classes-F3 | minor | mismatch | S | no | Edge-event loop stops via a 250 ms idle wake, not an eventfd as upstream's poll() input does | src/hardware/GpioInput.cpp:714-731@cinemate-port; src/hardware/GpioInput.cpp:818-847@cinemate-port |
| HW-input-classes-F4 | minor | mismatch | S | no | GpioInput::run() rebuilt around large capturing lambdas | src/hardware/GpioInput.cpp:618-712@cinemate-port; src/hardware/GpioInput.cpp:716-731@cinemate-port |
| HW-input-classes-F5 | minor | bug | S | no | Edge drain applies stale queued edges on top of a fresh full-level read | src/hardware/GpioInput.cpp:829-849@cinemate-port |
| HW-input-classes-F6 | minor | new-ground | S | yes | Switch positions apply toggle actions at start and on every Controls save; position and state drift | src/hardware/GpioInput.cpp:656-686@cinemate-port; src/ApertarCoreApp.cpp:12302-12319@cinemate-port |
| HW-input-classes-F8 | minor | duplication | S | yes | gpioChipScore half-shared: one moved, two private copies remain | src/hardware/GpioChipInfo.cpp:31-55@cinemate-port; src/hardware/TriggerOutput.cpp:195@cinemate-port |
| HW-input-classes-F7 | nit | mismatch | S | no | Seen callback injected by setter, not constructor | src/hardware/GpioInput.hpp:21-22@cinemate-port; src/hardware/Pcf8574Input.hpp:21-22@cinemate-port |
| HW-input-classes-F9 | nit | removed-upstream-behaviour | S | yes | IMU writes can create a sparse ~/apertar-hardware.conf that shadows /boot/firmware | src/hardware/Mpu6050RecordingSession.cpp:603-628@cinemate-port; src/hardware/HardwareConfigStore.cpp:118-123,160-163@cinemate-port |
| HW-input-classes-F10 | nit | slop | S | no | Comments narrate Cinemate provenance and WebUI features inside src/hardware | src/hardware/ButtonGesture.hpp:2-3@cinemate-port; src/hardware/GpioInput.cpp:623,662,667,735@cinemate-port |
| HW-input-classes-F11 | nit | duplication | S | no | Seen-key suffixes chosen by static_cast of the gesture enum into parallel arrays, three copies | src/hardware/GpioInput.cpp:643-645@cinemate-port; src/hardware/Pcf8574Input.cpp:458-459@cinemate-port |

## Unit Playback (verified; /home/user/apertar-kb/working/merge-review/raw/rev-Playback.md)

| id | sev | category | effort | deliberate | title | where |
| --- | --- | --- | --- | --- | --- | --- |
| Playback-F1 | major | slop | M | no | Comments narrate tutorial and critic history across all playback files | src/playback/PlaybackHold.hpp:3@cinemate-port; src/playback/ClipProbe.hpp:3@cinemate-port |
| Playback-F2 | major | bug | S | no | tjhandle leaks once per decoded frame | src/playback/PlaybackFrames.cpp:92@cinemate-port |
| Playback-F3 | minor | mismatch | S | no | Playback routes hand-write JSON error bodies | src/ApertarCoreApp.cpp:8499@cinemate-port; src/ApertarCoreApp.cpp:8506@cinemate-port |
| Playback-F4 | minor | removed-upstream-behaviour | S | unknown | In a hold, /api/media drops items without cached facts | src/ApertarCoreApp.cpp:7448-7453@cinemate-port; src/ApertarCoreApp.cpp:7529@cinemate-port |
| Playback-F5 | minor | removed-upstream-behaviour | S | yes | Downloads refused in every hold, also standby | src/ApertarCoreApp.cpp:8682-8689@cinemate-port; src/ApertarCoreApp.cpp:8811-8818@cinemate-port |
| Playback-F6 | minor | duplication | S | unknown | Clip text helpers duplicate App formatters | src/playback/ClipProbe.hpp:30@cinemate-port; src/playback/ClipProbe.hpp:41@cinemate-port |
| Playback-F7 | minor | slop | S | no | Dead code and hooks for tests kept outside the repo | src/playback/DecodeSlots.hpp:26-32@cinemate-port; src/playback/DecodeSlots.hpp:105@cinemate-port |
| Playback-F8 | minor | mismatch | S | no | Hold rule built twice; name string parsed back into enum | src/ApertarCoreApp.cpp:9362-9372@cinemate-port; src/ApertarCoreApp.cpp:11341-11357@cinemate-port |
| Playback-F9 | minor | bug | S | no | FORMAT row guesses the lossy ratio from the clip name | src/playback/ClipProbe.hpp:168-178@cinemate-port |
| Playback-F13 | minor | pi-compat | S | unknown | Playback RAM on 1-2 GB boards; JPEG caches never trimmed | src/playback/DecodeSlots.hpp:26-30@cinemate-port; src/playback/PlaybackFrames.cpp:76-87@cinemate-port |
| Playback-F10 | nit | slop | S | no | Diagnostic response headers no page reads | src/ApertarCoreApp.cpp:8540-8546@cinemate-port; src/playback/PlaybackFrames.hpp:29-30@cinemate-port |
| Playback-F12 | nit | slop | S | no | liblj92 README describes the UI's use | third_party/liblj92/README.apertar.md:8@cinemate-port |
| Playback-F14 | nit | duplication | S | no | Three identical millisecond steady clocks | src/playback/DecodeSlots.hpp:47@cinemate-port; src/ApertarCoreApp.cpp:6336@cinemate-port |
| Playback-F15 | nit | mismatch | S | no | UI helper namespace style | /home/user/Apertar-UI/src/ClipFrameFiles.hpp:17@cinemate-port |

## Unit UI-bridges (verified; /home/user/apertar-kb/working/merge-review/raw/rev-UI-bridges.md)

| id | sev | category | effort | deliberate | title | where |
| --- | --- | --- | --- | --- | --- | --- |
| UI-bridges-F1 | blocker | removed-upstream-behaviour | S | yes | Display fallback changed from 720x720 touch panel to HDMI-only 1080p (touch window hidden) | src/DisplayConfigBridge.cpp:11-12@cinemate-port; src/DisplayConfigBridge.cpp:289@cinemate-port |
| UI-bridges-F2 | major | removed-upstream-behaviour | S | yes | Nothing creates the default apertar-hardware.conf at first start any more | src/DisplayConfigBridge.cpp:35-38@cinemate-port; src/Ina219Bridge.cpp:63-66@cinemate-port |
| UI-bridges-F3 | minor | bug | S | no | Preview cap drops frames before frameArrived, so the Rec Run UI timecode slows or stops | src/ApertarPreviewSocketClient.cpp:488-498@cinemate-port; qml/CameraPage.qml:2038-2045@cinemate-port |
| UI-bridges-F4 | minor | slop | S | yes | APERTAR_UI_PREVIEW_RECORDING_FPS experiment knob left in the merge branch | src/ApertarPreviewSocketClient.cpp:25-43@cinemate-port; src/ApertarPreviewSocketClient.hpp:36,95-98@cinemate-port |
| UI-bridges-F5 | minor | mismatch | S | no | Five new apply* invokables return void instead of bool | src/ApertarControlBridge.hpp:194-200@cinemate-port; src/ApertarControlBridge.cpp:618-727@cinemate-port |
| UI-bridges-F6 | minor | slop | S | no | Ticket tags and Cinemate names in code comments | src/ApertarControlBridge.hpp:82@cinemate-port; src/ApertarControlBridge.hpp:424@cinemate-port |
| UI-bridges-F8 | minor | bug | S | no | ControlsWarning.qml missing from qml.qrc (non-AOT builds) | CMakeLists.txt:41@cinemate-port; qml.qrc@cinemate-port |
| UI-bridges-F9 | minor | bug | S | no | Core media override in MediaStatusBridge is never cleared when Core goes away | src/MediaStatusBridge.cpp:288-296@cinemate-port; src/MediaStatusBridge.cpp:1245-1257@cinemate-port |
| UI-bridges-F10 | minor | bug | S | no | Surprise card removal acts on one undebounced I2C sample, with an unrefusable unmount | src/CfeAutomounter.cpp:549-550@cinemate-port; src/CfeAutomounter.cpp:726-746@cinemate-port |
| UI-bridges-F7 | nit | removed-upstream-behaviour | S | yes | The camera-screen timecode tap no longer changes clip timecode | src/ApertarControlBridge.hpp:202-203@cinemate-port; src/ApertarControlBridge.cpp:750-771@cinemate-port |
| UI-bridges-F11 | nit | removed-upstream-behaviour | S | yes | Fan mode change from the touch UI now needs a running Core | src/SystemActionBridge.cpp:65-97@cinemate-port; src/SystemActionBridge.cpp:404-409@cinemate-port |

## Unit UI-camera-qml (verified; /home/user/apertar-kb/working/merge-review/raw/rev-UI-camera-qml.md)

| id | sev | category | effort | deliberate | title | where |
| --- | --- | --- | --- | --- | --- | --- |
| UI-camera-qml-F1 | minor | slop | S | no | Ticket numbers, names and dates in code comments | qml/CameraPage.qml:518@cinemate-port; qml/CameraPage.qml:544@cinemate-port |
| UI-camera-qml-F2 | minor | slop | S | no | Stale 'green' comments; the convention is italics | qml/CameraPage.qml:523@cinemate-port; qml/CameraPage.qml:859@cinemate-port |
| UI-camera-qml-F3 | minor | protocol | S | no | Lossless ISO and IMX585 lossless FPS caps lost against a Core without iso_max/fps_max | qml/CameraPage.qml:525-532@cinemate-port; qml/CameraPage.qml:904-916@cinemate-port |
| UI-camera-qml-F5 | minor | mismatch | S | no | Buffer bar written twice (StatusChip and HDMI pill) | qml/StatusChip.qml:95-119@cinemate-port; qml/ExternalMonitorWindow.qml:1104-1137@cinemate-port |
| UI-camera-qml-F6 | minor | bug | S | no | Safety-stop flush: pill says READY while the frame, red timecode and audio outline still show recording | qml/CameraPage.qml:4347@cinemate-port; qml/CameraPage.qml:3924@cinemate-port |
| UI-camera-qml-F8 | minor | duplication | S | no | isoOnAddedCap, built-in ISO list and raw-format test copied into the HDMI window with drift | qml/CameraPage.qml:534@cinemate-port; qml/ExternalMonitorWindow.qml:98@cinemate-port |
| UI-camera-qml-F11 | minor | bug | S | no | ISO Auto offered in non-IMX585 lossless modes, where Core still turns it off | qml/CameraPage.qml:528-532@cinemate-port; src/camera/CameraController.cpp:3150-3155@cinemate-port (Core) |
| UI-camera-qml-F4 | nit | removed-upstream-behaviour | S | yes | ISO Auto in IMX585 lossless; lossless ISO ceiling 800 -> 1600 | qml/CameraPage.qml:525-532@cinemate-port; src/camera/CameraController.cpp:3098-3100,3150-3155@cinemate-port (Core) |
| UI-camera-qml-F7 | nit | removed-upstream-behaviour | S | yes | HDMI timecode turns red while recording by default | qml/ExternalMonitorWindow.qml:1208@cinemate-port |
| UI-camera-qml-F9 | nit | slop | S | no | Empty if-block with a comment in fpsCeiling() | qml/CameraPage.qml:912-913@cinemate-port |
| UI-camera-qml-F10 | nit | slop | S | no | ControlsWarning.qml is in CMakeLists.txt but not in qml.qrc | CMakeLists.txt:41@cinemate-port; qml.qrc@cinemate-port |

## Unit UI-control-bridge (verified; /home/user/apertar-kb/working/merge-review/raw/rev-UI-control-bridge.md)

| id | sev | category | effort | deliberate | title | where |
| --- | --- | --- | --- | --- | --- | --- |
| UI-control-bridge-F1 | major | mismatch | S | no | Six new invokables return void; bool args sent as value=on/off and auto/off; names not in the upstream form | src/ApertarControlBridge.hpp:194-198@cinemate-port; src/ApertarControlBridge.hpp:200@cinemate-port |
| UI-control-bridge-F2 | major | mismatch | M | no | Second state path: dedicated buffer/controls/media event branches and a key-name-parameterised setter | src/ApertarControlBridge.cpp:1332-1349@cinemate-port; src/ApertarControlBridge.cpp:1424-1442@cinemate-port |
| UI-control-bridge-F5 | major | removed-upstream-behaviour | M | yes | applyTimecodeMode gained a required target: upstream one-arg call gone, camera tap no longer sets file timecode | src/ApertarControlBridge.cpp:750-771@cinemate-port; src/ApertarControlBridge.hpp:202-203@cinemate-port |
| UI-control-bridge-F6 | minor | mismatch | M | yes | 1 s full get_state poll while auto ISO/WB; updateRefreshTimer on every state pass | src/ApertarControlBridge.cpp:19-20@cinemate-port; src/ApertarControlBridge.cpp:1016@cinemate-port |
| UI-control-bridge-F4 | minor | slop | S | no | String-or-number tolerant parsing justified by 'KB trap 7'; Core emits typed JSON | src/ApertarControlBridge.cpp:2666@cinemate-port; src/ApertarControlBridge.cpp:2692-2759@cinemate-port |
| UI-control-bridge-F8 | minor | bug | S | no | shutterSetByCamera reads m_recording before setRecordingState in the same pass | src/ApertarControlBridge.cpp:1610@cinemate-port; src/ApertarControlBridge.cpp:1730-1731@cinemate-port |
| UI-control-bridge-F9 | minor | new-ground | S | no | Presence latches storagePrerollAutoKnown / clipNameKnown for 'older Core' | src/ApertarControlBridge.cpp:670-673@cinemate-port; src/ApertarControlBridge.cpp:2746-2749@cinemate-port |
| UI-control-bridge-F10 | nit | slop | S | no | Ticket ids, other product name, stale comments; missing <algorithm> include; setter among members | src/ApertarControlBridge.cpp:275@cinemate-port; src/ApertarControlBridge.cpp:1582@cinemate-port |
| UI-control-bridge-F3 | nit | duplication | S | no | Clip-name reply applied twice in applyClipNameTemplate | src/ApertarControlBridge.cpp:635-641@cinemate-port |

## Unit UI-settings-qml (verified; /home/user/apertar-kb/working/merge-review/raw/rev-UI-settings-qml.md)

| id | sev | category | effort | deliberate | title | where |
| --- | --- | --- | --- | --- | --- | --- |
| UI-settings-qml-F1 | major | mismatch | M | no | ActionTiles with a flipping accent tone used as radio buttons | qml/SettingsPage.qml diff:537-551 (Write Buffer Frames/RAM)@cinemate-port; qml/SettingsPage.qml diff:578-584 (Log On/Off)@cinemate-port |
| UI-settings-qml-F2 | major | removed-upstream-behaviour | M | yes | Timecode card: upstream Mode no longer sets file timecode; Free Run / Rec Run renamed | qml/SettingsPage.qml diff:614-663@cinemate-port; qml/SettingsPage.qml diff:24-26, 234-236@cinemate-port |
| UI-settings-qml-F3 | major | new-ground | M | unknown | ClipNameCard: drag-and-drop composer with its own drag layer, untested on touch | qml/ClipNameCard.qml:238-313, 392-471, 578-600@cinemate-port; qml/ClipNamePill.qml:53-94@cinemate-port |
| UI-settings-qml-F4 | minor | mismatch | S | no | recordItemVisible() hides the Clip Names card | qml/SettingsPage.qml diff:269-273, 845@cinemate-port |
| UI-settings-qml-F5 | minor | mismatch | S | unknown | Storage pre-roll placed inside the Media Speed card | qml/SettingsPage.qml diff:706-776@cinemate-port |
| UI-settings-qml-F6 | minor | bug | S | no | UI text states Core settings as fixed values | qml/SettingsPage.qml diff:759@cinemate-port; qml/SettingsPage.qml diff:819@cinemate-port |
| UI-settings-qml-F7 | minor | mismatch | S | no | New items skip icon and favourite registration | qml/SettingsPage.qml diff:407-477@cinemate-port; qml/SettingsPage.qml diff:665-687@cinemate-port |
| UI-settings-qml-F9 | minor | bug | S | no | Clip-name edit lost when recording starts within the 1 s save delay | qml/ClipNameCard.qml:156-160, 317-327@cinemate-port |
| UI-settings-qml-F10 | minor | protocol | S | unknown | set_timecode_mode target ignored by an original Core | src/ApertarControlBridge.cpp:758-760@cinemate-port; qml/SettingsPage.qml diff:644, 659@cinemate-port |
| UI-settings-qml-F11 | minor | mismatch | S | no | Hand-sized sub-labels and fixed pill sizes in the new blocks | qml/SettingsPage.qml diff:526-531, 571-576, 720-725@cinemate-port; qml/ClipNameCard.qml:16-21, 350-355, 512-519@cinemate-port |
| UI-settings-qml-F8 | nit | bug | S | no | Clip-name card drops unknown tokens when it saves | qml/ClipNameCard.qml:28-34, 66-93, 156-170@cinemate-port |
| UI-settings-qml-F12 | nit | slop | S | no | Ticket tag T45 in code comments | qml/SettingsPage.qml:6455 (diff:798)@cinemate-port; qml/ControlsWarning.qml:3@cinemate-port |

## Unit WCP-01 (verified; /home/user/apertar-kb/working/merge-review/raw/rev-WCP-01.md)

| id | sev | category | effort | deliberate | title | where |
| --- | --- | --- | --- | --- | --- | --- |
| WCP-01-F1 | minor | slop | S | no | 8 CSS comments in a comment-free stylesheet; one carries T33, one names a stale panel | src/web/WebControlPage.cpp:196@cinemate-port; src/web/WebControlPage.cpp:230@cinemate-port |
| WCP-01-F2 | minor | mismatch | S | no | Speed Ramp card head uses new .switch-field + .wrap-head instead of the Gyro Data card recipe | src/web/WebControlPage.cpp:860-876@cinemate-port; src/web/WebControlPage.cpp:4980-4990@cinemate-port |
| WCP-01-F3 | minor | mismatch | S | no | Upstream Timecode card grids switched to ladder-named .pill-grid.ladder-pair | src/web/WebControlPage.cpp:1184-1186@cinemate-port; src/web/WebControlPage.cpp:5089@cinemate-port |
| WCP-01-F4 | minor | mismatch | M | no | Ladder buttons and tiles re-create upstream button variants and .preset-row | src/web/WebControlPage.cpp:883-893@cinemate-port; src/web/WebControlPage.cpp:1236-1245@cinemate-port |
| WCP-01-F5 | minor | slop | S | no | About 60 lines of rules with no element at HEAD, plus dead ladder helpers | src/web/WebControlPage.cpp:1028-1034@cinemate-port; src/web/WebControlPage.cpp:1045-1055@cinemate-port |
| WCP-01-F6 | minor | duplication | M | no | .value-chip and .clip-pill draw one chip and one remove button twice | src/web/WebControlPage.cpp:1416-1453@cinemate-port; src/web/WebControlPage.cpp:1476-1535@cinemate-port |
| WCP-01-F7 | minor | mismatch | S | no | 741 lines split the .pill-button group; mid-file 560px media block; variants before base | src/web/WebControlPage.cpp:850-1590@cinemate-port; src/web/WebControlPage.cpp:1371-1380@cinemate-port |
| WCP-01-F8 | minor | mismatch | S | no | body.media-browser-open renamed to the abbreviation body.pb-open, declared twice | src/web/WebControlPage.cpp:68-71@cinemate-port; src/web/WebControlPage.cpp:1980-1982@cinemate-port |
| WCP-01-F9 | minor | bug | M | no | Crop thumbnail hard-wired to a 16:9 3840x2160 sensor area | src/web/WebControlPage.cpp:912-930@cinemate-port; src/web/WebControlPage.cpp:7642@cinemate-port |
| WCP-01-F10 | minor | new-ground | M | yes | Clip names drag-and-drop composer where upstream reorders with buttons | src/web/WebControlPage.cpp:1455-1589@cinemate-port; src/web/WebControlPage.cpp:1548-1556@cinemate-port |
| WCP-01-F11 | nit | slop | S | no | One-line rules, duplicate selector, untokenised colour literals, third monospace stack | src/web/WebControlPage.cpp:1838-1839@cinemate-port; src/web/WebControlPage.cpp:1848@cinemate-port |
| WCP-01-F12 | nit | new-ground | S | yes | Settings search (.searching, .search-hidden): keep | src/web/WebControlPage.cpp:1814-1869@cinemate-port |

## Unit WCP-02 (verified; /home/user/apertar-kb/working/merge-review/raw/rev-WCP-02.md)

| id | sev | category | effort | deliberate | title | where |
| --- | --- | --- | --- | --- | --- | --- |
| WCP-02-F1 | major | mismatch | M | yes | Clip Browser and Viewer bring a second button/menu/chip/dialog set in the touch-UI look instead of the WebUI's own parts | src/web/WebControlPage.cpp:2061-2094@cinemate-port; src/web/WebControlPage.cpp:2103-2178@cinemate-port |
| WCP-02-F2 | major | mismatch | S | yes | White dropdowns scoped by panel and id, with a dark exception for pin selects | src/web/WebControlPage.cpp:3484-3559@cinemate-port; src/web/WebControlPage.cpp:35-36@cinemate-port |
| WCP-02-F3 | minor | mismatch | S | yes | Upstream .media-browser-* rules renamed to abbreviated .pb-*/.pbv-* | src/web/WebControlPage.cpp:1984-2016@cinemate-port; src/web/WebControlPage.cpp:69@cinemate-port |
| WCP-02-F4 | minor | mismatch | S | unknown | Media queries beside components at 1119/719/419 px and min-width, not in upstream's end blocks | src/web/WebControlPage.cpp:2452@cinemate-port; src/web/WebControlPage.cpp:2458@cinemate-port |
| WCP-02-F5 | minor | mismatch | S | no | Attribute and id selectors in CSS where upstream uses classes only | src/web/WebControlPage.cpp:3137@cinemate-port; src/web/WebControlPage.cpp:3184-3185@cinemate-port |
| WCP-02-F6 | minor | slop | S | no | 11 CSS comments, 3 with T49/T50/CineMate, 2 no longer true | src/web/WebControlPage.cpp:1979@cinemate-port; src/web/WebControlPage.cpp:2505@cinemate-port |
| WCP-02-F7 | minor | bug | S | no | Newly added GPIO in row gets a white pin dropdown, saved rows dark | src/web/WebControlPage.cpp:3526-3559@cinemate-port; src/web/WebControlPage.cpp:17453@cinemate-port |
| WCP-02-F8 | minor | removed-upstream-behaviour | S | yes | Media list facts and always-visible tools removed with the 36 upstream rules | src/web/WebControlPage.cpp:2298-2319@cinemate-port; src/web/WebControlPage.cpp:2355-2396@cinemate-port |
| WCP-02-F9 | nit | slop | S | no | Rules with no element: .controls-output-item, .controls-output-title | src/web/WebControlPage.cpp:3288-3301@cinemate-port |
| WCP-02-F10 | nit | duplication | S | no | body.pb-open twice; eight .x.hidden rules repeat global .hidden | src/web/WebControlPage.cpp:69@cinemate-port; src/web/WebControlPage.cpp:1980-1982@cinemate-port |

## Unit WCP-03 (verified; /home/user/apertar-kb/working/merge-review/raw/rev-WCP-03.md)

| id | sev | category | effort | deliberate | title | where |
| --- | --- | --- | --- | --- | --- | --- |
| WCP-03-F1 | major | mismatch | M | yes | Playback overlay brings its own widget layer: modal dialog, browser history, inline SVG, h1, nested state.pb | src/web/WebControlPage.cpp:6335-6494@cinemate-port; src/web/WebControlPage.cpp:6475-6487@cinemate-port |
| WCP-03-F2 | major | new-ground | M | yes | Boot Config card: a config.txt editor in the System pane | src/web/WebControlPage.cpp:5859-5951@cinemate-port; src/web/WebControlPage.cpp:20164@cinemate-port |
| WCP-03-F3 | minor | removed-upstream-behaviour | S | yes | Per-row Download/Delete and the Clear-selection button removed from the media list | src/web/WebControlPage.cpp:6376-6390@cinemate-port; src/web/WebControlPage.cpp:11880-11896@cinemate-port |
| WCP-03-F4 | minor | bug | S | no | Exact shutter angle (2 decimals) leaves no pill active, e.g. 60 fps at 22.5 deg | src/web/WebControlPage.cpp:7172-7181@cinemate-port; src/web/WebControlPage.cpp:7605-7621@cinemate-port |
| WCP-03-F5 | minor | mismatch | S | no | hidden attribute (17x) and five [hidden] CSS patches instead of the .hidden class | src/web/WebControlPage.cpp:5769-5827@cinemate-port; src/web/WebControlPage.cpp:5868-5936@cinemate-port |
| WCP-03-F6 | minor | mismatch | S | no | On/Off switches built from new widget classes (ladder-pair, switch-field) | src/web/WebControlPage.cpp:1184@cinemate-port; src/web/WebControlPage.cpp:860@cinemate-port |
| WCP-03-F7 | minor | mismatch | S | no | Recording-indicator switches placed in the Live preview read-out card | src/web/WebControlPage.cpp:5274-5291@cinemate-port |
| WCP-03-F8 | minor | mismatch | S | yes | Remote controls card on the main page | src/web/WebControlPage.cpp:4567-4580@cinemate-port |
| WCP-03-F9 | minor | mismatch | S | no | Performance card mixes camera, preview and storage settings in System | src/web/WebControlPage.cpp:5781-5830@cinemate-port; src/web/WebControlPage.cpp:10093-10101@cinemate-port |
| WCP-03-F10 | minor | new-ground | S | yes | Modes and Controls panels have no touch UI counterpart; Value Lists filed under Controls | src/web/WebControlPage.cpp:4750-4773@cinemate-port; src/web/WebControlPage.cpp:6137@cinemate-port |
| WCP-03-F11 | minor | new-ground | M | yes | Three editors for apertar-hardware.conf (Controls pane, Hardware card, text editor) | src/web/WebControlPage.cpp:6137-6160@cinemate-port; src/web/WebControlPage.cpp:6172-6191@cinemate-port |
| WCP-03-F12 | minor | slop | S | no | Operator text: env var name, history narration, Cinemate keyword, programmer words, long copy | src/web/WebControlPage.cpp:5818@cinemate-port; src/web/WebControlPage.cpp:5813@cinemate-port |
| WCP-03-F13 | minor | bug | S | no | A <label> wraps the Log pill grid: clicking 'Log' or its note presses the first pill | src/web/WebControlPage.cpp:4913-4917@cinemate-port |
| WCP-03-F14 | nit | removed-upstream-behaviour | S | yes | Timecode card lost its current-value pill | src/web/WebControlPage.cpp:5080-5094@cinemate-port |
| WCP-03-F15 | nit | slop | S | no | Comments in the state object and above formatAngle | src/web/WebControlPage.cpp:6673-6685@cinemate-port; src/web/WebControlPage.cpp:7172-7173@cinemate-port |

## Unit WCP-04 (verified; /home/user/apertar-kb/working/merge-review/raw/rev-WCP-04.md)

| id | sev | category | effort | deliberate | title | where |
| --- | --- | --- | --- | --- | --- | --- |
| WCP-04-F1 | major | mismatch | M | yes | IMX585 resolution pills read the Mode Ladder reply (state.ladderServer.pool) | src/web/WebControlPage.cpp:8955-8960@cinemate-port; src/web/WebControlPage.cpp:9021-9032@cinemate-port |
| WCP-04-F5 | major | new-ground | L | yes | Mode Ladder editor re-implements and extends Core's ladder rules in JS | src/web/WebControlPage.cpp:7628-8480@cinemate-port; src/web/WebControlPage.cpp:7765-7866@cinemate-port |
| WCP-04-F2 | minor | mismatch | S | yes | ladderRequest duplicates sendCommand's fetch path | src/web/WebControlPage.cpp:8004-8015@cinemate-port; src/web/WebControlPage.cpp:8017-8031@cinemate-port |
| WCP-04-F3 | minor | mismatch | S | unknown | Ladder fetched from inside renderModeLadder on every poll | src/web/WebControlPage.cpp:8394-8400@cinemate-port; src/web/WebControlPage.cpp:10174-10175@cinemate-port |
| WCP-04-F4 | minor | mismatch | S | unknown | Generic pill builders know the Mode Ladder (option.locked -> showLadderLockWarning) | src/web/WebControlPage.cpp:15029-15053@cinemate-port; src/web/WebControlPage.cpp:10718-10735@cinemate-port |
| WCP-04-F6 | minor | bug | S | no | Crop diagram and ladder names assume IMX585 3840x2160 readout for all sensors | src/web/WebControlPage.cpp:7642@cinemate-port; src/web/WebControlPage.cpp:7903-7924@cinemate-port |
| WCP-04-F7 | minor | slop | S | no | Stale, contradictory and orphan comments; section banners | src/web/WebControlPage.cpp:7628-7633@cinemate-port; src/web/WebControlPage.cpp:7565-7567@cinemate-port |
| WCP-04-F8 | minor | slop | S | no | Ticket numbers, Cinemate references, and UI text pointing to core.py | src/web/WebControlPage.cpp:7516@cinemate-port; src/web/WebControlPage.cpp:7566-7576@cinemate-port |
| WCP-04-F9 | minor | mismatch | S | unknown | Inline SVG icon strings instead of /icons PNGs | src/web/WebControlPage.cpp:7644-7650@cinemate-port |
| WCP-04-F10 | minor | bug | S | no | Card write speed parsed from display text with a regex | src/web/WebControlPage.cpp:7945-7949@cinemate-port |
| WCP-04-F11 | minor | pi-compat | S | no | Board-specific lossless encoder measurement in operator text | src/web/WebControlPage.cpp:8178-8180@cinemate-port |
| WCP-04-F12 | minor | removed-upstream-behaviour | S | yes | IMX585 resolution choice reshaped; 1.85:1 sizes need the port driver | src/web/WebControlPage.cpp:8922-8927@cinemate-port; src/web/WebControlPage.cpp:9021-9032@cinemate-port |
| WCP-04-F13 | nit | slop | S | no | Empty if-branch holding only a comment | src/web/WebControlPage.cpp:7503-7506@cinemate-port |
| WCP-04-F14 | nit | duplication | S | no | Small duplications: flicker-free maths, toast, DOM helper | src/web/WebControlPage.cpp:7590-7601@cinemate-port; src/web/WebControlPage.cpp:7982-7993@cinemate-port |
| WCP-04-F15 | nit | mismatch | S | unknown | Mode tables in mini string formats | src/web/WebControlPage.cpp:8915-8920@cinemate-port; src/web/WebControlPage.cpp:8756-8770@cinemate-port |

## Unit WCP-05 (verified; /home/user/apertar-kb/working/merge-review/raw/rev-WCP-05.md)

| id | sev | category | effort | deliberate | title | where |
| --- | --- | --- | --- | --- | --- | --- |
| WCP-05-F1 | minor | mismatch | S | yes | Mode Ladder lock wired into the generic pill builders; two lock mechanisms | src/web/WebControlPage.cpp:10446-10447@cinemate-port; src/web/WebControlPage.cpp:10728-10735@cinemate-port |
| WCP-05-F2 | minor | removed-upstream-behaviour | S | yes | Upstream timecode labels Free Run / Rec Run shown as Time of Day / Clip | src/web/WebControlPage.cpp:9796-9803@cinemate-port; src/web/WebControlPage.cpp:9819-9823@cinemate-port |
| WCP-05-F3 | minor | new-ground | S | yes | One timecode setting split into UI and file timecode; the favourite became two blocks | src/web/WebControlPage.cpp:9819-9827@cinemate-port; src/web/WebControlPage.cpp:11176-11182@cinemate-port |
| WCP-05-F4 | minor | new-ground | M | yes | Settings search with a MutationObserver and runtime DOM insertion | src/web/WebControlPage.cpp:10183-10289@cinemate-port |
| WCP-05-F5 | nit | new-ground | S | yes | History API for phone Back in the media overlay (pointer to the Playback unit) | src/web/WebControlPage.cpp:10115-10145@cinemate-port; src/web/WebControlPage.cpp:12777@cinemate-port |
| WCP-05-F6 | nit | mismatch | S | unknown | imx585Selected predicate next to inline indexOf for the other sensors | src/web/WebControlPage.cpp:8935@cinemate-port; src/web/WebControlPage.cpp:9036,9130,9236,9247,9268,9281,9293,9313@cinemate-port |
| WCP-05-F7 | nit | mismatch | S | no | Port labels use the ' · ' separator; upstream uses ' • ' | src/web/WebControlPage.cpp:9044@cinemate-port; src/web/WebControlPage.cpp:9791@cinemate-port |
| WCP-05-F8 | nit | slop | S | no | 'Older Core' fallbacks in a page served by the same Core binary | src/web/WebControlPage.cpp:10891@cinemate-port; src/web/WebControlPage.cpp:15253-15255@cinemate-port |
| WCP-05-F9 | nit | slop | S | no | Ticket tokens (Q2, T33, T34, Request 24) in comments | src/web/WebControlPage.cpp:10123@cinemate-port; src/web/WebControlPage.cpp:7568,7576,7636,8483@cinemate-port |

## Unit WCP-06 (verified; /home/user/apertar-kb/working/merge-review/raw/rev-WCP-06.md)

| id | sev | category | effort | deliberate | title | where |
| --- | --- | --- | --- | --- | --- | --- |
| WCP-06-F1 | major | mismatch | M | no | Upstream media state and function names replaced by nested state.pb and pb*/pbv* families | src/web/WebControlPage.cpp:6723-6727@cinemate-port; src/web/WebControlPage.cpp:11653-12928@cinemate-port |
| WCP-06-F2 | minor | mismatch | S | yes | Custom remove scrim dialog where the WebUI convention is window.confirm | src/web/WebControlPage.cpp:12036-12048@cinemate-port; src/web/WebControlPage.cpp:12107-12118@cinemate-port |
| WCP-06-F3 | minor | slop | S | no | Tracker ids and history narration in Playback comments | src/web/WebControlPage.cpp:10123@cinemate-port; src/web/WebControlPage.cpp:11649@cinemate-port |
| WCP-06-F4 | minor | removed-upstream-behaviour | S | unknown | Clip cards lost size, fps, frame count and per-row Download/Delete; non-cDNG items show them nowhere | src/web/WebControlPage.cpp:11816-11926@cinemate-port; src/web/WebControlPage.cpp:12784-12789@cinemate-port |
| WCP-06-F5 | minor | bug | S | no | Viewer keeps previous clip's FPS/DROP badges, time and Info rows when a non-cDNG item opens | src/web/WebControlPage.cpp:12766-12797@cinemate-port |
| WCP-06-F6 | minor | bug | S | no | Clip opened during a hold stays blank after the hold ends | src/web/WebControlPage.cpp:12795-12798@cinemate-port; src/web/WebControlPage.cpp:12875-12886@cinemate-port |
| WCP-06-F7 | minor | bug | S | no | Playback freezes at the end when the WAV is shorter than the frame span (probable) | src/web/WebControlPage.cpp:12545-12575@cinemate-port; src/web/WebControlPage.cpp:12189@cinemate-port |
| WCP-06-F9 | minor | duplication | S | no | pbvTimecodeAt and pbvClock re-implement formatTimecode and pad2 | src/web/WebControlPage.cpp:12220-12238@cinemate-port |
| WCP-06-F13 | minor | pi-compat | S | yes | Player pacing (0.35 s look-ahead, two lanes at 640 w) measured on Pi 5 only | src/web/WebControlPage.cpp:12209-12218@cinemate-port; src/web/WebControlPage.cpp:12247-12255@cinemate-port |
| WCP-06-F8 | nit | bug | S | no | Failed remove from the viewer closes the viewer | src/web/WebControlPage.cpp:12050-12081@cinemate-port |
| WCP-06-F10 | nit | mismatch | S | no | Snapshot merge uses typeof === 'number' instead of isFiniteNumber; env-knob field reaches the page | src/web/WebControlPage.cpp:13835@cinemate-port; src/web/WebControlPage.cpp:13845@cinemate-port |
| WCP-06-F11 | nit | slop | S | no | Dead indirection and unused parameters | src/web/WebControlPage.cpp:11812@cinemate-port; src/web/WebControlPage.cpp:12209@cinemate-port |
| WCP-06-F12 | nit | mismatch | S | no | state.previewPausedForPlayback not declared in the state literal | src/web/WebControlPage.cpp:12138@cinemate-port; src/web/WebControlPage.cpp:13763@cinemate-port |

## Unit WCP-07 (verified; /home/user/apertar-kb/working/merge-review/raw/rev-WCP-07.md)

| id | sev | category | effort | deliberate | title | where |
| --- | --- | --- | --- | --- | --- | --- |
| WCP-07-F1 | major | new-ground | M | yes | Clip-name composer: ~570 lines of drag-and-drop + long-press for one template string | src/web/WebControlPage.cpp:14453-15024@cinemate-port; Apertar-UI qml/ClipNameCard.qml, qml/ClipNamePill.qml@cinemate-port |
| WCP-07-F2 | minor | mismatch | S | no | Composer state outside state, UPPER_CASE constants, one-letter fields | src/web/WebControlPage.cpp:14456-14495@cinemate-port |
| WCP-07-F3 | minor | mismatch | S | unknown | Buffer/pre-roll setting fields published twice by Core; page copies system.* to the top level | src/web/WebControlPage.cpp:15215-15222@cinemate-port; src/web/WebControlPage.cpp:13841-13860@cinemate-port |
| WCP-07-F4 | minor | mismatch | S | no | Buffer note parsed by regex; 60 % / 12 frames / 90 % hard-coded | src/web/WebControlPage.cpp:15467-15470@cinemate-port; src/web/WebControlPage.cpp:15478-15480@cinemate-port |
| WCP-07-F5 | minor | removed-upstream-behaviour | S | yes | ISO / WB badges no longer say Auto | src/web/WebControlPage.cpp:15398-15406@cinemate-port; src/web/WebControlPage.cpp:15507@cinemate-port |
| WCP-07-F6 | minor | removed-upstream-behaviour | S | yes | Record button greyed without media; guards test a different field, Core's reason never shown | src/web/WebControlPage.cpp:15772-15773@cinemate-port; src/web/WebControlPage.cpp:15253-15255@cinemate-port |
| WCP-07-F7 | minor | mismatch | S | unknown | APERTAR_* env-var names in operator text; _env state flags | src/web/WebControlPage.cpp:5818@cinemate-port; src/web/WebControlPage.cpp:15852@cinemate-port |
| WCP-07-F8 | minor | mismatch | S | no | Pre-roll auto switch not shaped like an upstream toggle | src/web/WebControlPage.cpp:15827-15855@cinemate-port; src/ApertarCoreApp.cpp:12900-12906@cinemate-port |
| WCP-07-F9 | minor | bug | S | no | Log 'Not applied' note always blames IMX585 SDR compression | src/web/WebControlPage.cpp:15456-15457@cinemate-port; src/camera/CameraController.cpp:12511-12514@cinemate-port |
| WCP-07-F10 | nit | duplication | S | yes | clipRawCommand: second /api/command wrapper | src/web/WebControlPage.cpp:14577-14588@cinemate-port |
| WCP-07-F11 | nit | slop | S | no | Narrating comments, non-ASCII glyphs, lowercase status fragment | src/web/WebControlPage.cpp:14453-14455@cinemate-port; src/web/WebControlPage.cpp:15398@cinemate-port |
| WCP-07-F12 | nit | slop | S | no | 'Custom' preset pill forced disabled-but-active via DOM pokes | src/web/WebControlPage.cpp:14960-14972@cinemate-port |

## Unit WCP-08 (verified; /home/user/apertar-kb/working/merge-review/raw/rev-WCP-08.md)

| id | sev | category | effort | deliberate | title | where |
| --- | --- | --- | --- | --- | --- | --- |
| WCP-08-F1 | major | mismatch | M | yes | Second 4 Hz poll loop, second global store and pill DOM edits outside renderSnapshot | src/web/WebControlPage.cpp:16419-16421@cinemate-port; src/web/WebControlPage.cpp:16430-16433@cinemate-port |
| WCP-08-F2 | minor | duplication | S | no | Pre-roll, safety-stop pill and timer-start logic written twice | src/web/WebControlPage.cpp:16441-16456@cinemate-port; src/web/WebControlPage.cpp:15758-15767@cinemate-port |
| WCP-08-F3 | minor | slop | S | no | Narrating and out-of-date comments, three ad-hoc 1000 ms freshness windows | src/web/WebControlPage.cpp:16416-16425@cinemate-port; src/web/WebControlPage.cpp:16455@cinemate-port |
| WCP-08-F4 | minor | new-ground | S | yes | Faster-than-1 Hz server poll exists only because /api/state blocks during a RAM drain | src/web/WebControlPage.cpp:16562-16572@cinemate-port; src/ApertarCoreApp.cpp:8418-8426@cinemate-port |

## Unit WCP-09 (NOT verified; /home/user/apertar-kb/working/merge-review/raw/rev-WCP-09.md)

| id | sev | category | effort | deliberate | title | where |
| --- | --- | --- | --- | --- | --- | --- |
| WCP-09-F1 | major | mismatch | M | unknown | Second client store controlsState plus 18 module-level consts/lets | src/web/WebControlPage.cpp:16633@cinemate-port; src/web/WebControlPage.cpp:16798@cinemate-port |
| WCP-09-F2 | major | mismatch | S | unknown | Second fetch wrapper controlsCall; hand-checked ok and missing try/catch | src/web/WebControlPage.cpp:16698-16705@cinemate-port; src/web/WebControlPage.cpp:17687@cinemate-port |
| WCP-09-F3 | major | mismatch | S | yes | Remote controls card on the main page with hold-to-repeat pills | src/web/WebControlPage.cpp:4569-4580@cinemate-port; src/web/WebControlPage.cpp:17995-18042@cinemate-port |
| WCP-09-F4 | major | new-ground | L | yes | 2100-line structured hardware editor with extras; size and shape foreign | src/web/WebControlPage.cpp:16622-18710@cinemate-port; src/web/WebControlPage.cpp:16875-16880@cinemate-port |
| WCP-09-F5 | minor | bug | S | no | Saving Controls or Hardware silently drops the other card's unsaved edits | src/web/WebControlPage.cpp:18240@cinemate-port; src/web/WebControlPage.cpp:18668@cinemate-port |
| WCP-09-F6 | minor | bug | S | no | Pins recovered by regex from Core's display text | src/web/WebControlPage.cpp:17163-17189@cinemate-port; src/web/WebControlPage.cpp:17598@cinemate-port |
| WCP-09-F7 | minor | bug | S | no | Unhandled rejections: Scan sticks at Scanning..., Listen overlaps requests | src/web/WebControlPage.cpp:18183-18189@cinemate-port; src/web/WebControlPage.cpp:18624-18648@cinemate-port |
| WCP-09-F8 | minor | mismatch | S | yes | Listen is a third poll loop (300 ms) with its own timer outside state | src/web/WebControlPage.cpp:18609-18649@cinemate-port |
| WCP-09-F9 | minor | new-ground | S | yes | Chip editor: duck-typed fake select with drag and drop | src/web/WebControlPage.cpp:16799-16872@cinemate-port; src/web/WebControlPage.cpp:16831-16835@cinemate-port |
| WCP-09-F10 | minor | mismatch | S | yes | Inline message/review/pending boxes duplicate toasts | src/web/WebControlPage.cpp:18671-18673@cinemate-port; src/web/WebControlPage.cpp:18243-18245@cinemate-port |
| WCP-09-F11 | minor | removed-upstream-behaviour | S | yes | Tally enabled hidden and derived from the pin; None/Remove erases the wiring | src/web/WebControlPage.cpp:17619-17646@cinemate-port; src/web/WebControlPage.cpp:17704-17705@cinemate-port |
| WCP-09-F12 | minor | mismatch | M | yes | Hardware-file whole-text write through a command while upstream's door is /api/config | src/web/WebControlPage.cpp:18588@cinemate-port; src/web/WebControlPage.cpp:18264@cinemate-port |
| WCP-09-F13 | minor | pi-compat | S | yes | Any DPI line greys GPIO 0-27 regardless of overlay | src/web/WebControlPage.cpp:17198-17200@cinemate-port; src/web/WebControlPage.cpp:17261-17264@cinemate-port |
| WCP-09-F14 | minor | duplication | S | no | Issues box x3, Test handler x2, kind-name map x3, DPI loop x2 | src/web/WebControlPage.cpp:16718@cinemate-port; src/web/WebControlPage.cpp:18129@cinemate-port |
| WCP-09-F15 | minor | slop | S | no | 127 comment lines incl. T39-T42 ticket ids and 'as in Cinemate' | src/web/WebControlPage.cpp:16795@cinemate-port; src/web/WebControlPage.cpp:16874@cinemate-port |
| WCP-09-F16 | nit | mismatch | S | no | Yes/No select for bools, inline grid style, 'GPIO in' vs 'GPIO buttons', loadX naming | src/web/WebControlPage.cpp:17716-17726@cinemate-port; src/web/WebControlPage.cpp:18065@cinemate-port |
| WCP-09-F17 | nit | slop | S | no | One-entry Function dropdown for outputs | src/web/WebControlPage.cpp:17821@cinemate-port; src/web/WebControlPage.cpp:17859-17870@cinemate-port |

## Unit WCP-10 (verified; /home/user/apertar-kb/working/merge-review/raw/rev-WCP-10.md)

| id | sev | category | effort | deliberate | title | where |
| --- | --- | --- | --- | --- | --- | --- |
| WCP-10-F1 | major | mismatch | M | unknown | Boot Config posts to its own route instead of /api/command | src/web/WebControlPage.cpp:20004-20016@cinemate-port; src/ApertarCoreApp.cpp:9170-9196@cinemate-port |
| WCP-10-F2 | major | mismatch | M | no | bootConfig page-side store and own installer beside state | src/web/WebControlPage.cpp:19872-19884@cinemate-port; src/web/WebControlPage.cpp:20553-20606@cinemate-port |
| WCP-10-F3 | major | new-ground | M | yes | Boot Config card over-built: Edit file, live managed-line marks, legend, own-lines hint | src/web/WebControlPage.cpp:19868-20606@cinemate-port; src/web/WebControlPage.cpp:20490-20515@cinemate-port |
| WCP-10-F4 | major | security | S | unknown | Edit file sends whole config.txt to a root write; set_boot_config has no revision guard on /api/command | src/web/WebControlPage.cpp:19999@cinemate-port; src/ApertarCoreApp.cpp:3790-3794@cinemate-port |
| WCP-10-F5 | minor | mismatch | S | yes | Display-change checkbox gate instead of window.confirm | src/web/WebControlPage.cpp:20282-20314@cinemate-port |
| WCP-10-F6 | minor | bug | S | no | Reboot wait polls /api/buffer; the 60 s never-down rule misreports a slow shutdown | src/web/WebControlPage.cpp:20355-20403@cinemate-port |
| WCP-10-F7 | minor | mismatch | S | no | Config Check and Save use two transports; Check falls back to base "h" and then always fails | src/web/WebControlPage.cpp:18795@cinemate-port; src/web/WebControlPage.cpp:18918-18927@cinemate-port |
| WCP-10-F8 | minor | duplication | S | no | Two diff renderers; bootConfigOption re-implements ensureSelectEntries | src/web/WebControlPage.cpp:18854-18887@cinemate-port; src/web/WebControlPage.cpp:20225-20317@cinemate-port |
| WCP-10-F9 | minor | mismatch | S | yes | Remote controls loader runs its own untracked 5 s setTimeout loop | src/web/WebControlPage.cpp:20869-20878@cinemate-port |
| WCP-10-F11 | minor | slop | S | no | T43 tags, Cinemate history and a banner in comments; 32 comment lines | src/web/WebControlPage.cpp:18758@cinemate-port; src/web/WebControlPage.cpp:18792@cinemate-port |
| WCP-10-F10 | nit | new-ground | S | yes | toggleRecord decides 'flushing' from page-side frameBufferBar | src/web/WebControlPage.cpp:19199-19204@cinemate-port; src/web/WebControlPage.cpp:19240@cinemate-port |
| WCP-10-F12 | nit | new-ground | S | yes | Save Config now takes two clicks (diff, then Save these changes) | src/web/WebControlPage.cpp:20884@cinemate-port; src/web/WebControlPage.cpp:18854-18887@cinemate-port |
| WCP-10-F13 | nit | mismatch | S | no | Toast 'Storage pre-roll started' lacks the period | src/web/WebControlPage.cpp:19828@cinemate-port |

## Sweep board-support (verified; /home/user/apertar-kb/working/merge-review/raw/sweep-board-support.md)

| id | sev | category | effort | deliberate | title | where |
| --- | --- | --- | --- | --- | --- | --- |
| X-board-support-1 | major | removed-upstream-behaviour | S | yes | Controls page models only the 40-pin header; chip= is gone from the card | src/hardware/ControlsModel.hpp:258-271; src/hardware/ControlsModel.hpp:381 |
| X-board-support-2 | major | stock-behaviour-change | S | yes | Display defaults are the owner's HDMI rig; the touch UI is hidden when the key is missing | UI src/DisplayConfigBridge.cpp:11-12; UI src/DisplayConfigBridge.cpp:289-294 |
| X-board-support-3 | major | bug | S | unknown | Boot Config card does not see include camera-selection.txt | src/hardware/BootConfigText.hpp:270-307; src/hardware/BootConfigText.hpp:616-622 |
| X-board-support-4 | minor | mismatch | S | unknown | Third board detector, matching by substring, with its own config.txt filter rules | src/hardware/BootConfigText.hpp:76-122; src/ApertarCoreApp.cpp:3653-3657 |
| X-board-support-5 | minor | pi-compat | S | unknown | Controls validator reads config.txt as a Pi 5 would | src/hardware/HardwareConfigText.hpp:1037-1051; src/ApertarCoreApp.cpp:4976 |
| X-board-support-6 | minor | pi-compat | S | unknown | Link-frequency cap exists for family pi4 only | src/hardware/BootConfigText.hpp:147; src/hardware/BootConfigText.hpp:186 |
| X-board-support-7 | minor | pi-compat | M | yes | Raw write path changed for every board and was run on one CM5 | src/camera/CameraController.cpp:1334-1338; src/camera/CameraController.cpp:1458-1470 |
| X-board-support-8 | minor | pi-compat | S | yes | Raw copy pool is kept between takes | src/camera/CameraController.cpp:4935-4945; src/camera/CameraController.cpp:5547-5550 |
| X-board-support-9 | minor | mismatch | S | unknown | New cards do not follow recording_capabilities | src/camera/CameraController.cpp:10838-10843; src/camera/CameraController.cpp:10949-10958 |
| X-board-support-10 | minor | pi-compat | S | unknown | Media tuning helper sets dirty-page limits in absolute bytes | scripts/apertar-media-tune:68-71; scripts/apertar-media-tune:87-90 |
| X-board-support-13 | minor | bug | S | no | Clip viewer refuses 8-bit DNG that Core itself writes | src/playback/DngTags.hpp:307-312; src/playback/DngFrameReader.hpp:67-82 |
| X-board-support-14 | minor | pi-compat | S | yes | Sensor paths run on a CM5 only | src/camera/Imx585Modes.hpp:40-98; src/camera/CameraController.cpp:8295-8296 |
| X-board-support-15 | minor | stock-behaviour-change | S | yes | Preview temporal denoise off by default also changes recorded ISP output | include/apertar/core/Types.hpp:139; src/camera/CameraController.cpp:7306-7318 |
| X-board-support-11 | nit | stock-behaviour-change | S | unknown | Root helper requires a [pi5], [pi4] or [all] header, and fan mode now goes through it | scripts/apertar-boot-config:51-54; src/ApertarCoreApp.cpp:3589-3591 |
| X-board-support-12 | nit | pi-compat | S | unknown | APERTAR_RT=1 pins Core to cores 1 to 3 without checking | scripts/start-apertar-core.sh:28; scripts/start-apertar-core.sh:35-37 |
| X-board-support-16 | nit | pi-compat | S | yes | Drivers need kernel 6.12 | imx283-v4l2-driver imx283.c:10; imx283-v4l2-driver README.md:9 |

## Sweep commits-core-1 (NOT verified; /home/user/apertar-kb/working/merge-review/raw/sweep-commits-core-1.md)

| id | sev | category | effort | deliberate | title | where |
| --- | --- | --- | --- | --- | --- | --- |
| X-commits-core-1-1 | major | commit | M | no | Commits that do not compile on their own | 80ddac1; 8f7dc39 |
| X-commits-core-1-3 | major | commit | L | no | Chain of 36 WebUI wording and tweak commits around the Mode Ladder | 1ef94fe; 24355d3 |
| X-commits-core-1-4 | major | commit | M | no | fsync/writeback experiments committed as a chain | 4ce382e; 441e42a |
| X-commits-core-1-5 | major | new-ground | M | unknown | Media tuning shipped, then switched off; privileged helper has no upstream precedent | 26da30e; 0358fcf |
| X-commits-core-1-6 | major | slop | M | no | Tutorial numbers and internal ids in subjects and bodies | b0e90ad; ff33d2d |
| X-commits-core-1-8 | major | commit | L | no | Mixed-purpose commits | 438a342; 26da30e |
| X-commits-core-1-9 | major | stock-behaviour-change | S | yes | b5b787e reverses a 1.6.0 behaviour inside a mixed commit | b5b787e; 2f43ecc |
| X-commits-core-1-11 | major | new-ground | M | unknown | New ground with no Apertar upstream precedent introduced in this half | 1af26c8; third_party/liblj92 |
| X-commits-core-1-2 | minor | commit | S | no | Add-then-remove and flip-flop pairs | 97adea0; bcedbe5 |
| X-commits-core-1-7 | minor | commit | S | unknown | Co-Authored-By and Tested: trailers on every commit; Tested: text is a run log | all 95 commits |
| X-commits-core-1-10 | minor | commit | S | no | Subjects that do not say what changed, and prefix mismatches | e16033e; 1ef94fe |
| X-commits-core-1-12 | nit | commit | S | no | Unrelated small commits inside topic chains | 086443c; d7ff071 |

## Sweep commits-core-2 (NOT verified; /home/user/apertar-kb/working/merge-review/raw/sweep-commits-core-2.md)

| id | sev | category | effort | deliberate | title | where |
| --- | --- | --- | --- | --- | --- | --- |
| X-commits-core-2-1 | blocker | commit | L | no | d44b177 squashes 12 features under a 7-feature subject | d44b177 |
| X-commits-core-2-2 | major | commit | S | yes | Message and diff disagree: 04bac89 and e0fa852 carry each other's hunks | 04bac89; e0fa852 |
| X-commits-core-2-3 | major | commit | M | no | Tutorial and work-package numbers and 'part N' in subjects | 4629de2; a37a902 |
| X-commits-core-2-4 | major | commit | L | no | Controls page and gestures rewritten four times; page and Core halves in separate commits | d282de9; f5fe41b |
| X-commits-core-2-5 | major | commit | M | no | Merges of side branches hide conflict resolution and one is pure noise | 4581a69; 4b2eeac |
| X-commits-core-2-6 | major | commit | M | no | Behaviour added then reversed inside the series | d44b177; caa0153 |
| X-commits-core-2-7 | major | knob | M | yes | Env-knob commits made moot by later commits | c57c284; 6ef0ddc |
| X-commits-core-2-8 | major | commit | S | unknown | Eleven commits authored 'Claude' and three trailer names | f19b245; dda1713 |
| X-commits-core-2-9 | minor | commit | S | no | Subjects that say nothing or use a branch name as prefix | 766aba8; afa00e8 |
| X-commits-core-2-10 | minor | commit | S | no | Dead-code and not-run commits in the series | 3526e4b; f19b245 |
| X-commits-core-2-11 | minor | commit | M | no | Commit bodies hold behaviour changes the subject hides | 916c1dd; 243fe2c |
| X-commits-core-2-14 | minor | new-ground | M | unknown | Controls, boot-config and split-clip features are large new ground bundled in drive-test commits | 3526e4b; f19b245 |
| X-commits-core-2-12 | nit | commit | S | no | Unrelated features and layout churn placed between others | 2c259b9; a40112a |
| X-commits-core-2-13 | nit | commit | S | unknown | Tests and A/B data referenced only in bodies | e55557d; 4abbef0 |

## Sweep commits-ui-drivers (NOT verified; /home/user/apertar-kb/working/merge-review/raw/sweep-commits-ui-drivers.md)

| id | sev | category | effort | deliberate | title | where |
| --- | --- | --- | --- | --- | --- | --- |
| X-commits-ui-drivers-2 | major | bug | S |  | Touch UI caps 4K Clear HDR 16-bit at 25 fps; Core removed that cap | Apertar-UI qml/CameraPage.qml:820-822@cinemate-port; Apertar-UI d1efb67 |
| X-commits-ui-drivers-5 | major | protocol | M |  | UI commits depend on Core commits and cannot merge alone | Apertar-UI 41ff827; Apertar-UI c9d841f |
| X-commits-ui-drivers-7 | major | commit | M |  | imx585 history is experiment-and-fix steps, with WP-585 numbers and 'experimental:' subjects | imx585-v4l2-driver e711fc9..4949b06; imx585-v4l2-driver 475c3ea |
| X-commits-ui-drivers-8 | major | commit | M |  | imx283 history: one experiment in 11 commits ended by a revert, values flipped back and forth | imx283-v4l2-driver 4350e3e..a852cfe; imx283-v4l2-driver c20c603..cb925e5 |
| X-commits-ui-drivers-9 | major | mismatch | S |  | imx585 README describes 7 modes under a gone branch; READMEs do not link APERTAR.md | imx585-v4l2-driver README.md:148; imx585-v4l2-driver README.md:155 |
| X-commits-ui-drivers-1 | minor | commit | S |  | Eight preview experiment commits net to nothing but stay in history | Apertar-UI a51c95e; Apertar-UI 322d329 |
| X-commits-ui-drivers-3 | minor | knob | S |  | UI preview-FPS env knob kept after its eight sibling experiments were dropped | Apertar-UI src/ApertarPreviewSocketClient.cpp:26-33; Apertar-UI src/ApertarPreviewSocketClient.cpp:488 |
| X-commits-ui-drivers-6 | minor | commit | M |  | UI commit bodies carry internal numbers, branch prefixes and 'not built' notes | Apertar-UI ed0d7b5; Apertar-UI c9d841f |
| X-commits-ui-drivers-4 | nit | commit | S |  | UI colour and label churn: green, white, italic; 16-bit, 16 b, 16-bit | Apertar-UI f1edf96; Apertar-UI 7840438 |

## Sweep knobs (verified; /home/user/apertar-kb/working/merge-review/raw/sweep-knobs.md)

| id | sev | category | effort | deliberate | title | where |
| --- | --- | --- | --- | --- | --- | --- |
| X-knobs-2 | blocker | stock-behaviour-change | S | yes | The display fallback is the contributor's HDMI rig | Apertar-UI/src/DisplayConfigBridge.cpp:11-12; Apertar-UI/src/DisplayConfigBridge.cpp:289 |
| X-knobs-3 | major | stock-behaviour-change | S | yes | The storage pre-roll runs by itself (default on) | src/util/StoragePreroll.hpp:98; src/ApertarCoreApp.cpp:5069-5072 |
| X-knobs-4 | major | stock-behaviour-change | S | yes | preview_tdn=false also strips temporal denoise from H.264 and ProRes recordings | include/apertar/core/Types.hpp:139; src/camera/CameraController.cpp:7309-7318 |
| X-knobs-6 | major | duplication | M | yes | A second bench-tuning mechanism beside upstream's .apertar-tuning | src/util/MediaTune.hpp; scripts/apertar-tune |
| X-knobs-9 | major | knob | M | yes | Experiment leftovers among the env vars (27 names, RT scheduling, LimitRTPRIO) | scripts/start-apertar-core.sh:20-41; config/apertar-core-capture-priority.conf |
| X-knobs-5 | minor | stock-behaviour-change | S | yes | The record gate's opt-out is an undocumented env var | src/ApertarCoreApp.cpp:11331-11337; src/ApertarCoreApp.cpp:11359-11384 |
| X-knobs-7 | minor | mismatch | M | yes | Storage switches in two stores, edited by App itself | src/ApertarCoreApp.cpp:12829-12925; src/util/BufferBudget.hpp:150-195 |
| X-knobs-8 | minor | knob | S | yes | Env twins silently beat a UI switch | src/ApertarCoreApp.cpp:262-276; src/ApertarCoreApp.cpp:6402 |
| X-knobs-10 | minor | security | S | yes | The kernel-tune root helper chain never ran | scripts/apertar-media-tune; config/apertar-media.sudoers |
| X-knobs-11 | minor | slop | S | yes | The eject flag has no reader | src/util/MediaIntent.hpp:10-58; src/ApertarCoreApp.cpp:4355 |
| X-knobs-12 | minor | slop | S | unknown | Knobs that do nothing: conform_fps, hold_ms/double_ms, directIo | include/apertar/core/Types.hpp:137; src/camera/CameraController.cpp:696-697 |
| X-knobs-13 | minor | mismatch | S | yes | Clear HDR ISO caps as a [camera] section of the hardware file | src/camera/CameraController.cpp:2933-2981; src/ApertarCoreApp.cpp:5074-5079 |
| X-knobs-15 | minor | slop | S | yes | README documents bench knobs, install recipes and private references | README.md:202-203; README.md:303-310 |
| X-knobs-16 | minor | mismatch | S | yes | Three write routes for config.txt; new shell helpers in Core | src/ApertarCoreApp.cpp:3530-3611; src/ApertarCoreApp.cpp:11478-11500 |
| X-knobs-17 | minor | knob | S | unknown | IMX283 driver default and Core default cancel each other | imx283-v4l2-driver/imx283.c:269-281; src/camera/Imx283Modes.hpp:138 |
| X-knobs-1 | nit | knob | S | yes | set_controls refuses the GPIO keys [gpio_encoders] shares | src/hardware/HardwareConfigText.hpp:460-462@04fe197; src/hardware/GpioInput.cpp:336-355 |
| X-knobs-14 | nit | duplication | S | yes | modeLadderPath() copies persistedSettingsPath() | src/camera/CameraController.cpp:404-415; src/camera/CameraController.cpp:417-428 |
| X-knobs-18 | nit | commit | S | yes | Eight UI commits add and drop three env knobs | Apertar-UI c13b846; a51c95e |
| X-knobs-19 | nit | mismatch | S | unknown | Two boolean spellings in camera_settings.conf | src/camera/CameraController.cpp:974-979 |

## Sweep protocol-security (verified; /home/user/apertar-kb/working/merge-review/raw/sweep-protocol-security.md)

| id | sev | category | effort | deliberate | title | where |
| --- | --- | --- | --- | --- | --- | --- |
| X-protocol-security-1 | major | security | M | yes | Any LAN client can write arbitrary text into /boot/firmware/config.txt as root | src/ApertarCoreApp.cpp:3775-3850; src/ApertarCoreApp.cpp:3532-3608 |
| X-protocol-security-2 | major | security | S | no | test_input lets the LAN run any readable file with bash, without a button press | src/ApertarCoreApp.cpp:12393-12415; src/ApertarCoreApp.cpp:12565-12566 |
| X-protocol-security-5 | minor | mismatch | M | yes | Six commands run before commandMutex_; get_controls is not read-only | src/ApertarCoreApp.cpp:12559-12571; src/ApertarCoreApp.cpp:12418-12556 |
| X-protocol-security-7 | minor | mismatch | S | unknown | Two doors to set_boot_config with different guards; HTTP route wraps the command parser | src/ApertarCoreApp.cpp:9170-9198; src/ApertarCoreApp.cpp:14589-14590 |
| X-protocol-security-3 | nit | protocol | S | unknown | Port UI ISO Lock does nothing against a 1.6.0 Core | Apertar-UI src/ApertarControlBridge.cpp:300-308; Apertar-UI qml/CameraPage.qml:531 |
| X-protocol-security-4 | nit | protocol | S | unknown | set_timecode_mode target= is ignored by a 1.6.0 Core | Apertar-UI src/ApertarControlBridge.cpp:750-771; core-upstream src/ApertarCoreApp.cpp:9424-9436 |
| X-protocol-security-6 | nit | bug | S | no | get_state emits media_state twice | src/ApertarCoreApp.cpp:12944; src/ApertarCoreApp.cpp:12961 |
| X-protocol-security-8 | nit | protocol | M | yes | Port UI polls get_state at 1 Hz while auto ISO or auto WB is on | Apertar-UI src/ApertarControlBridge.cpp:18-20; Apertar-UI src/ApertarControlBridge.cpp:1012-1018 |
| X-protocol-security-9 | nit | new-ground | S | yes | sudoers files are new ground and imply a hardening Core does not have | config/apertar-boot-config.sudoers; config/apertar-media-trim.sudoers |

## Sweep slop (NOT verified; /home/user/apertar-kb/working/merge-review/raw/sweep-slop.md)

| id | sev | category | effort | deliberate | title | where |
| --- | --- | --- | --- | --- | --- | --- |
| X-slop-1 | major | slop | M | no | Tutorial and work-package ids in Core comments | src/ApertarCoreApp.cpp (52 lines, e.g. :1272 :6335 :7354 :12168); src/web/WebControlPage.cpp (32, e.g. :1398 :7568 :12151) |
| X-slop-2 | major | slop | S | no | Pointers to the private KB, critics and design sketch | src/ApertarCoreApp.cpp:92,10897,10927,11377; src/camera/CameraController.cpp:3430,4888,9112 |
| X-slop-3 | major | slop | S | no | Names, dates and clip numbers of test runs in comments | src/camera/CameraController.cpp:3025,3034,3099,3154,3428,4357,4714,4734,9066; src/audio/AudioRecordingSession.cpp:210,590,752 |
| X-slop-4 | major | slop | S | no | Cinemate-branded strings reach the journal, clip metadata and operator-readable files | src/camera/CameraController.cpp:3985,4008,11350; src/cdng/LogCurve.hpp:48 |
| X-slop-6 | major | slop | L | unknown | Comment density far above upstream | src/camera/CameraController.hpp (185 vs 7 per 1000); src/camera/CameraController.cpp (54 vs 9) |
| X-slop-7 | major | slop | M | no | Comments that narrate history or a debugging story | src/audio/AudioRecordingSession.cpp:209-211,589-591,751-753; src/camera/CameraController.cpp:4356-4358,4713-4715,4733-4735,9065-9069,3025-3027,3428-3431 |
| X-slop-8 | major | slop | M | no | Work-package ids and dated test results in the imx585 driver | imx585-v4l2-driver imx585.c:606,709,769-847,1008,1018,1026,4449-4470 (53 lines with WP-585-N); tools/clearhdr-gate/README.md (8 lines) |
| X-slop-9 | major | slop | M | no | Dated debugging history and clip names in the imx283 driver | imx283-v4l2-driver imx283.c:265,439,678-740,765-800,842,1313; EXPERIMENTAL_CROPS.md:24,27,33,64,134 |
| X-slop-5 | minor | slop | S | no | Cinemate used as justification and commit hashes of another project in comments | src/ApertarCoreApp.cpp:1293,4387,10846; src/camera/CameraController.cpp:1462,8907,9068,10729,10736,10748 |
| X-slop-11 | minor | slop | S | no | Dead field that says it is unused | src/util/MediaProfile.hpp:133 |
| X-slop-12 | minor | slop | S | unknown | Over-long operator hints in the WebUI | src/web/WebControlPage.cpp (boot-config card hint 305 chars); clip-name card hint 247 chars |
| X-slop-13 | minor | slop | S | unknown | Private branch names and provenance in the driver docs and README | imx585-v4l2-driver APERTAR.md,README.md:37,148,159,206; imx283-v4l2-driver APERTAR.md:12-14,31,39 |
| X-slop-10 | nit | slop | S |  | Banner comments in Core | src/camera/CameraController.cpp:1108,9742,10823,12039; src/ApertarCoreApp.cpp (4) |

## Sweep state-consistency (verified; /home/user/apertar-kb/working/merge-review/raw/sweep-state-consistency.md)

| id | sev | category | effort | deliberate | title | where |
| --- | --- | --- | --- | --- | --- | --- |
| X-state-consistency-1 | major | mismatch | M | no | Touch UI presets omit every camera setting the port added | Apertar-UI/src/ApertarControlBridge.cpp:1254-1286@cinemate-port; Apertar-Core/src/ApertarCoreApp.cpp:7844-7862@cinemate-port |
| X-state-consistency-3 | major | duplication | M | no | IMX585 mode table has one source in Core; touch UI keeps the upstream list, the WebUI a hand copy | Apertar-Core/src/camera/Imx585Modes.hpp@cinemate-port; Apertar-Core/src/web/WebControlPage.cpp:8910-8920@cinemate-port |
| X-state-consistency-2 | minor | mismatch | S | no | Touch UI and hardware buttons ignore fps_take_max during a ladder take | Apertar-UI/qml/CameraPage.qml:904-906@cinemate-port; Apertar-UI/src/ApertarControlBridge.cpp:1589-1594@cinemate-port |
| X-state-consistency-4 | minor | mismatch | S | no | Touch UI built-in FPS list lacks Core's IMX585 100/120 | Apertar-Core/src/ApertarCoreApp.cpp:1398-1406@cinemate-port; Apertar-UI/qml/CameraPage.qml:923-930@cinemate-port |
| X-state-consistency-5 | minor | duplication | S | no | Old FPS ceiling copies stay beside fps_max | Apertar-UI/qml/CameraPage.qml:904-918@cinemate-port; Apertar-Core/src/web/WebControlPage.cpp:7490-7509@cinemate-port |
| X-state-consistency-6 | minor | mismatch | S | no | WebUI preset load allow-list drops frameBufferBarEnabled | Apertar-Core/src/web/WebControlPage.cpp:19028-19112@cinemate-port; Apertar-Core/src/ApertarCoreApp.cpp:7787@cinemate-port |
| X-state-consistency-7 | minor | mismatch | S | no | settingsBody carries 14 hardware-file keys the settings event lacks | Apertar-Core/src/ApertarCoreApp.cpp:393@cinemate-port; Apertar-Core/src/ApertarCoreApp.cpp:252-269@cinemate-port |
| X-state-consistency-8 | nit | bug | S | unknown | settings event always sends iso_actual 0 | Apertar-Core/src/camera/CameraController.cpp:12856-12870@cinemate-port; Apertar-Core/src/camera/CameraController.cpp:12583-12587@cinemate-port |
| X-state-consistency-9 | nit | slop | S | unknown | Published port state fields with no reader in either UI | Apertar-Core/src/ApertarCoreApp.cpp:309-400@cinemate-port; Apertar-Core/src/ApertarCoreApp.cpp:9298-9720@cinemate-port |
| X-state-consistency-11 | nit | bug | S | no | get_state emits media_state twice | Apertar-Core/src/ApertarCoreApp.cpp:12944@cinemate-port; Apertar-Core/src/ApertarCoreApp.cpp:12961@cinemate-port |
| X-state-consistency-12 | nit | duplication | S | no | Two array serialisers print ladder_tops with different precision | Apertar-Core/src/camera/CameraController.cpp:153-161@cinemate-port; Apertar-Core/src/ApertarCoreApp.cpp:486-496@cinemate-port |
| X-state-consistency-13 | nit | mismatch | S | no | help list lacks test_input | Apertar-Core/src/ApertarCoreApp.cpp:12930@cinemate-port; Apertar-Core/src/ApertarCoreApp.cpp:12565@cinemate-port |
| X-state-consistency-14 | nit | mismatch | S | unknown | preview_tdn and media_trim persisted but not in presets | Apertar-Core/src/camera/CameraController.cpp:887,975@cinemate-port; Apertar-Core/src/camera/CameraController.cpp:11348-11368@cinemate-port |

## Sweep stock-behaviour (verified; /home/user/apertar-kb/working/merge-review/raw/sweep-stock-behaviour.md)

| id | sev | category | effort | deliberate | title | where |
| --- | --- | --- | --- | --- | --- | --- |
| X-stock-behaviour-1 | blocker | stock-behaviour-change | S | unknown | Display fallback is the HDMI rig: touch UI hidden on a stock camera with no hardware file | Apertar-UI/src/DisplayConfigBridge.cpp:11-12; Apertar-UI/src/DisplayConfigBridge.cpp:289 |
| X-stock-behaviour-3 | major | stock-behaviour-change | S | yes | FPS ceilings come from the probe alone and the IMX585 lossless 30 fps cap is gone | Apertar-Core/src/camera/FpsCeiling.hpp:14-19; Apertar-Core/src/camera/FpsCeiling.hpp:42-45 |
| X-stock-behaviour-4 | major | stock-behaviour-change | M | yes | IMX585 1.85:1 crop sizes of the cinemate-port driver forced on the stock driver | Apertar-Core/src/camera/CameraController.cpp:440-452; Apertar-Core/src/camera/CameraController.cpp:703 |
| X-stock-behaviour-5 | major | stock-behaviour-change | S | yes | Storage pre-roll runs by itself at start, insert and format | Apertar-Core/src/util/StoragePreroll.hpp:98; Apertar-Core/src/ApertarCoreApp.cpp:5069-5070 |
| X-stock-behaviour-6 | major | stock-behaviour-change | S | unknown | Preview temporal denoise off by default also strips TDN from H.264 and ProRes recordings | Apertar-Core/include/apertar/core/Types.hpp:139; Apertar-Core/src/camera/CameraController.cpp:7302-7318 |
| X-stock-behaviour-7 | major | stock-behaviour-change | S | no | Default APERTAR_DNG_DONTNEED=sync removes 1.6.0's per-file page-cache drop from Lossy DNG | Apertar-Core/src/lossydng/LossyDngEncoder.cpp:102-105; Apertar-Core/src/cdng/CdngEncoder.cpp:85-106 |
| X-stock-behaviour-8 | major | stock-behaviour-change | S | yes | Touch-UI timecode tap and Settings Mode no longer change the files' timecode | Apertar-UI/qml/CameraPage.qml:1842; Apertar-UI/qml/SettingsPage.qml:4011 |
| X-stock-behaviour-2 | minor | stock-behaviour-change | M | yes | No first-run hardware file is written any more | Apertar-UI/src/DisplayConfigBridge.cpp (ensureDefaultHardwareConfigFile removed, c9d841f); Apertar-UI/src/Ina219Bridge.cpp (writer removed) |
| X-stock-behaviour-9 | minor | stock-behaviour-change | S | yes | Lossless cDNG ISO cap raised to 1600 on every sensor | Apertar-Core/src/camera/CameraController.cpp:3100; Apertar-Core/src/camera/CameraController.cpp:3146-3170 |
| X-stock-behaviour-10 | minor | stock-behaviour-change | M | yes | Auto ISO kept in IMX585 lossless and offered in every UI; Core undoes it on other sensors | Apertar-Core/src/camera/CameraController.cpp:3152-3156; Apertar-Core/src/ApertarCoreApp.cpp:10485 |
| X-stock-behaviour-11 | nit | stock-behaviour-change | S | unknown | Media trim switch shows on when the root helper is not installed | Apertar-Core/include/apertar/core/Types.hpp:140; Apertar-Core/src/ApertarCoreApp.cpp:11505-11514 |
| X-stock-behaviour-12 | nit | stock-behaviour-change | S | yes | HDMI monitor timecode turns red during takes by default | Apertar-UI/src/SettingsBridge.cpp:370; Apertar-UI/qml/ExternalMonitorWindow.qml:1208 |
| X-stock-behaviour-13 | nit | stock-behaviour-change | S | yes | Audio meter red outline on by default | Apertar-UI/src/SettingsBridge.cpp:371 |
