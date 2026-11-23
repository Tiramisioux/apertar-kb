# Plans and fixes checked against the owner's recorded decisions (summary)

The eight rework plans in this folder were written from the code and the review findings. They were then checked
against every decision Patrik recorded in this knowledge base (collected in `../owner-recorded-decisions-a.md` and
`../owner-recorded-decisions-b.md`, 211 rows). This page lists the conflicts found and the variant that keeps the
decision while a stock camera still behaves as Apertar 1.6.0. The full tables are at the end of each plan page,
section "Checked against the owner's recorded decisions".

State at the pause (2026-11-17): audited: hardware-inputs, command-plane, storage-settings, preroll, webui-state.
**Not yet audited: touch-ui, camera-modes, boot-config-helpers, and the fixes already made** (two of these audits
were running when the campaign was paused; they must be re-run before those plans are implemented further).


## hardware-inputs

4 conflicts, 21 commits fine.

| Commit | Decision it touches | Problem | Variant that keeps the decision |
| --- | --- | --- | --- |
| plan 2 (delete scriptPaths guard) | DA-4 / controls Q2: "[run_script] paths: ssh only; the browser cannot write them"; DA-28, DA-29 | Deleting the guard lets the browser set script paths again, which reverses Q2. | Do not land the plan text. Use the lane variant 476ca75 (guard kept; Undo, History and restore may put back a kept version), gated as described in the lane commit 2 row. |
| lane 476ca75 (plan 2 variant) | DA-4 / Q2 kept; the stock-camera rule | The guard is always on, so a stock camera's Config page refuses a [run_script] path edit that 1.6.0 wrote (App:5323-5386@upstream-1.6.0 has no such check). | Run the guard and keptScriptPaths only when APERTAR_SCRIPT_PATHS=ssh is set in Core's environment; unset means 1.6.0 behaviour. Precedent: upstream APERTAR_LOSSYDNG_ASYNCWRITE (LossyDngEncoder.cpp:325-328), port APERTAR_MEDIA_TUNE=1 opt-in. Set it in /home/pi/start-apertar-core.sh. About +5 lines and one README sentence. KB controls_store_test.cpp:146-151 sets the variable before its script-path checks. |
| plan 5 (delete the merge review) | DA-20 / controls Q17: "Stale text save: merge per key when only values changed and no key clashes, shown as a review before saving; otherwise refuse" | The commit deletes textToEdits, confirmMerge, needsReview and the merge_review code. It also breaks KB controls_store_test.cpp section 4 (lines 117-135). | Drop commit 5 and keep the Core merge as it is. The Config page never wired the review (WCP:19025 treats merge_review as Reload; POST /api/config sets no confirmMerge). Whether to wire it is his question, for the webui-state theme. A stock camera is not affected. |
| plan 10 (delete held-at-start inversion) | DA-34: "like Cinemate (gpio_input.py check_initial_state): ... one that already reads pressed is taken as wired the other way round and inverted ... with a journal line naming it"; DA-39: "PCF pins get the 1-0-1 inversion at start" | The commit removes a feature he asked for. Keeping it always on changes a stock camera: a button held at start is inverted for the session, where 1.6.0 ignored it until release. | Add a section bool invert_on_start (parseConfigBool, default false) in [gpio_buttons] (buttons branch only, not shared with [gpio_encoders]) and [pcf8574]. False: held at start is ignored until released (1.6.0). True: today's inversion and journal line (GpioInput.cpp:620-631, Pcf8574Input.cpp:424-435). Precedent: upstream [neorotary4] reset_on_start (NeoRotary4Input.cpp:419), [grove_analog] emit_on_start (GroveAnalogInput.cpp:309). Add a comment line to the template; knownKey accepts the key; no Controls card row. Switches (DA-36) and NeoRotary unchanged. Drop commit 12. Pi: grep the journal for 'taken as inverted'; any line means he sets invert_on_start=true. |

Decisions this plan must keep:

- DA-4/DA-28/DA-29: [run_script] paths ssh only (when APERTAR_SCRIPT_PATHS=ssh); Undo/History/restore may put back kept versions (DA-18 Undo last save)
- DA-34/DA-39: Cinemate held-at-start inversion for GPIO buttons and PCF pins (invert_on_start=true); none for switches (DA-36); NeoRotary push held at start counts from release
- DA-20 / Q17: a stale text save merges per key with a review, otherwise it is refused; do not delete the merge
- DA-3 / Q1: Core owns ~/apertar-hardware.conf, notes in ~/.config/apertar-core/; DA-84: APERTAR_HARDWARE_CONFIG and XDG_CONFIG_HOME stay honoured
- DA-7: [ina219] enabled=true in the template; DA-8: detect and show, nothing written from a scan
- DA-25: history of 20 versions plus the pinned Before Controls
- DA-30: fixed gesture timings (0.5 s click window, Hold 3 s); DA-35: edge-event wait loop untouched
- DA-31/DA-36: switch keys, position applied at Core start
- DA-22: touch chip on errors only; DA-6: save during a take is written now, applied after
- DA-15: KB host tests built on his live file keep building (commits 17 and 19 update them)

Open questions a recorded decision already answers:

- Owner Q1 (script paths from the browser): DA-4/Q2 says no, ssh only; Undo/restore of kept versions allowed; behind APERTAR_SCRIPT_PATHS=ssh for stock
- Owner Q2 (normally closed buttons): DA-34/DA-39 say yes, by the Cinemate inversion; keep it behind invert_on_start, drop commit 12
- Owner Q3 (who writes the first file): DA-3/Q1 says Core
- Owner Q4 (IMU on in the first file): DA-7/DA-8 say on, as he kept INA219 on by default with absent hardware shown as not found
- Owner Q5 (chip, merge review): DA-22/Q19 keeps the chip; DA-20/Q17 keeps the merge review (page wiring still his call)
- hold_ms/double_ms per source: DA-30 replaces DA-9; timings fixed in code, commit 21 refuses the keys

## storage-settings

5 conflicts, 16 commits fine.

| Commit | Decision it touches | Problem | Variant that keeps the decision |
| --- | --- | --- | --- |
| 17, 18 (decision 3: media tuning file family deleted) | Request of 2026-11-02 (working/drop-frames/media-tune-file.md:3-5): a tuning file per storage medium next to the hardware conf, test nights can override it from the command line; DA-104 / DB-65 'everything back' kept the media-tune reader; DA-88 APERTAR_MEDIA_TUNE opt-in | Plan recommends option a), which deletes the file, the /run override and scripts/apertar-tune. Option c) as written also drops the override and the editor he asked for | Decision 3 = keep the base file, the /run override and apertar-tune; drop commit 18. Commit 17 removes only the statics: MediaProfile carries the resolved MediaTune (deriveMediaProfile already loads it, MediaProfile.hpp:195), App hands the profile over in commit 16, the read sites CdngEncoder.cpp:91, CC:1467, :4364, :4718 read the copy. Env still wins. A stock camera has no file (only 'apertar-tune init' or a hand cp creates it), so code defaults apply; upstream precedent: tuningOverride /home/pi/.apertar-tuning, ProresEncoder.cpp:771-813@upstream |
| 20 (switches of finished A/B tests) | DB-71 / DB-72 NVMe campaign requirements; the campaign uses APERTAR_AUDIO_BUFFER_MS as a lever (apertar-campaign-helper.sh:36,:207,:244; longtakes.py --audio-ms :2756-2758; nvme-campaign/plan.md:277,:285; handoff-nvme-campaign.md:103) | Deletes APERTAR_AUDIO_BUFFER_MS: the helper's arm and the per-take environ read-back fail, and the long tiers lose their recorded fallback | Keep APERTAR_AUDIO_BUFFER_MS unchanged (already env only, read where used, AudioRecordingSession.cpp:208-218; R8 shape like APERTAR_CDNG_QUEUE_FRAMES CC:3328-3330@upstream). Delete the other three as planned |
| 21 (knobs nobody set become constants) | DA-82 dual-sensor sync from Cinemate's phase lock 'in software'; DA-87 / DB-56 phase lock stays, off; APERTAR_PHASE_LOCK_DEADBAND_US=100000 used as a meter (hardware-log.md:262-263) and in dual-sensor test 1.1 (design-dual-sensor.md:1081, sync-synthesis.md:210) | The phase-lock knobs were set, and a planned test needs them; making them constants breaks test 1.1 | Keep APERTAR_PHASE_LOCK_KP/_KI/_DEADBAND_US/_CLAMP_US (read once, CC:8910-8923@core-work). The other knobs become constants as planned. Stock: the lock is off by default, no effect |
| 23 (conform_fps and directIo gone) | DA-92 / DB-31 request 21: 'conform_fps, the project's timeline rate, default 25' (ramp-ladder/README.md:48, fork-log.md:67); dual-sensor forwards set_conform_fps | The plan calls conform_fps unused and deletes it, but it is his request | Keep conform_fps (field, loader/writer, set_conform_fps, serialisers, preset key, carry-over); only directIo goes. Stock unaffected: nothing derives from it (Types.hpp:135-136), only a port field in the state |
| 24 (stock writes as 1.6.0) | DB-65 'everything back': trim switch default on, APERTAR_DNG_DONTNEED=sync default | Both defaults change a stock camera (1.6.0 drops in the writer, CdngEncoder.cpp:1777@upstream; no trim), so the plan flips them to the 1.6.0 values, against his chosen defaults | Keep commit 24 as planned: it is the form the review rule prescribes. Under the variant of 17 his rig needs no drop-in: ~/apertar-media-tune.conf already holds dontneed=sync writeback=on sync_ms=1000 and the exfat writer rows, and camera_settings.conf already holds a media_trim= line that keeps its value. The Pi step becomes two greps of those files before updating |

Decisions this plan must keep:

- DB-61: Record during a safety-stop flush discards queued frames and starts at once; the old clip is cut short, written frames stay (commit 14)
- 2026-11-02 request / DA-104 / DB-65: keep ~/apertar-media-tune.conf, its /run override and scripts/apertar-tune; env still wins
- DA-92 / DB-31: keep conform_fps (default 25, 1-120, persisted, carried, in presets)
- DA-90 / DB-19: Clear HDR ISO caps 1585 (16-bit) / 720 (12-bit)
- DA-105 / DB-66 / DB-67: clip split and merge worker stay; merge on by default; frames_per_folder default 0
- DB-65 / DA-88: trim, sync drop, sync thread, writeback stay operator options (off on stock); APERTAR_MEDIA_TUNE opt-in
- DB-101: RAM fraction stays his choice; env knob kept, default 0.6 / 512
- Campaign levers kept: APERTAR_AUDIO_BUFFER_MS, APERTAR_DNG_DONTNEED, APERTAR_DNG_WRITEBACK, APERTAR_MEDIA_SYNC_MS, APERTAR_PHASE_LOCK_*
- Command names and fields the KB scripts read stay (set_frames_per_folder, set_clip_merge, set_media_trim; frames_per_folder, clip_merge_*, buffer_setting, media_trim_running/_last_*)
- DA-3: Core stays the hardware file's writer; with the read-only takeover it writes nothing there for this theme
- DA-77: no touch screen on his rig; no UI commit is needed

Open questions a recorded decision already answers:

- Decision 3 (media tuning file): keep it with override and editor (2026-11-02 request, DA-104/DB-65); drop commit 18, shrink 17 to the statics
- Decision 4 (stock write-path defaults): b) commit 24 per the review rule; his rig keeps his values through his own media-tune file and camera_settings.conf
- Decision 10 (remove moved keys): read-only takeover keyed on the keys the constructor's load saw (DA-3 allows but does not require an edit; DA-8 nothing written automatically; upstream SettingsBridge precedent)
- Settled item 2 (refuse buffer / frames-per-folder change during a take): DA-6 points to 'allowed, applies to the next take' (today's behaviour); ask him
- Env twins for the dual-sensor secondary: not needed; its own XDG camera_settings.conf or its role gate holds pre-roll and trim off (DA-84 is an unanswered plan, DA-83)
- conform_fps removable? No, request 21 (DA-92/DB-31)
- Knobs of commits 20-21 still used: APERTAR_AUDIO_BUFFER_MS (NVMe campaign) and APERTAR_PHASE_LOCK_* (dual-sensor sync test, meter)
- Clear HDR 12-bit cap if the fixes move it: the measured value becomes the constant (DB-19, request 18 'measure')

## preroll

6 conflicts, 13 commits fine.

| Commit | Decision it touches | Problem | Variant that keeps the decision |
| --- | --- | --- | --- |
| 0977dd6 (in the tree) automatic pre-roll off by default | nvme-campaign plan "the pre-roll stays ON as in real use"; DB-71 tests as in real life | His rig file has no `preroll` key (the template wrote `# preroll=on` commented out), so his camera goes from on to off by itself. Real use and his campaigns run it on (nvme-campaign/plan.md:231, :307). longtakes.py:2766 voids every take and e3-unit.sh:19-20 stops with NOT STARTED after 10 min | No code change; the default stays off (stock = 1.6.0). The fix log and the owner page tell him to send `set_storage_preroll value=on` once (App:12928-12934) or add `[media] preroll=on` |
| 4. the 1 Hz loop ends a storage pre-roll through record_stop | His campaign scripts in working/tools (e3-unit.sh, takes_from_journal.py) | The plan splits the log into a start line with reason= and an end line with end=/result=. e3-unit.sh greps `reason=start.*result=` and `result=[a-z]+ ms=[0-9]+`; takes_from_journal.py marks the clip before any `storage preroll: reason` line as the pre-roll | Keep one end line `ApertarCore storage preroll: reason=<trigger> fps= measured_fps= seconds= frames= bytes= result= ms=` in today's order, with `end=<...>` added after `ms=`. Any start line uses another prefix (`storage preroll started: trigger=...`) |
| 4, 5, 6 Pi checks (card pull, card insert, format_media) | hardware-log.md:354-355; dual-sensor/HANDOFF.md:273-277 (never format_media/eject_media to a Core under test, formatting is his) | On his CM5 the CFexpress card cannot be hot-plugged: a re-inserted card needs a PCIe rescan or a reboot. Formatting and format_media to a Core under test are his alone | The card pull is optional and his call, on the Samsung T7 USB SSD. reason=mount is tested with his remount commands; reason=format only if he formats, else the --simulate check stands. sudo steps are command blocks for him to run |
| 13, 14. rename storage_preroll to storage_preroll_start | His NVMe campaign runner (working/tools/longtakes.py); DB-92 least intrusive change | His campaign runner sends `core('storage_preroll', seconds=5)` (longtakes.py:3197). The plan's 'Confirmed that nothing else sends it' is wrong | Keep `storage_preroll` (decision 2 = keep) and drop commits 13 and 14. Upstream has no command aliases. If he wants the rename, the same merge changes longtakes.py:3197 and he says so |
| 12. pre-roll at the mode's recordable maximum fps (held, decision 1) | hardware-log.md:842-855 (sensor maximum confirmed by the owner); DB-52 fps max from the sensor; nvme-campaign/plan.md:102, :246 | Option A runs the pre-roll at the arm's own fps, so the runner's encoder capacity reading (longtakes.py:3194-3205, :3257-3268) becomes meaningless | Not option A while his runner uses the pre-roll as the capacity reading. B keeps it on the IMX585 (the lossless ceiling equals the mode maximum, FpsCeiling.hpp:42, CC:3148; it differs from today only by the ladder and speed-ramp ceilings, which the runner turns off). B or C is his choice |
| Findings X-knobs-3 (env twin APERTAR_STORAGE_PREROLL goes with storage-settings) | DA-84 (dual-sensor env switches); DB-91 each change behind an env knob or setting | The dual-sensor plan starts the secondary with APERTAR_STORAGE_PREROLL=0 (design-dual-sensor.md:133, :216, :1042). Removing the switch breaks that plan | Keep the env read in automaticEnabled (SP:92-99). With default off it does nothing on a stock camera. Upstream precedent: APERTAR_LOSSYDNG_ASYNCWRITE (LossyDngEncoder.cpp:325@upstream) |

Decisions this plan must keep:

- Automatic pre-roll default off (stock = 1.6.0); his rig turned on with one command he sends (`set_storage_preroll value=on`)
- One journal line per run starting `ApertarCore storage preroll: reason=<trigger>`, today's fields and order, `result=<word> ms=<n>` adjacent; no other line with that prefix before the pre-roll's clip line
- The `storage_preroll` command name, its `seconds` argument (1-10) and the ok/error reply shape
- `storage_preroll_active`, `storage_preroll_last`, `storage_preroll_auto` top-level in socket get_state; the lastOk text with '(measured N)'
- Pre-roll fps as he confirmed (sensor maximum) until decision 1; the measured fps comes from sensor timestamps
- Trim before an automatic pre-roll and after every pre-roll delete (DB-65)
- APERTAR_STORAGE_PREROLL=0|1 keeps working (DA-84)
- Italic fps readout while it runs (DA-98)
- Pi steps fit his camera: no touch screen (DA-77), CFexpress not hot-pluggable, formatting and sudo are his

Open questions a recorded decision already answers:

- Decision 2 (rename): keep `storage_preroll`; his runner longtakes.py:3197 sends it
- Decision 1 (fps), in part: not option A while his campaigns use the pre-roll as the capacity reading (hardware-log.md:842-855, DB-52)
- Is the automatic pre-roll off on his camera after 0977dd6: yes unless his file has preroll=on; he turns it on with one command
- X-knobs-3 env switch: keep it (DA-84, DB-91)
- Pi checks: on the HDMI output with a mouse, not a tap; remount by his commands; the card pull only on the T7, if he wants it

## command-plane

8 conflicts, 10 commits fine.

| Commit | Decision it touches | Problem | Variant that keeps the decision |
| --- | --- | --- | --- |
| 1 (landed 1c5c76a) | DA-1 "with the functionality of Apertar api"; DA-3/Q1; DA-8/Q7 detect and show; DA-38 hat on Config > Hardware; DA-84 APERTAR_HARDWARE_CONFIG lookup | After get_controls is gone, tutorial.py can no longer read the controls state: it refuses any curl stage naming /api/config and still lists get_controls as safe. The KB copy of controls_page_test.js still mocks get_controls. | No code change. Alongside, in the KB: tutorials/tutorial.py drops get_controls from SAFE_CORE_CMDS (:48-49) and refuses /api/config only when the curl stage sends a body or another method (-X POST, -d, --data*, -F, -T) (:192-193). The KB copy of working/tools/controls_page_test.js takes the lane's GET /api/config mock (:67). |
| 2 (landed 7625476) | DA-25/Q22 "History: 20 versions + a pinned 'Before Controls'"; HANDOFF-next test 3 Undo | The same KB-tool break as commit 1, for controls_history. | Drop controls_history from tutorial.py SAFE_CORE_CMDS; /api/config/history passes once commit 1's curl rule is narrowed. KB controls_page_test.js:68-70 and :270 take the route mock. The store (20 versions plus the pinned entry) is untouched. |
| 3 (landed a035679) | DA-8/Q7 found / not found / error; DA-2 i2c channel settings for his fix; owner camera facts (CM5 only) | The commit's Pi check and the owner row ask for a Pi 4 / CM4 measurement; he has only a CM5. | Pi check on his CM5 bus 1 (hat 0x34 and NeoRotary seesaw 0x49 behind the Qwiic hub), expecting HANDOFF-next test 4's result. The Pi 4 and CM4 timings are 'not run' and go to the original developer. |
| 6 | Q17/DA-20 stale text save merges per key, shown as a review, otherwise refused; Q2/DA-4 script paths ssh only | The merge members look unused (the page never shows the review), so a cleanup could delete the half-built Q17 review. The KB test checks the 'Line 140' list and the 'Your choices stay on the page' wording, which the commit removes. | Keep textToEdits, conflicts, needsReview, confirm_merge and the set_controls 'merged' member, and the script_paths refusal sentence (HardwareConfigStore.cpp:331-334). Change controls_page_test.js:229-244 to Core's sentence in the same step. |
| 8 | DA-65 "Playback is held in standby and in long-interval timelapses"; DA-51 hold everything; DA-46 downloads get 409 in a take; DA-72 holes drawn black | WCP:12809 opens a clip with pbvApplyHold(clip.hold // snapshotHold // 'recording'). Without the hold member, a clip opened in standby within a second of the last poll shows the Recording card with Live, not the Wake card. | On a 409 the page fetches GET /api/state (lock-free, state key playback_hold, App:9561) and calls pbvApplyHold with that hold, falling back to 'recording' only when it is empty. The timelapse hold sentence becomes 'Stop recording or the timelapse before playing or downloading media.' |
| 9 | DA-78/79/80/81, DB-82, DA-21; standing rule: never send set_boot_config without dry_run to a Core under test | The Pi check needs a Pi 4 with the stock DPI screen. He has none, and his DPI overlays are commented out, so the display guard cannot fire on his rig. | No code change. The Pi 4 + 720x720 DPI check goes to the original developer. On the CM5, saves and the reboot are a command block he runs; Claude's probes use dry_run=true. |
| 11 | DA-77 no touch screen, only the WebUI and HDMI | The Pi check names the 720x720 screen. | His Pi check: the touch UI seen on HDMI with a mouse. The 720x720 step goes to the original developer. |
| 12+13 (rename option) | DB-65 everything back (pre-roll); DB-71..73 NVMe campaign tooling | working/tools/longtakes.py:3197 calls core('storage_preroll', seconds=5). | If the owner takes the storage_preroll -> storage_preroll_start rename, change longtakes.py:3197 in the same step. Commit 12 as planned is fine. |

Decisions this plan must keep:

- Q2/DA-4: the store's script_paths refusal stays, with its sentence, for every HTTP client, with or without a revision or Origin
- Q17/DA-20: keep the store merge path (textToEdits, conflicts, needsReview, confirm_merge, merged); merge_review stays a 409 refusal with a sentence
- Q5/DA-6: saving during a take stays allowed; the lock move adds no take refusal to set_controls
- Q7/DA-8: reads probe known addresses on demand and write nothing, no file and no counter
- Q22/DA-25: 20 history versions plus the pinned 'Before Controls'
- Q20/Q21: Listen (controls_last_input) keeps working from a phone and on a fresh board
- DA-38: the hat row stays on Config > Hardware for a file with [cfexpress_hat] (his is on bus 1)
- DA-84: the hardware file path keeps coming from $APERTAR_HARDWARE_CONFIG
- DA-46/51/52/65/72: holds in a take, a timelapse and standby; 409 for downloads; each hold keeps its own card text and button; holes stay black
- DA-78/79/80/81: config.txt edited in place, Apertar layout, Core the only writer; the display guard keeps refusing
- DA-87/DB-56/DB-65/DA-93: commit 15 changes spelling only, no default
- DA-77 and the camera facts: CM5, HDMI monitor, no touch screen, no Pi 4, CM4 or DPI screen; a Pi check on hardware he lacks is 'not run' or for the original developer
- Rename or move a command: update tutorials/tutorial.py, working/tools/controls_page_test.js and working/tools/longtakes.py in the same step

Open questions a recorded decision already answers:

- 2 s file check in the Controls worker (App-4-F7): Q3/DA-5 'Hand edit over ssh: not applied on the side; applies on Apply / next start / Save and apply both' -> option b. There is no apply_controls in the port, so an ssh edit applies at the next save or at a restart; it stays the hardware-inputs theme's commit
- set_cdng_log value=auto|off vs enabled=: DB-62 (no Log in SDR lossless, the UI says it is not applied) and DB-64 (Log is an extra option) -> keep 'auto' (probable)
- scan_i2c 'measure on a Pi 4': camera facts (CM5 only) -> measure on his CM5 bus 1; the Pi 4 number is left for the original developer
- 1 s get_state poll: DA-77 and the facts (HDMI monitor in use) meet the plan's condition for option b; the choice stays his
- Socket clients losing get_controls/controls_history: DA-1 does not answer it; option a keeps the controls on Apertar's API; stays open (commits 1 and 2 already landed with a)

## webui-state

8 conflicts, 16 commits fine.

| Commit | Decision it touches | Problem | Variant that keeps the decision |
| --- | --- | --- | --- |
| 11 web: Remove in the Clip Browser asks with window.confirm | DA-43 (WebUI playback looks and behaves like the touch UI's Clip Browser/Viewer); design-playback.md B23 'the old window.confirm is removed from the delete helpers', V12 'Remove Clip?' dialog, V17 | Replaces his approved and tried Remove dialog with window.confirm; the plan wrongly claims WEB-21 settles it | Drop commit 11; the dialog stays as documented new ground, renamed in commit 15 (.media-browser-dialog*), buttons already secondary-/danger-button. It exists only inside the port's Clip Browser |
| 12 web: the Clip Browser header uses upstream's title, Back, Refresh, filter row and sort select | DA-43; design B2 PLAYBACK eyebrow, B3 per-category titles, B5 SHOW menu, B6 Refresh with refresh.png, B10 sort chip replacing the <select>; DA-49 (Q2) 'filter only (opens on Stills in photo mode)' | Copying U:3981-4012 removes the eyebrow, Still/Timelapse/Audio Browser titles, the SHOW menu and the sort chip he chose | Reshape: keep eyebrow, titles, SHOW menu and sort chip; build them from upstream parts: Back = upstream's icon-button settings-back-button with text Back/Cancel, Refresh = secondary-button + /icons/refresh.png, SHOW and chip = secondary-button, title = h2.section-title, upstream ids where the job is the same; delete the 2 SVGs, .pb-top-button, .pb-h1; no filter row, no select |
| 14 web: the Clip Viewer uses the page's buttons and /icons PNGs | DA-43, design V8 'three circles ... round .icon-buttons with previous/play/pause/next PNGs'; DA-48 O1 frame step | Transport loses its round circles; frame step would get previous.png/next.png, the same glyphs as previous/next clip | .icon-button base plus one round modifier (.clip-viewer-transport .icon-button {border-radius:50%}); frame step as text glyphs in .icon-button; Info keeps info.png; Download as text secondary-button is fine |
| 20 web: the Mode Ladder and settings search draw no inline SVG | DB-51 'no drag and drop, the ladder orders itself by quality', 'Max boxes between rows'; DB-49 'one column of collapsible groups'; DA-32 white SVG blueprint sketches (wish) | The plan adds Up/Down/Remove buttons the ladder does not have (only ladderIcons.down P7:8195 and .chevron P7:8307 are used), which would bring back manual ordering; a page-wide 0-SVG rule would block DA-32 | Delete the dead handle/up/remove icons, drop the arrow on the Max line, draw the chevron in CSS like .settings-select's arrow (U:1535-1541 linear-gradients) turned by aria-expanded; DA-32 sketches later as files in src/web/icons via /icons/<name> |
| 22 web: the Clip Browser adds no browser history entries | DA-43 + design D19 'the browser's Back gesture and button close the viewer, then the browser (history.pushState/popstate)'; DA-56; tried: fork-log.md:102, measurements.md:132 'The phone's Back leaves the viewer first' | Deletes a behaviour he approved and tried | Drop commit 22 (owner Q1 option b); history stays as documented new ground under the new names, about 25 lines; pushState runs only when the overlay/viewer opens (P7:10135, P7:12783), so the rest of a stock page is 1.6.0 |
| 23 web: frame step and knob arrows send one step per click | DA-48 (Q9) O1 'Frame step ◀ ▶ (hold to repeat)' (design-playback.md:1473; built fork-log.md:102) | Removes frame-step hold-to-repeat he chose; the knob-arrow repeat (1319967, another session) has no decision | Split: keep repeatClipFrameStep and its two calls (P7:12940-12941); owner Q2 only for the Remote controls knob arrows; if removed, also change the card copy 'Hold an arrow to keep turning.' (P7:4577) |
| 6 web: the Controls page keeps its state in state | His Controls test harness working/tools/controls_page_test.js (60/60, controls/HANDOFF-next.md:31) evaluates controlsState.added/.removed/.edits at :240, :246 | The rename breaks the KB test | Apply the commit's sed map to controls_page_test.js in the same change set (state.controlsAdded.length, state.controlsRemoved.size, state.controlsEdits.size) and rerun it after commits 4, 6, 7; its mock must answer the /api/state refresh sendCommand schedules |
| 25 web: the Remote controls loader keeps its retry timer in state | DA-104/DB-65 keep Remote controls; no decision on its place; stock rule | Keeps a card (and a get_controls poll every 5 s) on every stock camera's main page, unlike 1.6.0 | Take commit 24 instead; if he wants the main-page card, it becomes a UI.conf option off by default shaped like frameBufferBarEnabled (App:1905, :2096, :7791; set_frame_buffer_bar_enabled), which needs Core and is outside this page-only plan |

Decisions this plan must keep:

- Clip Browser and Viewer look and behave like the touch UI's (DA-43, DB-75): PLAYBACK eyebrow, per-category title, SHOW menu, sort chip, Back that reads Cancel in selection, round transport, Remove dialog; change parts to upstream classes/ids/PNGs, not the shape
- SHOW only filters and opens on Stills in photo mode (DA-49)
- Phone Back closes the viewer, then the browser (design D19, fork-log.md:102)
- Frame step repeats while held (DA-48, O1)
- Download, Select All, Timelapse, Audio stay (DA-50); '1 item' wording (DA-54); thumbnails fill the card (DA-74); keep-awake only while playing (DA-57); Space play/pause (DA-64)
- REC pill READY green while the buffer drains after a safety stop, bar on or off; REC during the flush discards and starts at once, with its toast (DB-61); Frame buffer bar stays an option, off by default
- /api/buffer poll rate and start/stop rule unchanged (his NVMe campaign ran with frameBufferBarEnabled=true)
- Mode Ladder orders itself, Max boxes between rows, collapsible groups (DB-49, DB-51); no manual Up/Down
- Controls: Save during a take allowed (DA-6); stale save keeps edits on the page (DA-20); Listen stays (DA-23); Check shows Core's issues with line numbers
- Remote controls stays as a feature (DA-104), off the stock main page
- No page-wide 0-SVG rule that blocks DA-32 accessory sketches; they go to src/web/icons
- Rerun working/tools/controls_page_test.js after commits 4, 6, 7, updated by the same sed map

Open questions a recorded decision already answers:

- Owner Q1 (phone Back closes the Clip Browser?): DA-43 + design D19 + DA-56, tried (fork-log.md:102) -> keep pushState/popstate (option b); commit 22 goes
- Owner Q2 (hold-to-repeat): DA-48 O1 'hold to repeat' -> keep for frame step; question stays only for the knob arrows
- Owner Q3 (where Remote controls lives): no decision on the place; DA-104 keeps the feature and the stock rule picks the Controls panel (commit 24)
- Dropped owner item 7 (window.confirm vs dialog): DA-43 + design B23/V12 -> the dialog stays; commit 11 goes
- Header filter row and select vs SHOW menu and chip (not asked by the plan): DA-43 + B5/B10 + DA-49 -> SHOW menu and chip stay, built from secondary-button
