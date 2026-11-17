# Fix list: cinemate-port into Apertar main

The one list for Patrik. 253 fix items from seven domain editors, 240 after merging twins across domains. Detail,
evidence and rework steps stay in the domain files named in the last column. Yardstick: `apertar-conventions.md`.
Refs: Core `cinemate-port` `01f170c`, UI `7ea9afc`; improvement branches Core `work/improve` (`/home/user/wt/core-work`,
14 commits), UI `work/improve` (3 commits), imx283 `36d484b`.

## Verdict

1. **Not ready to merge.** 235 of 240 items are open: 5 blockers, 66 major, 142 minor, 22 nit.
2. Blockers: Boot Config writes LAN free text into config.txt as root (HW-1); the Config page refuses saves 1.6.0 took (HW-2); IMX585 crops renamed so Core needs the port driver (CAM-1); CameraController reads apertar-hardware.conf (REC-1); the Core history cannot be reviewed (TXT-1).
3. Milestone 1 (Apertar design) holds 149 open items, 42 of them major: a second dispatcher and reply builder, process-wide statics, a pre-roll take outside handleCommand, root helpers, a second tuning file, a second WebUI store and widget layer.
4. 31 open items wait on an owner answer (`owner-decisions.md`); the first five decisions hold back about 55 items.
5. Nothing was run on a Pi for this review. Every item with a "Needs the Pi" line must pass there before the PR.

## Done on the improvement branches

| Commit | What | Closes |
| --- | --- | --- |
| Core `04fe197` | GPIO chip is a Controls setting again, checks per chip | owner request 16 (fix-list-hardware.md) |
| Core `7dc6f7a`, UI `6a59d83` | Display defaults 720x720 square again (template and UI fallback) | UI-bridges-F1, App-2-F1 (blocker) |
| UI `2d9cf94`, Core `ff4c7c5` | Audio meter outline off by default, both halves | X-stock-behaviour-13, APP-19 |
| UI `ac1fc28` | HDMI timecode white until red timecode is set | X-stock-behaviour-12 |
| Core `0977dd6` | Storage pre-roll off by default | APP-2 (blocker) |
| Core `e4246ee` | get_state sends media_state once | APP-22 |
| Core `615b48c` | Lossy DNG drops each file's pages after the write again | X-stock-behaviour-7 |
| Core `b923c06`, `3650027`, `0d13a6f` | Preview TDN on by default as in 1.6.0; the switch leaves H.264, ProRes alone; photo follows it | CAM-3, APP-6 |
| Core `d1dcdee` | test_input refuses script actions | APP-8 (HW-3 stays open) |
| imx283 `36d484b` | Per-crop VMAX floors off by default | CAM-10 step 1 |
| Core `9bd7610` `93cab28` `a36c52f` `56e135c` | 12-bit Clear HDR fixes from the `hdr12/` investigation | HDR-D1, D2, D3, H1 interim |

In lanes, not yet on `work/improve`: Core `lane/core1` (REC-5, REC-6, REC-7), `lane/core3` (HW-2), `lane/hdr` (part of HW-13);
UI `lane/ui1` (UI-6, UI-7). They show as "open; lane ..." below.

## Twins merged across domains

One row is kept; the other id points at it. Fix both halves in one commit.

| Kept | Also filed as |
| --- | --- |
| HW-1 Boot Config free text as root | APP-1, WEB-1 (page half) |
| HW-4 Boot Config HTTP door | APP-3 |
| HW-5 config.txt write routes | APP-4 |
| APP-7 pre-lock dispatcher | HW-21 |
| APP-11 storage switch home | HW-36 |
| APP-14 second tuning file | REC-11 |
| APP-16 first-run hardware file | HW-9, UI-4 |
| REC-1 CC reads the hardware file | CAM-15; replaces APP-10 step 1 (App parses [storage], CC gets an option struct, rule CAM-19) |
| CAM-2, CAM-14 lossless and FPS ceilings | REC-4 |
| CAM-3 preview TDN | APP-6 |
| HW-37 fan mode through Core | UI-27 |

Same problem, separate code, one owner answer: UI-8 / WEB-8 (drag composer), UI-14 / WEB-14 (ISO Auto offered),
UI-1 / WEB-13 / APP-45 (timecode), UI-3 / APP-47 / WEB-15 (presets). Twin text items (APP-17, CAM-11, CAM-12, REC-12,
HW-38, UI-20, WEB-33, WEB-34) share one rule and gate, TXT-7.

Severity is the domain editor's. Conventions ids are written 'rule CAM-n' where they could be read as an item id. "owner" in State: waits on `owner-decisions.md`. Rows: most severe first, then domain.

## Milestone 1: compatibility with the original Apertar design

Kinds mismatch, removed, stock, protocol, security, duplication, new-ground. 153 item rows, 149 open, plus the GPIO chip row (owner request 16, done).

| Id | Kind | Sev | Eff | Title | State | Read more |
| --- | --- | --- | --- | --- | --- | --- |
| APP-2 | stock | blocker | S | Storage pre-roll runs by itself: a raw take at every boot, card insert and format | done 0977dd6 | fix-list-core-app.md |
| HW-1 | security | blocker | M | Boot Config writes free text into config.txt as root for any LAN client (also APP-1, page half WEB-1) | open, owner | fix-list-hardware.md |
| HW-2 | removed | blocker | S | Config page text save is refused on validator errors the readers accept | open; lane/core3 322117b | fix-list-hardware.md |
| CAM-1 | removed | blocker | M | IMX585 1.85:1 crops renamed in the driver and rewritten by Core; colour crop sizes lost the auto-config fallback | open, owner | fix-list-camera.md |
| REC-1 | mismatch | blocker | L | CameraController reads apertar-hardware.conf: [storage] at every take, [camera] Clear HDR ISO caps (also CAM-15; overrides APP-10 step 1) | open, owner | fix-list-recording.md |
| GPIO-chip | removed | major | S | GPIO chip setting back on the Controls page, checks per chip (owner request 16, no item id) | done 04fe197 | fix-list-hardware.md |
| APP-5 | mismatch | major | M | errorReplyBody: a third reply builder with machine error codes and extra members | open | fix-list-core-app.md |
| APP-7 | mismatch | major | M | A second dispatcher answers six commands before the command lock (also HW-21) | open | fix-list-core-app.md |
| APP-8 | security | major | S | test_input lets a LAN client run any readable file with bash, without a button press | done d1dcdee | fix-list-core-app.md |
| APP-10 | mismatch | major | L | [storage] parsed by App and by CameraController; live state shared through header singletons and global std::function hooks (step 1 replaced by REC-1) | open | fix-list-core-app.md |
| APP-11 | mismatch | major | M | Storage switches inline the hardware-store edit three times; one family of recording switches spread over two stores (also HW-36) | open, owner | fix-list-core-app.md |
| APP-12 | mismatch | major | L | Storage pre-roll worker starts and finishes a camera take outside handleCommand | open | fix-list-core-app.md |
| APP-13 | mismatch | major | M | Three root helpers as /bin/sh scripts with sudoers and tmpfiles inside Core; trim switch says on without the helper | open | fix-list-core-app.md |
| APP-14 | duplication | major | M | A second bench-tuning mechanism (INI, /run override, 487-line apertar-tune, tmpfiles) beside upstream's .apertar-tuning (also REC-11) | open, owner | fix-list-core-app.md |
| APP-16 | removed | major | M | No first-run hardware file, and the only default lacks chip=, input tuning and [mpu6050] (also HW-9, UI-4) | open, owner | fix-list-core-app.md |
| HW-3 | security | major | S | Scripts: the browser cannot set [run_script] paths, yet can run mapped scripts without a press (test_input half done in APP-8) | open, owner | fix-list-hardware.md |
| HW-4 | mismatch | major | M | Boot Config has its own write route with cmd splicing, a revision header, 403/409 and an Origin rule (also APP-3) | open | fix-list-hardware.md |
| HW-5 | mismatch | major | S | config.txt root write has three routes, a stdin root helper and a sudoers file in Core (also APP-4: helper breaks fan mode) | open | fix-list-hardware.md |
| HW-7 | removed | major | S | A Standby wake press still fires click and Hold gestures | open | fix-list-hardware.md |
| HW-8 | removed | major | S | A button that reads pressed at start is inverted for the session, overriding active_low | open, owner | fix-list-hardware.md |
| HW-10 | new-ground | major | M | hwconf is a second table-driven model of every reader in one 1141-line header, and it has drifted | open | fix-list-hardware.md |
| HW-11 | new-ground | major | L | Boot Config engine: 1355-line header-only framework that writes wire JSON | open | fix-list-hardware.md |
| HW-12 | mismatch | major | M | ActionCatalog replaces the drivers' flat alias chains with a CSV table and a second action parser | open | fix-list-hardware.md |
| HW-13 | mismatch | major | M | Controls page keeps its own store (controlsState) and its own fetch wrapper (controlsCall) | open; lane/hdr 0ddf007 (part) | fix-list-hardware.md |
| HW-14 | mismatch | major | S | Remote controls card on the main page with hold-to-repeat and a load-time retry loop | open, owner | fix-list-hardware.md |
| HW-15 | new-ground | major | L | 2100-line structured hardware editor: chip box, pin-claim cascade, review re-derivation, one-entry dropdown | open, owner | fix-list-hardware.md |
| CAM-2 | stock | major | S | FPS ceilings come from the probe alone and the IMX585 lossless 30 fps cap is lifted by default (also REC-4) | open, owner | fix-list-camera.md |
| CAM-3 | stock | major | S | Preview temporal denoise off by default also strips TDN from H.264, ProRes and processed stills (also APP-6) | done b923c06 3650027 0d13a6f | fix-list-camera.md |
| CAM-4 | mismatch | major | M | TDN strip: a 451-line header with its own JSON parser, atomic writer, sidecar and cache folder | open | fix-list-camera.md |
| CAM-5 | mismatch | major | M | DNG copy worker returns requests through a set-once setRequestRelease(libcamera::Request*) callback | open | fix-list-camera.md |
| CAM-6 | mismatch | major | M | Storage pre-roll writes fps after the sanitiser and re-pins FrameDurationLimits on every request | open, owner | fix-list-camera.md |
| CAM-7 | mismatch | major | M | Raw buffer and request count: kActiveRequestCount gone, a process-global media root, three evaluations per configure, no board cap | open, owner | fix-list-camera.md |
| CAM-8 | mismatch | major | M | Mode ladder persists in its own mode_ladder.conf, with a copied path function | open, owner | fix-list-camera.md |
| REC-2 | mismatch | major | L | Safety stop, flush abort, buffer gauge, buffer setting and media snapshot are process-wide statics and std::function registries, with two polling threads | open | fix-list-recording.md |
| REC-3 | stock | major | S | Media trim on by default: deleted takes become unrecoverable once trim works on a stock image | open | fix-list-recording.md |
| REC-10 | mismatch | major | M | Storage pre-roll is a hidden second take kind; setTuningFile and enterStandby not excluded; unlocked public getter | open | fix-list-recording.md |
| WEB-2 | mismatch | major | M | Playback renames the original developer's media feature: pb*/pbv* functions, nested state.pb, .pb-* CSS | open | fix-list-webui.md |
| WEB-3 | mismatch | major | M | Playback brings a second widget layer: modal scrim, History API, own buttons, menu, chip, cyan selection | open, owner | fix-list-webui.md |
| WEB-4 | mismatch | major | M | Second 4 Hz poll, second store frameBufferBar, recording pill written outside renderSnapshot | open | fix-list-webui.md |
| WEB-5 | mismatch | major | M | Boot Config card internals: own store and installer, checkbox gate, own diff and select builders | open | fix-list-webui.md |
| WEB-6 | mismatch | major | M | IMX585 resolution pills read the Mode Ladder reply; mode tables hand-copied in a private string format | open | fix-list-webui.md |
| WEB-7 | new-ground | major | L | Mode Ladder editor re-implements Core's ladder rules in JS, and they already differ | open, owner | fix-list-webui.md |
| WEB-8 | new-ground | major | M | Clip-name composer: about 570 lines of drag-and-drop and long-press for one template string | open, owner | fix-list-webui.md |
| WEB-9 | mismatch | major | S | White dropdowns scoped to the Controls panel by panel and id, dark again for some pin selects | open, owner | fix-list-webui.md |
| UI-1 | stock | major | M | Timecode tap and Settings "Mode" no longer set the files' timecode; upstream names gone | open, owner | fix-list-touch-ui.md |
| UI-3 | removed | major | M | Touch-UI presets omit every camera setting the port added | open | fix-list-touch-ui.md |
| UI-5 | mismatch | major | M | Touch-UI IMX585 resolution and FPS lists lag Core's tables | open | fix-list-touch-ui.md |
| UI-6 | mismatch | major | S | New command invokables return void, send on/off and auto/off, apply a reply twice | open; UI lane/ui1 98d7a1c | fix-list-touch-ui.md |
| UI-7 | mismatch | major | M | ActionTiles with flipping accent tone used as radio buttons; hand-sized sub-labels | open; UI lane/ui1 3b2c98b 797180e | fix-list-touch-ui.md |
| UI-8 | new-ground | major | M | ClipNameCard: drag-and-drop composer with a hand-placed ghost, untested on touch | open, owner | fix-list-touch-ui.md |
| APP-19 | stock | minor | S | Core treats a missing audioRecordedOutlineEnabled as on (the UI half was fixed in U2) | done ff4c7c5 | fix-list-core-app.md |
| APP-20 | removed | minor | S | FPS and ISO step lists now end on the mode's odd ceiling | open | fix-list-core-app.md |
| APP-21 | mismatch | minor | S | settingsBody carries 14 [storage] members the settings event lacks | open | fix-list-core-app.md |
| APP-23 | removed | minor | S | Record gate refuses a --media folder that is not a mount point; the opt-out is an undocumented env variable | open | fix-list-core-app.md |
| APP-24 | removed | minor | S | Downloads refused in Standby and without media, not only during a take | open | fix-list-core-app.md |
| APP-25 | removed | minor | S | /api/media hides folders during a hold; cDNG size_bytes and file_count change meaning | open | fix-list-core-app.md |
| APP-27 | protocol | minor | S | /api/buffer 'recording' means something else than /api/state 'recording' | open | fix-list-core-app.md |
| APP-28 | protocol | minor | S | set_storage_preroll takes value=on/off and the action is the bare noun storage_preroll | open | fix-list-core-app.md |
| APP-30 | mismatch | minor | M | Worker lifecycle: three start styles, stopMediaWatcher stops five more threads, five idle predicates, three clocks, record_start waits 4.5 s under the lock | open | fix-list-core-app.md |
| APP-31 | mismatch | minor | M | Buffer level pushed by an App polling thread; two identical events in one turn | open | fix-list-core-app.md |
| APP-32 | mismatch | minor | S | Controls worker polls the hardware file every 2 s | open | fix-list-core-app.md |
| APP-35 | duplication | minor | S | [cfexpress_hat]: two parsers, defaults in two places, C++ reader off where upstream's is on, status row on boards without the HAT | open | fix-list-core-app.md |
| APP-36 | new-ground | minor | S | clipInfoJson nests meta/extra objects that repeat top-level values | open | fix-list-core-app.md |
| APP-37 | mismatch | minor | S | set_value_steps: range table inside the branch, repeated in the snapshot reader; nested ui reply | open | fix-list-core-app.md |
| APP-38 | duplication | minor | S | Clip name template parsed in App and again in CameraController; dead out-parameter | open | fix-list-core-app.md |
| APP-41 | mismatch | minor | S | ApertarCoreApp.hpp: methods among members, split member groups, 37 comment lines | open | fix-list-core-app.md |
| APP-42 | new-ground | minor | S | Host tests in tools/ outside CMake, with build lines that disagree | open | fix-list-core-app.md |
| APP-43 | new-ground | minor | S | HardwareConfigStore replaces upstream's one save function | open | fix-list-core-app.md |
| APP-44 | protocol | minor | S | Socket request line raised from 64 KiB to 1 MiB for whole-file set_controls | open | fix-list-core-app.md |
| APP-45 | new-ground | minor | S | set_timecode_mode target= sets screen and file timecode apart | open | fix-list-core-app.md |
| HW-16 | removed | minor | S | set_controls refuses keys the readers use, hides others, and accepts hold_ms/double_ms nobody reads | open | fix-list-hardware.md |
| HW-19 | protocol | minor | M | Whole-file text through set_controls skips the upstream empty/size/NUL checks | open | fix-list-hardware.md |
| HW-20 | protocol | minor | M | Hardware-file replies carry machine codes, issue arrays, a merge-review path with no client and an Origin rule | open | fix-list-hardware.md |
| HW-22 | duplication | minor | S | Two config.txt readers with different section filters; the Controls one reads as a Pi 5 | open | fix-list-hardware.md |
| HW-30 | mismatch | minor | S | JSON built in hardware headers with string + and its own escaper; defaults repeated | open | fix-list-hardware.md |
| HW-31 | new-ground | minor | S | GPIO edge-event loop: keep, but stop by eventfd, drain fully, and use member functions | open | fix-list-hardware.md |
| HW-32 | new-ground | minor | S | Switch positions apply toggle actions at start and on every Controls save | open | fix-list-hardware.md |
| HW-33 | new-ground | minor | M | Remote-only buttons stored as remote<N> in [gpio_buttons] | open | fix-list-hardware.md |
| HW-35 | mismatch | minor | S | Listen is a second 300 ms network poll loop | open | fix-list-hardware.md |
| HW-37 | removed | minor | S | Touch-UI fan mode now needs Core (also UI-27) | open, owner | fix-list-hardware.md |
| HW-39 | new-ground | minor | S | Host tests for the Boot Config engine and helper | open | fix-list-hardware.md |
| HW-40 | mismatch | minor | S | Controls page idioms: two feedback channels, duplicated helpers, inline style, loader naming | open | fix-list-hardware.md |
| CAM-14 | stock | minor | S | Lossless ISO cap raised to 1600 on every sensor; auto ISO kept in IMX585 lossless with any tuning (also REC-4) | open | fix-list-camera.md |
| CAM-16 | mismatch | minor | S | Ladder and clip-name methods return errors and data through out-parameters | open | fix-list-camera.md |
| CAM-17 | new-ground | minor | S | ladder_text: Core composes a UTF-8 display line; ladderCount repeats ladder_tops | open | fix-list-camera.md |
| CAM-20 | mismatch | minor | S | Six new booleans written as true/false in camera_settings.conf | open | fix-list-camera.md |
| CAM-21 | mismatch | minor | S | Speed ramp writes a journal line per set_fps and per transition; the refusal names a socket command | open | fix-list-camera.md |
| CAM-22 | duplication | minor | S | Core mirrors the driver mode tables by hand; rows the driver refuses vanish without a log line; provenance is a branch name | open | fix-list-camera.md |
| CAM-25 | new-ground | minor | M | Speed-ramp audio stretch: undeclared rubberband started as a detached double fork of sh -c, default on | open, owner | fix-list-camera.md |
| CAM-26 | mismatch | minor | S | set_resolution refuses an IMX585 size the current class lacks; upstream sanitises silently | open, owner | fix-list-camera.md |
| CAM-27 | new-ground | minor | S | imx585 driver: 960/1024-wide families hidden by Core, and a Clear HDR test module parameter with a CineMate test kit | open, owner | fix-list-camera.md |
| CAM-28 | new-ground | minor | S | Frame-rate phase lock: keep the servo, cut the socket telemetry and fix its comments | open | fix-list-camera.md |
| CAM-29 | new-ground | minor | S | Deliberate departures from stated upstream intents: tell the original developer | open | fix-list-camera.md |
| CAM-30 | new-ground | minor | S | Camera host tests: four tests in three styles with build lines in comments | open | fix-list-camera.md |
| CAM-31 | new-ground | minor | S | Mode-ladder override: one flag set by setClearHdr and cleared by hand in six setters; lost at restart | open | fix-list-camera.md |
| CAM-32 | duplication | minor | S | IMX585 and IMX283 exact-mode checks repeat the bit-depth and PISP_COMP1 logic | open | fix-list-camera.md |
| CAM-33 | new-ground | minor | S | Both drivers audit their static tables at every probe; imx585 warns about a known duplicate on every boot | open | fix-list-camera.md |
| CAM-39 | new-ground | minor | S | imx283 IMX283_ASPECT_MODE takes 15 positional arguments; parent timing repeated in 51 rows | open | fix-list-camera.md |
| CAM-41 | mismatch | minor | S | Rung::compression is a free string mixing record format and compression | open | fix-list-camera.md |
| REC-13 | removed | minor | S | Per-filesystem writer table changes upstream writer, queue and raw buffer defaults on vfat, NTFS and other | open | fix-list-recording.md |
| REC-14 | removed | minor | S | Raw copy pool kept between takes (about 100 MB at 16-bit 4K) | open | fix-list-recording.md |
| REC-17 | removed | minor | S | The 1 GiB free-space floor also refuses a single still | open | fix-list-recording.md |
| REC-18 | mismatch | minor | S | Playback routes hand-write JSON error bodies; hold rule built twice and parsed back from a string | open | fix-list-recording.md |
| REC-19 | mismatch | minor | S | Sensor probe tells IMX585 by a Model substring; second sysfs subdev walk | open | fix-list-recording.md |
| REC-20 | mismatch | minor | S | Ladder refusals are constants that name a wrong menu path; ladder compression handled as strings | open | fix-list-recording.md |
| REC-22 | new-ground | minor | S | Per-file writeback, 1 s fsync sweep and syncfs at stop: keep, but fix the shared cv and the DONTNEED fallback | open | fix-list-recording.md |
| REC-27 | duplication | minor | S | Playback text helpers and clocks duplicate App's | open | fix-list-recording.md |
| REC-28 | duplication | minor | S | Frame-number rule in two C++ copies | open | fix-list-recording.md |
| REC-30 | new-ground | minor | S | Clip-name template: constant tokens, src/util placement, second sensorName | open | fix-list-recording.md |
| REC-32 | new-ground | minor | S | Safety stop ends a take; record during the flush discards queued frames | open | fix-list-recording.md |
| REC-40 | new-ground | minor | S | GET /api/buffer polled at 4 Hz beside /api/state | open | fix-list-recording.md |
| WEB-10 | removed | minor | S | Media list lost size, fps and frame count, per-row Download/Delete and Clear selection | open | fix-list-webui.md |
| WEB-11 | removed | minor | S | Record button greyed without media; Core's reason never shown; "has media" decided by two fields | open | fix-list-webui.md |
| WEB-12 | removed | minor | S | ISO and WB badges no longer say Auto | open, owner | fix-list-webui.md |
| WEB-13 | removed | minor | S | Timecode: upstream labels renamed, the favourite split in two, the card lost its value pill | open, owner | fix-list-webui.md |
| WEB-14 | stock | minor | S | ISO Auto offered by the page's own rule wherever Clear HDR is off | open | fix-list-webui.md |
| WEB-16 | mismatch | minor | S | APERTAR_* names and *_env greying in operator text; pre-roll switch not shaped like an upstream toggle | open | fix-list-webui.md |
| WEB-17 | protocol | minor | S | Page parses Core's display text: write speed, buffer note; Log reason hard-coded for IMX585 | open | fix-list-webui.md |
| WEB-18 | protocol | minor | S | Buffer and pre-roll settings published twice by Core; renderSnapshot copies system.* to the top level | open | fix-list-webui.md |
| WEB-19 | mismatch | minor | S | Mode Ladder lock wired into the two generic pill builders; two lock mechanisms | open | fix-list-webui.md |
| WEB-20 | mismatch | minor | S | Inline SVG icons (13 places) where the page uses /icons PNGs | open | fix-list-webui.md |
| WEB-21 | mismatch | minor | S | Hiding by the hidden attribute with [hidden] patches; attribute and id selectors in CSS | open | fix-list-webui.md |
| WEB-22 | mismatch | minor | S | Cards filed under the wrong topic: indicators in Live preview, a Performance card in System, Value Lists in Controls | open | fix-list-webui.md |
| WEB-23 | mismatch | minor | S | On/Off switches from new classes (.switch-field, .ladder-pair); a label wraps the Log pills | open | fix-list-webui.md |
| WEB-24 | mismatch | minor | S | Config editor Check goes through set_controls with a fake "h" revision; Save diff step kept | open | fix-list-webui.md |
| WEB-25 | new-ground | minor | M | Settings search: MutationObserver and elements inserted at runtime | open | fix-list-webui.md |
| WEB-26 | duplication | minor | M | Parallel CSS vocabulary: ladder buttons and tile re-create upstream ones; four chip classes | open | fix-list-webui.md |
| WEB-27 | mismatch | minor | S | Stylesheet order and breakpoints: 741 lines inside the pill-button group, media queries at 1119/719/419 | open | fix-list-webui.md |
| WEB-32 | duplication | minor | S | FPS caps re-applied in JS on top of Core's fps_max; an empty if-branch | open | fix-list-webui.md |
| UI-11 | mismatch | minor | M | Second state path: controls/media/buffer event branches and a key-name setter | open | fix-list-touch-ui.md |
| UI-12 | mismatch | minor | M | Full get_state poll every second while auto ISO or auto WB is on | open | fix-list-touch-ui.md |
| UI-13 | mismatch | minor | S | Storage pre-roll inside the Media Speed card; presence latches hide pre-roll and Clip Names | open | fix-list-touch-ui.md |
| UI-14 | stock | minor | S | ISO Auto offered in lossless modes where Core turns it off | open | fix-list-touch-ui.md |
| UI-18 | mismatch | minor | S | New Settings items skip icon and favourite registration | open | fix-list-touch-ui.md |
| UI-21 | duplication | minor | S | Buffer bar written twice (StatusChip and HDMI pill) | open | fix-list-touch-ui.md |
| UI-22 | duplication | minor | S | HDMI window copies of ISO cap, raw-format test and fps formatting drift from CameraPage | open | fix-list-touch-ui.md |
| TXT-9 | new-ground | minor | S | New ground arrives as ordinary feature commits with no note for the original developer | open | fix-list-text-history.md |
| APP-46 | mismatch | nit | S | Serialiser nits: leading-comma fragments, two ladder_tops precisions, help lacks test_input, start logs every success | open | fix-list-core-app.md |
| APP-47 | mismatch | nit | S | preview_tdn and media_trim are persisted but not preset fields | open, owner | fix-list-core-app.md |
| APP-48 | new-ground | nit | S | set_iso_auto gains enabled=false (lock at the measured gain) | open | fix-list-core-app.md |
| APP-49 | mismatch | nit | S | Second include block after the JPEG #if; util/ headers ahead of public headers | open | fix-list-core-app.md |
| HW-41 | duplication | nit | S | gpioChipScore half-shared | open | fix-list-hardware.md |
| HW-42 | mismatch | nit | S | Listen wiring: seen callback by setter, gesture suffix arrays in three copies | open | fix-list-hardware.md |
| CAM-42 | new-ground | nit | S | Read-only Mode geometry controls in both drivers have no Apertar consumer | open | fix-list-camera.md |
| CAM-43 | removed | nit | S | imx283 base sizes 2784x1548 (MODE_2A) and 5568x3094 (MODE_1A) replaced | open | fix-list-camera.md |
| CAM-45 | mismatch | nit | S | Small CameraController nits: include order, public data members, namespace spelling, lone assert, repeated mono expression, duplicated row loop | open | fix-list-camera.md |
| REC-29 | duplication | nit | S | Second /proc/mounts parser beside upstream's | open | fix-list-recording.md |
| REC-33 | new-ground | nit | S | Dropped-frame count in state and event; unused fault field | open | fix-list-recording.md |
| REC-34 | mismatch | nit | S | Extra settings event helper for cdng_log_applied | open | fix-list-recording.md |
| REC-36 | new-ground | nit | S | Audio drift fit, 10 ms ALSA period, MLV black level differ from 1.6.0 | open | fix-list-recording.md |
| REC-37 | new-ground | nit | S | Host tests and desk tools of this domain | open | fix-list-recording.md |
| REC-38 | mismatch | nit | S | Placement and namespace names (BufferBudget, StoragePreroll, UI clipframes) | open | fix-list-recording.md |
| WEB-37 | new-ground | nit | S | WebUI-only panels (Modes, Controls) and three editors of apertar-hardware.conf | open | fix-list-webui.md |
| WEB-38 | duplication | nit | S | Small duplications: flicker-free maths, ladder toast, raw createElement, typeof number checks | open | fix-list-webui.md |

## Milestone 2: bugs and Raspberry Pi model compatibility

Kinds bug, board. 50 rows, 49 open. REC-5, REC-6, REC-7 are fixed in `lane/core1`, not yet integrated.

| Id | Kind | Sev | Eff | Title | State | Read more |
| --- | --- | --- | --- | --- | --- | --- |
| HW-6 | bug | major | S | Boot Config ignores include camera-selection.txt and adds a second sensor overlay | open | fix-list-hardware.md |
| REC-5 | bug | major | S | Playback leaks one TurboJPEG handle per decoded frame | open; lane/core1 b3fd1e6 | fix-list-recording.md |
| REC-6 | bug | major | S | Clip-name example stats up to 9999 paths on the media under mutex_ at every settings read and event | open; lane/core1 c89dae5 | fix-list-recording.md |
| REC-7 | bug | major | S | Write queue stop: copy workers joined without a bound; detached writers outlive the queue | open; lane/core1 e8b065e | fix-list-recording.md |
| REC-8 | bug | major | S | A slow but live medium is judged Removed after 5 s and the clip is not finalised | open | fix-list-recording.md |
| REC-9 | bug | major | S | Ending a trim signals sudo, fstrim runs on into the take; commands wait up to 3.5 s under commandMutex_ | open | fix-list-recording.md |
| UI-2 | bug | major | S | Safety-stop flush shows READY while Core still writes the take | open | fix-list-touch-ui.md |
| APP-22 | bug | minor | S | get_state writes media_state twice from two snapshots | done e4246ee | fix-list-core-app.md |
| APP-26 | bug | minor | S | audio_url is JSON-escaped, not URL-encoded | open | fix-list-core-app.md |
| APP-33 | bug | minor | S | Delete gate is not atomic with record_start | open | fix-list-core-app.md |
| APP-39 | bug | minor | S | IMX585 Clear HDR fallback fps cap disagrees with Core's table | open | fix-list-core-app.md |
| APP-40 | board | minor | S | Hardware-file checker reads config.txt for [all] and [pi5] only | open | fix-list-core-app.md |
| HW-17 | bug | minor | S | A key edit on a duplicated section writes the copy the readers ignore | open | fix-list-hardware.md |
| HW-18 | bug | minor | S | An IMU write on a /boot-only rig creates a partial /home/pi file that hides the /boot file | open | fix-list-hardware.md |
| HW-23 | bug | minor | S | Sensor list of the Boot Config card lacks IMX283 | open | fix-list-hardware.md |
| HW-24 | board | minor | S | Boot Config board model: unknown read as Pi 5, Zero 2 W as pi3, link cap only for pi4 | open | fix-list-hardware.md |
| HW-25 | board | minor | S | Core's free-pin list and output line limit stay fixed to the 40-pin header | open | fix-list-hardware.md |
| HW-26 | board | minor | S | Any DPI line greys GPIO 0-27, in the page and in Core's validator | open | fix-list-hardware.md |
| HW-27 | bug | minor | S | Saving one Controls card silently drops the other card's unsaved edits | open | fix-list-hardware.md |
| HW-28 | bug | minor | S | Tally card: switching off erases the pin | open | fix-list-hardware.md |
| HW-29 | bug | minor | S | Pins recovered by regex from Core's display text | open | fix-list-hardware.md |
| HW-34 | bug | minor | S | Status probes and scan_i2c read chips the UI process polls | open | fix-list-hardware.md |
| CAM-13 | bug | minor | S | Speed ramp: a mid-ramp FPS can be saved as the operator's FPS; the keep-exposure shutter leaks into another format's profile | open | fix-list-camera.md |
| CAM-19 | board | minor | S | Ladder editor ignores recording_capabilities: every compression reads usable on a board without raw compression | open | fix-list-camera.md |
| CAM-24 | bug | minor | S | imx283: function-local statics shared by all sensor instances | open | fix-list-camera.md |
| CAM-35 | bug | minor | S | imx585 1440x1080 frames differently at 12-bit (1x1 window) and 10-bit (2x2 of 2880) | open | fix-list-camera.md |
| CAM-36 | bug | minor | S | imx585 12-bit Clear HDR offered on 27 1x1 crops without a recorded take | open | fix-list-camera.md |
| CAM-37 | bug | minor | S | imx283 MODE_1C window .top = 852 is centred on the old active area; .left 924 OB unchecked on raw | open | fix-list-camera.md |
| CAM-40 | bug | minor | S | {res} clip-name token labels by width only | open | fix-list-camera.md |
| REC-15 | bug | minor | S | UI automounter unmounts and PCIe-removes the drive on one HAT read | open | fix-list-recording.md |
| REC-16 | bug | minor | S | Audio writer queue unbounded; after a write failure the WAV is built from bytes never written | open | fix-list-recording.md |
| REC-23 | board | minor | M | Raw write path changed for every board and run on one CM5 | open | fix-list-recording.md |
| REC-24 | bug | minor | S | Clip viewer refuses the 8-bit DNGs Core writes | open | fix-list-recording.md |
| REC-25 | bug | minor | S | FORMAT row guesses the lossy ratio from the clip name | open | fix-list-recording.md |
| REC-26 | board | minor | S | Playback memory: JPEG caches never trimmed, unused slot buffer, wrong memory comment | open | fix-list-recording.md |
| REC-31 | bug | minor | S | Early safety-stop recording event carries a stale lastError_ | open | fix-list-recording.md |
| WEB-15 | bug | minor | S | Loading a preset from the WebUI library drops frameBufferBarEnabled | open | fix-list-webui.md |
| WEB-28 | bug | minor | S | Clip viewer: stale badges on non-cDNG items, blank after a hold, freeze on a short WAV | open | fix-list-webui.md |
| WEB-29 | bug | minor | M | Crop picture and ladder names assume the IMX585 3840x2160 readout on every sensor | open | fix-list-webui.md |
| WEB-30 | bug | minor | S | Exact shutter angle leaves no pill active (60 fps at 22.5 deg) | open | fix-list-webui.md |
| WEB-31 | bug | minor | S | Boot Config reboot wait polls /api/buffer and misreports a slow shutdown | open | fix-list-webui.md |
| WEB-36 | board | minor | S | Player pacing tuned on a Pi 5 only | open | fix-list-webui.md |
| UI-10 | bug | minor | S | Clip-name card loses an edit at record start and drops unknown tokens | open | fix-list-touch-ui.md |
| UI-17 | bug | minor | S | ControlsWarning.qml missing from qml.qrc (non-AOT builds) | open | fix-list-touch-ui.md |
| UI-19 | bug | minor | S | Settings text states Core settings as fixed values | open | fix-list-touch-ui.md |
| UI-23 | bug | minor | S | Touch picker and FPS buttons ignore fps_take_max during a ladder take | open | fix-list-touch-ui.md |
| UI-24 | bug | minor | S | Core media override never cleared when Core goes away | open | fix-list-touch-ui.md |
| UI-25 | bug | minor | S | shutterSetByCamera reads m_recording before the recording state is set | open | fix-list-touch-ui.md |
| HW-43 | bug | nit | S | Store: `by` written raw into hardware-state.conf; 100 ms sleep under the store mutex | open | fix-list-hardware.md |
| REC-35 | bug | nit | S | wavSampleRate rejects RF64 | open | fix-list-recording.md |

## Milestone 3: text (comments, UI strings, README, knobs to drop)

Kinds slop, docs, knob. 29 rows, all open. TXT-7 is the shared rule and the gate (`check_text.sh`).

| Id | Kind | Sev | Eff | Title | State | Read more |
| --- | --- | --- | --- | --- | --- | --- |
| APP-9 | knob | major | M | Environment knobs in the command plane override saved settings and surface as *_env state | open | fix-list-core-app.md |
| APP-15 | knob | major | S | Real-time scheduling in the start script; LimitRTPRIO=80 under upstream's 'non-real-time' comment | open | fix-list-core-app.md |
| APP-17 | slop | major | M | Ticket numbers, KB paths, Cinemate hashes, banners and narration in App, its header, scripts and config | open | fix-list-core-app.md |
| APP-18 | docs | major | S | README grows into a lab manual: env knob table, install recipes, socket field lists, measurements | open | fix-list-core-app.md |
| CAM-9 | knob | major | S | Camera bench knobs: restore switches, never-set gains and an RT priority knob measured with no effect | open | fix-list-camera.md |
| CAM-10 | knob | major | S | IMX283 driver turns on unmeasured per-crop VMAX floors by default; Core caps them away again | open; driver half done imx283 36d484b | fix-list-camera.md |
| CAM-11 | slop | major | M | Ticket numbers, Cinemate history, KB paths, dates and banners in Core camera comments and in a written file | open | fix-list-camera.md |
| CAM-12 | slop | major | M | Driver comments and docs: work-package history, 'Experimental' on shipping modes, absent files, stale lines, Cinemate sections | open | fix-list-camera.md |
| REC-12 | slop | major | M | Ticket ids, dates, clip ids, KB paths, Cinemate hashes and the 'CineMate Log' brand in comments and log lines | open | fix-list-recording.md |
| TXT-7 | slop | major | L | One comment rule and one gate for all four repos; density 3x to 26x upstream | open | fix-list-text-history.md |
| TXT-8 | docs | major | S | Driver docs: stale 7-mode README section, no link to APERTAR.md, three branch names, image pulls the old branch | open, owner | fix-list-text-history.md |
| APP-29 | slop | minor | S | Eject-intent flag file has no reader | open | fix-list-core-app.md |
| APP-34 | slop | minor | S | State and protocol fields with no reader | open, owner | fix-list-core-app.md |
| HW-38 | slop | minor | S | Comments and README carry Cinemate references, ticket numbers, names and history | open | fix-list-hardware.md |
| CAM-18 | slop | minor | S | conform_fps: persisted, settable, published and in presets, with no reader and no control | open | fix-list-camera.md |
| CAM-23 | docs | minor | S | Tested scope not stated: sensor paths run on a CM5 only; drivers need kernel 6.12 | open | fix-list-camera.md |
| CAM-34 | slop | minor | S | Driver dead code: an unused VMAX override, identity wrappers, dead crop macros | open | fix-list-camera.md |
| REC-21 | knob | minor | S | A/B and restore env knobs left in the recorder and encoders | open | fix-list-recording.md |
| WEB-33 | slop | minor | S | Comments: ticket ids, Cinemate references, banners, stale text in a page with no comments | open | fix-list-webui.md |
| WEB-34 | slop | minor | S | Operator text: long card copy, env names, core.py, board-specific numbers, separator and glyphs | open | fix-list-webui.md |
| WEB-35 | slop | minor | S | Dead CSS rules and dead ladder helpers | open | fix-list-webui.md |
| UI-15 | slop | minor | S | Fallback ceilings: dead ISO fallback, empty FPS block, edited 25 fps cap | open | fix-list-touch-ui.md |
| UI-16 | knob | minor | S | APERTAR_UI_PREVIEW_RECORDING_FPS experiment knob kept, and it stalls the Rec Run timecode | open | fix-list-touch-ui.md |
| UI-20 | slop | minor | S | Ticket ids, names, dates, "CineMate" and stale "green" in comments; missing include | open | fix-list-touch-ui.md |
| UI-26 | slop | minor | S | String-or-number tolerant parsing for typed Core fields | open | fix-list-touch-ui.md |
| TXT-10 | docs | minor | S | Developer-only knobs that stay have no home once the README table goes | open | fix-list-text-history.md |
| APP-50 | docs | nit | S | Core's liblj92 README.apertar.md says 'in the UI' | open | fix-list-core-app.md |
| CAM-44 | slop | nit | S | CdngLog accepts spellings that never shipped; CdngLog::Auto means On | open | fix-list-camera.md |
| REC-39 | slop | nit | S | Diagnostic response headers no page reads | open | fix-list-recording.md |

## Milestone 4: commit series

8 rows, all open. Cut last, from the final tree, with one `commit-plan.md` for Core, UI and both drivers.

| Id | Kind | Sev | Eff | Title | State | Read more |
| --- | --- | --- | --- | --- | --- | --- |
| TXT-1 | commit | blocker | L | Core history cannot be reviewed: a 12-feature squash, 10 merges with conflict work inside, swapped hunks | open | fix-list-text-history.md |
| UI-9 | commit | major | M | UI commit series: experiments, churn, ticket numbers, and Core pairs | open, owner | fix-list-touch-ui.md |
| TXT-2 | commit | major | L | No single clean series: experiment chains, flip-flops and four rewrites of one card stay in history | open | fix-list-text-history.md |
| TXT-3 | commit | major | M | Commits that do not build alone; Tested: lines describe a later run; tests cited that are not in the tree | open | fix-list-text-history.md |
| TXT-4 | commit | major | S | Behaviour changes against 1.6.0 hidden inside unrelated commits | open | fix-list-text-history.md |
| TXT-5 | commit | major | M | Commit messages carry tutorial and work-package ids, dead SHAs, KB paths, names and branch prefixes | open | fix-list-text-history.md |
| TXT-6 | commit | major | S | Authors and trailers: 11 + 14 commits authored "Claude", three model names, session URLs, cherry-pick lines | open, owner | fix-list-text-history.md |
| CAM-38 | commit | minor | M | Driver histories: experiments, reverts, fix-ups and WP numbers in subjects | open | fix-list-camera.md |

## Order of work

Each step lists what must be in place first. Steps inside one number can run in parallel lanes.

1. **Owner answers first** (`owner-decisions.md` rows 1-10): storage switch home, Boot Config editor, IMX585 crop names, ceilings and lossless policy, tuning file, first-run writer, ladder file and rules, timecode, clip-name composer. Work on the items behind them waits; everything else starts.
2. **Reply and dispatch plane.** APP-5 (one okReply/errorReply, sentences plus HTTP status, CMD-9) before APP-7 (one dispatcher, absorbs HW-21), APP-24, APP-43, REC-18, HW-20. Every later Core item replies through it.
3. **Boot Config, one commit set.** HW-1 answer, then HW-4, then HW-5 with APP-13 (root helpers out of Core). REC-3 (trim default off) lands before or with APP-13; REC-9 after it. Then HW-11 (engine size follows HW-1), WEB-1 and WEB-5 (page half), HW-6, HW-23, HW-24, HW-37, HW-39, WEB-31.
4. **Hardware-file ownership.** REC-1 (App parses [storage], CC receives an option struct, the [camera] ISO caps become constants) after the APP-11 answer; then APP-10 (minus its step 1), REC-2 (statics to members), APP-11, APP-28, APP-21, APP-35. Rule CAM-19 holds after this step: nothing in `src/camera` opens the hardware file.
5. **Pre-roll, one commit set.** APP-12, REC-10 and CAM-6 after step 4 (and APP-2, done). Then APP-30, APP-31, APP-27, WEB-18, WEB-4, REC-40.
6. **Env knobs and tuning.** APP-9 before APP-21, APP-23, WEB-16; APP-14 answer before APP-15, CAM-9, REC-21, REC-13, REC-14, UI-16. APP-42/CAM-30/REC-37 (host tests) after APP-13 and APP-14.
7. **Camera modes.** CAM-1 (driver and Core together) before CAM-22, CAM-23, CAM-32, CAM-33, UI-5, WEB-6. CAM-10 rest before CAM-2; CAM-2 before CAM-6, CAM-9, CAM-14, CAM-45; CAM-14 before UI-14, WEB-14. CAM-20 before CAM-8; CAM-8 before CAM-16, CAM-31, CAM-41, CAM-44; then CAM-17, CAM-19, WEB-6, WEB-7, WEB-19. CAM-4 (TDN header) after CAM-3 (done).
8. **Hardware inputs.** HW-2 and HW-20 before HW-19, HW-16, HW-17, HW-18, HW-10, WEB-24. HW-12 before HW-30. HW-7, HW-8 before HW-31, then HW-32, HW-42. HW-13 before HW-14, HW-15, HW-27, HW-35, HW-40; HW-3 and HW-14 before HW-33. HW-22 before HW-26. APP-16 after its answer and after HW-2.
9. **WebUI page.** WEB-2 (names) before WEB-20, then WEB-3, then WEB-10, WEB-28, WEB-26. REC-30 (token list) before WEB-8 and UI-8. WEB-21 to WEB-23 after the cards they touch have moved.
10. **Touch UI.** UI-2 (READY during a flush, footage risk) first and alone. UI-1 with APP-45 and WEB-13 after the timecode answer. UI-3 with APP-47 and WEB-15. UI-6, UI-7 from `lane/ui1`; UI-11, UI-12, UI-13 after step 4 (state keys settle).
11. **Milestone 2 bugs** on the reworked code: the lane fixes (REC-5, REC-6, REC-7, HW-2) integrate first; a bug inside code that milestone 1 deletes is closed by the delete, not fixed. Board items after their owners: HW-24 after HW-11, HW-26 after HW-22, REC-23 and CAM-23 need the board tests T3-T6, T8 (`raw/sweep-board-support.md`).
12. **Milestone 3 text** per file after that file's structural items: APP-17, CAM-11, CAM-12, REC-12, HW-38, UI-20, WEB-33, WEB-34, WEB-35; then APP-18 (README) after APP-9, APP-13, APP-14; then TXT-7 (gate over all four repos), TXT-10, TXT-8 (after CAM-12, CAM-22, CAM-38).
13. **Pi pass.** One run of every "Needs the Pi" line on the integrated tree: safety stop, pulled drive, pre-roll, Boot Config, crops, ceilings, GPIO inputs, touch panel.
14. **Milestone 4 series** from the final tree: TXT-1 (one commit-plan.md, no merges), then TXT-2 to TXT-5, TXT-9, UI-9, CAM-38 in that plan; TXT-6 trailers and TXT-8 branch per the owner's answers. `git diff <final tree> <clean tip>` must be empty.

## What conforms

1. New settings are CaptureSettings fields added in place, in both serialisers, persisted as else-if branches in the existing reader (rule CAM-25).
2. New setters are bool setters on CameraController under its one mutex: lock, gate with a sentence, applySettingsLocked (rules CAM-7, CAM-8).
3. IMX283 arrives by recipe R5: one SensorFamily value, one case per sensor switch, crop maths beside upstream's.
4. Mode tables, ladder, phase lock and clip names are small header-only std code without libcamera includes (rules CAM-1, CAM-4); Core still builds without libcamera (rule CAM-28).
5. Most new socket commands are flat handleCommand blocks with scalar arguments that reply settingsBody (CMD rules).
6. New state and the `media` event are flat snake_case scalars; absent new fields give the 1.6.0 behaviour (CMD-30).
7. Log lines keep `ApertarCore <area>: key=value`; repeated warnings are rate-limited (rules STY-7, CAM-23).
8. The touch UI's new switches follow recipe R3; bridges add read-only Q_PROPERTYs and go through sendCoreCommand (UIC-3, UIC-4).
9. Operator error texts keep upstream's one-sentence shape; no AI residue, TODO, debug print or build warning in port code.
10. Lossy DNG write failures now fail the take, and a pulled drive ends the take through upstream's checkRecordingFailure supervisor.
