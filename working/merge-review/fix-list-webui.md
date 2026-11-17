# Fix list: WebUI page

Editor's list for the merge review. Domain: the WebUI page `src/web/WebControlPage.cpp` (`WCP`), units WCP-01 to WCP-08 and WCP-10 (WCP-09, the Controls editor, is in `fix-list-hardware.md`), plus the page-side findings of the sweeps stock-behaviour, state-consistency and protocol-security. Port ref `@cinemate-port` (Core `01f170c`). Upstream ref `@upstream-1.6.0` (`/home/user/wt/core-upstream`). `U:n` = `WCP:n@upstream-1.6.0`, `P:n` = `WCP:n@cinemate-port`, `App` = `src/ApertarCoreApp.cpp`. Rule ids `WEB-n`, `CMD-n`, `HW-n` are from `apertar-conventions.md`; they are written "rule WEB-n" so they do not clash with the item ids `WEB-<n>` of this list.

Items of other lists that carry a page step are listed in "Page steps owed to other lists"; they are fixed in the same commit as their Core half.

## Already done on the improvement branch

| Commit | What | Closes |
| --- | --- | --- |
| Core `04fe197` (worktree `/home/user/wt/core-work`) | GPIO chip setting back on the Controls page; claims and checks per chip | HW-controls-model-F1 (hardware list). Nothing in this list is fixed yet |

## Standard checks on this machine

| Id | Command |
| --- | --- |
| C1 compile | `/home/user/build/bin/check_core.sh <core tree> <tag> nolc` (the page is a C++ raw string; a stray `)APERTAR"` fails here) |
| C2 script syntax | `awk '/<script>/{f=1;next}/<\/script>/{f=0}f' <tree>/src/web/WebControlPage.cpp > /tmp/page.js && node --check /tmp/page.js` (passes at cinemate-port) |
| C3 reply shape | `/home/user/build/bin/smoke_core.sh <tag>-nolc/apertar-core 8810 out.txt`, diff against the cinemate-port output |
| C4 browser | `apertar-core --simulate --web-bind 127.0.0.1 --web-port 8810` (as in smoke_core.sh), then `google-chrome --headless=new --window-size=420,900 --screenshot=s.png http://127.0.0.1:8810/` or drive it over `--remote-debugging-port`; widths 420, 720, 1120 |

## Summary

| Id | Sev | Kind | Rec | Effort | Title |
| --- | --- | --- | --- | --- | --- |
| WEB-1 | blocker | security | ask-owner | M | Boot Config card: Edit file sends free text to a root write, through its own HTTP route |
| WEB-2 | major | mismatch | fix-now | M | Playback renames the original developer's media feature: pb*/pbv* functions, nested state.pb, .pb-* CSS |
| WEB-3 | major | mismatch | fix-now | M | Playback brings a second widget layer: modal scrim, History API, own buttons, menu, chip, cyan selection |
| WEB-4 | major | mismatch | fix-now | M | Second 4 Hz poll, second store frameBufferBar, recording pill written outside renderSnapshot |
| WEB-5 | major | mismatch | fix-now | M | Boot Config card internals: own store and installer, checkbox gate, own diff and select builders |
| WEB-6 | major | mismatch | fix-now | M | IMX585 resolution pills read the Mode Ladder reply; mode tables hand-copied in a private string format |
| WEB-7 | major | new-ground | ask-owner | L | Mode Ladder editor re-implements Core's ladder rules in JS, and they already differ |
| WEB-8 | major | new-ground | ask-owner | M | Clip-name composer: about 570 lines of drag-and-drop and long-press for one template string |
| WEB-9 | major | mismatch | ask-owner | S | White dropdowns scoped to the Controls panel by panel and id, dark again for some pin selects |
| WEB-10 | minor | removed | fix-now | S | Media list lost size, fps and frame count, per-row Download/Delete and Clear selection |
| WEB-11 | minor | removed | fix-now | S | Record button greyed without media; Core's reason never shown; "has media" decided by two fields |
| WEB-12 | minor | removed | ask-owner | S | ISO and WB badges no longer say Auto |
| WEB-13 | minor | removed | ask-owner | S | Timecode: upstream labels renamed, the favourite split in two, the card lost its value pill |
| WEB-14 | minor | stock | fix-now | S | ISO Auto offered by the page's own rule wherever Clear HDR is off |
| WEB-15 | minor | bug | fix-now | S | Loading a preset from the WebUI library drops frameBufferBarEnabled |
| WEB-16 | minor | mismatch | fix-now | S | APERTAR_* names and *_env greying in operator text; pre-roll switch not shaped like an upstream toggle |
| WEB-17 | minor | protocol | fix-now | S | Page parses Core's display text: write speed, buffer note; Log reason hard-coded for IMX585 |
| WEB-18 | minor | protocol | fix-now | S | Buffer and pre-roll settings published twice by Core; renderSnapshot copies system.* to the top level |
| WEB-19 | minor | mismatch | fix-now | S | Mode Ladder lock wired into the two generic pill builders; two lock mechanisms |
| WEB-20 | minor | mismatch | fix-now | S | Inline SVG icons (13 places) where the page uses /icons PNGs |
| WEB-21 | minor | mismatch | fix-now | S | Hiding by the hidden attribute with [hidden] patches; attribute and id selectors in CSS |
| WEB-22 | minor | mismatch | fix-now | S | Cards filed under the wrong topic: indicators in Live preview, a Performance card in System, Value Lists in Controls |
| WEB-23 | minor | mismatch | fix-now | S | On/Off switches from new classes (.switch-field, .ladder-pair); a label wraps the Log pills |
| WEB-24 | minor | mismatch | fix-now | S | Config editor Check goes through set_controls with a fake "h" revision; Save diff step kept |
| WEB-25 | minor | new-ground | fix-later | M | Settings search: MutationObserver and elements inserted at runtime |
| WEB-26 | minor | duplication | fix-later | M | Parallel CSS vocabulary: ladder buttons and tile re-create upstream ones; four chip classes |
| WEB-27 | minor | mismatch | fix-later | S | Stylesheet order and breakpoints: 741 lines inside the pill-button group, media queries at 1119/719/419 |
| WEB-28 | minor | bug | fix-later | S | Clip viewer: stale badges on non-cDNG items, blank after a hold, freeze on a short WAV |
| WEB-29 | minor | bug | fix-later | M | Crop picture and ladder names assume the IMX585 3840x2160 readout on every sensor |
| WEB-30 | minor | bug | fix-later | S | Exact shutter angle leaves no pill active (60 fps at 22.5 deg) |
| WEB-31 | minor | bug | fix-later | S | Boot Config reboot wait polls /api/buffer and misreports a slow shutdown |
| WEB-32 | minor | duplication | fix-later | S | FPS caps re-applied in JS on top of Core's fps_max; an empty if-branch |
| WEB-33 | minor | slop | fix-later | S | Comments: ticket ids, Cinemate references, banners, stale text in a page with no comments |
| WEB-34 | minor | slop | fix-later | S | Operator text: long card copy, env names, core.py, board-specific numbers, separator and glyphs |
| WEB-35 | minor | slop | fix-later | S | Dead CSS rules and dead ladder helpers |
| WEB-36 | minor | board | keep-and-document | S | Player pacing tuned on a Pi 5 only |
| WEB-37 | nit | new-ground | keep-and-document | S | WebUI-only panels (Modes, Controls) and three editors of apertar-hardware.conf |
| WEB-38 | nit | duplication | fix-later | S | Small duplications: flicker-free maths, ladder toast, raw createElement, typeof number checks |

**Needs the Pi.** Only WEB-4 (safety stop and pre-roll pill), WEB-1/WEB-5 (one save and reboot), WEB-28 (short-WAV take), WEB-36 (Pi 4 pacing). Everything else is checked here with C1-C4.

---

## WEB-1. Boot Config card: Edit file sends free text to a root write, through its own HTTP route

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| security | blocker | M | yes | ask-owner | WCP-10-F4, WCP-10-F3, WCP-10-F1, WCP-03-F2, X-protocol-security-1 (page half), X-protocol-security-7 (page half) |

**Where.** `P:5925-5951` (buttons, Edit field); `P:19868-19911` (bootConfig store, BOOT_CONFIG_MANAGED, bootConfigManagedMap/Summary, bootConfigOwnLinesHint); `P:20004-20016` (bootConfigPost to POST /api/boot-config); `P:20418-20550` (toggleBootConfigFile, showBootConfigEditorMarks, bootConfigEditorEdited, useBootConfigText, three POST /api/boot-config/parse calls). Server half: `App:3775-3850`, `App:9170-9198`, `App:14589-14590`.

**Problem.** Edit file puts the whole of config.txt in a textarea; Use This Text stores it in bootConfig.text and Save sends it as set_boot_config text=, which Core writes to /boot/firmware/config.txt as root (confirmed). The card posts to its own route, where Core splices "cmd" into the body; /api/command reaches the same setter without the revision guard (X-protocol-security-7, confirmed). Around Edit file sit live managed-line marks re-parsed 500 ms after each keystroke, a legend and an own-lines hint: about 800 page lines for the card. The original developer will not accept a root free-text path.

**Apertar way.** The page touches config.txt through one control: `sendCommand({cmd:"set_fan_mode", value})` (U:11093), Core builds the block (App:3042-3178@upstream-1.6.0). Rule WEB-3: actions go through /api/command via sendCommand. Rule WEB-21: system actions confirm with window.confirm. The one upstream text editor is apertar-hardware.conf, a plain textarea with Reload/Save (U:10304-10359).

**Rework.** Page half; the Core half is HW-1 / HW-4 (same as APP-1 / APP-3), one commit.
1. Markup P:5928 and P:5937-5950: delete editBootConfigButton and the whole bootConfigEditField block (gutter, editor, legend, Use This Text, Close).
2. Script: delete BOOT_CONFIG_MANAGED, bootConfigManagedMap, bootConfigManagedSummary, bootConfigOwnLinesHint, showBootConfigEditorMarks, bootConfigEditorEdited, useBootConfigText, closeBootConfigEditor, the Edit branch of toggleBootConfigFile, and the fields text, previewState, editorMarks, editorTimer.
3. bootConfigRequestBody: stop sending text.
4. bootConfigPost becomes `sendCommand({cmd: "set_boot_config", ...flat string fields, dry_run: "true"|"false", revision})` (booleans as "true"/"false", rule WEB-15); delete the fetch to POST /api/boot-config, result.httpStatus and the result.code branches (P:20329); a refusal shows Core's sentence through showToast (rule WEB-14) and re-reads with loadBootConfig.
5. Upload: it parses through POST /api/boot-config/parse, which HW-1 step 4 deletes. Drop Upload with it (recommended), or keep parse as a read-only route and Upload as "fill the card from a file" only.
6. Card copy P:5863: one sentence (rule WEB-23), e.g. "Camera sensors, buses and display in config.txt."; RP1 text only in bootConfigRp1Note.
7. Keep: the controls, the dry-run review as the confirm step, Save and Reboot / Save Only, View file and Download (read-only).

**Depends on.** HW-1, HW-4 (Core half).

**Owner decision.** Same question as HW-1 (asked once there): drop Edit file (recommended) or keep it with a boot-chain deny-list. This item follows that answer; with "keep", steps 1-3 and 5 are skipped and only step 4 and 6 remain.

**Risk.** Removes a feature the owner added (3b87d99); hand edits of config.txt go back to ssh.

**Check here.** C1, C2; C4 with `APERTAR_BOOT_CONFIG=<scratch copy>`: dry run shows the diff, Save writes the scratch file, `grep -n 'api/boot-config' src/web/WebControlPage.cpp` shows only the GET.

**Needs the Pi.** One card save and reboot on a Pi 5 (and a Pi 4 if available), then `sudo cat /boot/firmware/config.txt`.

## WEB-2. Playback renames the original developer's media feature: pb*/pbv* functions, nested state.pb, .pb-* CSS

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| mismatch | major | M | no | fix-now | WCP-06-F1, WCP-02-F3, WCP-01-F8, WCP-02-F10, WCP-06-F9, WCP-06-F11, WCP-06-F12 |

**Where.** `P:6720-6727` (state.pb, 22 keys); `P:11653-12928` (70 pb/pbv functions); CSS `P:68-71`, `P:1979-2016`, `P:2027-2629` (.pb-*, .pbv-*, body.pb-open twice, eight .x.hidden rules); `P:12220-12238` (pbvTimecodeAt, pbvClock); `P:11812`, `P:12209`, `P:12240`, `P:12742`; `P:12138`.

**Problem.** Upstream jobs keep their job and lose their name: renderMediaLibrary -> pbRender, sortedMediaItems -> pbSorted, toggleMediaSelection -> pbToggle, deleteSelectedMediaItems -> pbRemoveSelected and so on, while fetchMediaLibrary, setMediaBrowserOpen and state.mediaBrowserOpen keep theirs. .media-browser-overlay/.media-browser-shell and body.media-browser-open are deleted and re-added as .pb-overlay/.pb-shell/body.pb-open (declared twice); the real change is the shell size. The diff reads as a rewrite of the original developer's feature. Smaller in the same pass: pbvTimecodeAt/pbvClock re-implement formatTimecode and pad2; pbOpenClip only forwards; pbvEls().hist and two tl parameters are unused; state.previewPausedForPlayback is not declared in the state literal.

**Apertar way.** Flat state with a media prefix (U:4233-4246); media functions U:7511-7700, U:10361-10460; classes full-word kebab-case (.media-browser-overlay U:1122, .media-browser-shell U:1142, body.media-browser-open U:66). Rule WEB-12 (one flat state), rule WEB-17 (naming). Every state field is in the literal (previewStreamStarted U:4227). pad2 U:4635, formatTimecode U:4678 (both still at P:7117, P:7160).

**Rework.** Mechanical, no behaviour change; one commit.
1. CSS: restore .media-browser-overlay, .media-browser-shell, body.media-browser-open and change only the shell size in place; name new parts media-browser-* (grid, card, thumb, foot) and clip-viewer-* (stage, scrub, transport); delete P:1979-1982 and the eight .x.hidden rules (global .hidden covers them).
2. Script: restore renderMediaLibrary, sortedMediaItems, selectedMediaItems, toggleMediaSelection, setMediaBrowserFilter, setMediaBrowserSort, downloadSelectedMediaItems, deleteSelectedMediaItems, pruneMediaSelection, selectAllVisibleMedia.
3. Flatten state.pb into flat media* fields beside mediaLibrary/mediaSelection (mediaFetchQueued, mediaSelecting, mediaThumbCache, mediaThumbQueue, mediaThumbsInFlight, mediaHold, mediaError, mediaRemoving, mediaBrowserPage, ...); the viewer may stay one object state.clipViewer, created by createClipViewerState.
4. New functions get verb-first names: buildMediaCard, queueMediaThumbnail, openClipViewer, closeClipViewer, playClip, pauseClip, stepClipFrame, seekClip, fetchClipFrame, drawClipFrame, applyClipHold.
5. pbvTimecodeAt: frames from the start timecode + (number - tl.first), return formatTimecode(frames % (nominal * 86400), nominal); pbvClock uses pad2.
6. Delete pbOpenClip (call the viewer open directly), pbvEls().hist, the unused tl parameters; add previewPausedForPlayback: false next to previewStreamStarted (P:6708).

**Depends on.** Do before WEB-3, WEB-10 and WEB-28 (they edit the same functions).

**Owner decision.** None.

**Risk.** About 1300 lines touched; a missed reference breaks the overlay. C2 and a click-through catch it.

**Check here.** C1, C2; C4: open the browser, filter, sort, select, download, delete, open a clip, step, play; `grep -c 'state\.pb\b\|function pb' WCP` = 0.

**Needs the Pi.** Nothing.

## WEB-3. Playback brings a second widget layer: modal scrim, History API, own buttons, menu, chip, cyan selection

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| mismatch | major | M | yes | fix-now | WCP-02-F1, WCP-03-F1, WCP-06-F2, WCP-05-F5, WCP-06-F8 |

**Where.** CSS `P:2061-2178`, `P:2398-2450`, `P:2657-2678`, `P:2743-2775`; markup `P:6335-6494` (#pbRemoveScrim P:6475-6487, h1.pb-h1); script `P:12036-12118` (pbOpenRemoveDialog), `P:10115-10145`, `P:12777`, `P:12869`, `P:20634-20649` (pushState/popstate, ignorePop), `P:12050-12081` (viewer Remove).

**Problem.** The overlay copies the touch UI's Clip Browser: round .pb-top-button/.pbv-circle buttons, a .pb-menu with a cyan active state, a .pb-chip sort toggle, a .pb-scrim + .pb-dialog modal with focus and Escape handling for one confirm, an h1, and history.pushState so the phone's Back closes it. Upstream has none of these parts; changes to .icon-button or to the white selection no longer reach playback. The port contradicts itself: viewer Download (P:12914) and GPIO replace (P:17317) still use window.confirm. Found in passing: a failed Remove from the viewer closes the viewer although the clip is still there (WCP-06-F8).

**Apertar way.** Buttons .primary/.secondary/.danger-button U:1632-1706, .icon-button U:194-215; selected = white (.media-filter-button.active U:1238-1242); old header icon-button settings-back-button + h2.section-title (U:3979-3995); sort select media-sort-select (U:1244-1253). Rule WEB-21: window.confirm (U:10385, U:10434). No history use upstream (setMediaBrowserOpen U:6139-6147). Rule WEB-19 (white = selected).

**Rework.**
1. Refresh/Show/Back and viewer Info/Download: icon-button or secondary-button with img.icon-image (icons per WEB-20); delete .pb-top-button, .pb-show-*, .pbv-icon-button, .pbv-info-button; size the transport buttons from .icon-button, active white.
2. SHOW menu: a visible row of media-filter-button pills with the white active state; delete .pb-menu*.
3. Newest/Oldest chip: select.settings-select as media-sort-select; delete .pb-chip.
4. Remove: deleteSelectedMediaItems(items) asks `window.confirm("Remove " + label + "? This cannot be undone.")`; viewer Remove calls it with [item] and closes the viewer only when the reply is ok. Delete #pbRemoveScrim markup and CSS (.pb-scrim, .pb-dialog*), pbOpenRemoveDialog, removeTargets, the scrim branch in the Escape handler, the scrim lines at P:10137 and P:20634, the keydown guard.
5. h1.pb-h1 -> h2.section-title.
6. History API: per the owner answer. If kept, it is the one documented new-ground piece: pushState on open, history.back() on close, one popstate listener, its flags in flat state.
7. Keep: grid, card, thumb, stage, scrub, histogram, metadata rules.

**Depends on.** WEB-2, WEB-20.

**Owner decision.** Keep phone Back closing the overlay through the History API (recommended: about 30 lines, a real phone need; cost: the one router-like hook in the page, documented for the original developer), or drop it (cost: Back leaves the page)?

**Risk.** Loses the touch UI's multi-line dialog layout; the text fits in a confirm.

**Check here.** C2; C4 at 420 and 1120 px: select two clips, Remove asks with window.confirm; stop Core during a viewer Remove: toast, viewer stays open; `grep -c 'pb-scrim\|pb-menu\|pb-chip' WCP` = 0.

**Needs the Pi.** Nothing.

## WEB-4. Second 4 Hz poll, second store frameBufferBar, recording pill written outside renderSnapshot

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| mismatch | major | M | yes | fix-now | WCP-08-F1, WCP-08-F2, WCP-08-F3, WCP-08-F4, WCP-10-F10 |

**Where.** `P:16416-16589` (frameBufferBar P:16419, pollFrameBufferBar, applyPrerollPill, applyFrameBufferPillClasses, setInterval P:16432 and again P:16587); `P:15752-15771` (pill block of renderSnapshot); readers `P:14381, 15389, 15757-15759, 15917, 19201`; `App:8418-8426` (/api/buffer).

**Problem.** const frameBufferBar holds 14 fields outside state; a 250 ms loop fetches /api/buffer, writes state.snapshot.storage_preroll_* directly and toggles .preroll/.recording/.writing/.buffer-drain and the status text itself. renderSnapshot writes the same pill at 1 Hz; three 1000 ms freshness guards decide who wins, and the two copies already differ (the render excludes timelapse). The fast poll has a real need: /api/state blocks during a RAM drain, so a safety stop would show late. toggleRecord decides "flushing" from frameBufferBar.safetyStop (P:19199-19204).

**Apertar way.** One store `const state = {` (U:4204), timers as state.<x>Timer (rule WEB-12). One poll `window.setInterval(() => fetchState(true), 1000)` (U:11609, rule WEB-13). Pill classes set only in renderSnapshot (U:9794-9802). Edge toasts from previous-vs-new snapshot, like recording_error (U:9331-9333). No sub-second fetch upstream (startLiveReadoutLoop U:9237 interpolates locally).

**Rework.**
1. Move the fields into state: bufferPollTimer, bufferPollInFlight, bufferPolledAtMs, prerollPollUntilMs, bufferDiscardSeen; delete frameBufferBar.
2. Rename pollFrameBufferBar to fetchBufferState; keep the lock-free route and cache: "no-store".
3. On each reply call applyBufferSnapshotPatch(payload): merge the flat buffer and preroll keys into state.snapshot. The reply's recording goes in as buffer_recording and never over snapshot.recording (/api/buffer reports false during a safety stop, App:8424; Core rename is APP-27).
4. Move the pill block of renderSnapshot (P:15752-15771) into renderRecordingStatus(snapshot); call it from renderSnapshot and from fetchBufferState. Delete applyPrerollPill, applyFrameBufferPillClasses, the READY/PRE-ROLL label rewrites and the three freshness guards.
5. Toasts: compare previous and new buffer_safety_stop / buffer_flush_discarded, as the recording_error toast does.
6. One function startStopBufferPoll(snapshot) decides from the snapshot; the inline setInterval at P:16587 goes.
7. toggleRecord and the 5 other readers read state.snapshot.buffer_* fields.
8. Keep one comment line at fetchBufferState: why it is lock-free. Handoff: the fast poll exists because /api/state takes the camera lock during a drain; a non-blocking /api/state would remove it.

**Depends on.** APP-27 (buffer_recording name in Core), WEB-18.

**Owner decision.** None. The flush-then-record behaviour of toggleRecord (owner decision 2026-11-01) stays.

**Risk.** Rule WEB-24 says do not split renderSnapshot unasked; extracting only the pill block is the smallest split that gives the pill one writer. Safety stop, flush discard and the pre-roll pill must be re-tested on the Pi.

**Check here.** C1, C2; C4: start the pre-roll and a --simulate take, watch the pill change within 250 ms; `grep -c frameBufferBar WCP` = 0; Network panel shows /api/buffer only while recording, draining or within 5 s of the pre-roll button.

**Needs the Pi.** Record 4K into the RAM buffer until the safety stop: pill shows the drain, toast fires once, record during the flush starts a new take. Pre-roll button: PRE-ROLL pill within a second.

## WEB-5. Boot Config card internals: own store and installer, checkbox gate, own diff and select builders

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| mismatch | major | M | no | fix-now | WCP-10-F2, WCP-10-F5, WCP-10-F8 |

**Where.** `P:19872-19884` (const bootConfig); `P:20553-20606` (installBootConfigInteractions, called P:20852); `P:20282-20314` (checkbox gate, syncGate); `P:20225-20317` (bootConfigDiffLine, reviewBootConfig); `P:18854-18887` (showConfigDiff); `P:20038-20044` (bootConfigOption).

**Problem.** A fourth store beside state (same shape as controlsState, frameBufferBar, clipUi), with its own listener installer. A display change is confirmed by a ticked checkbox that enables both Save buttons, a widget found nowhere upstream. The card builds its own diff box and button row a second time next to the config editor's showConfigDiff, and refills selects with innerHTML plus bootConfigOption to get a disabled flag.

**Apertar way.** Rule WEB-12: flat fields on state, <thing>InFlight busy flags (U:4204-4266); all listeners inline in installInteractions (U:11348-11610). Rule WEB-21: `if (!window.confirm("Restart the Apertar system now?"))` (U:11325). Rule WEB-15: no checkboxes; selects through ensureSelectOptions / normalizeSelectEntries / ensureSelectEntries (U:6191, 6210, 6221), disabled choices as enabled:false (normalizeChoiceOptions U:6317).

**Rework.**
1. state gains bootConfigPayload, bootConfigForm, bootConfigFetchInFlight, bootConfigSaveInFlight, bootConfigRebootWaiting, bootConfigReview, bootConfigSavedPendingReboot; delete const bootConfig (text/editor fields go with WEB-1).
2. Move the listeners of installBootConfigInteractions into installInteractions next to restartSystemButton; delete the installer.
3. saveBootConfig: when review.display_changed, `if (!window.confirm("Change the display and reboot? " + <the DPI sentence>)) return;`; delete the checkbox and syncGate; keep the diff-note lines.
4. Add renderDiffBox(boxId, lines, actions) and use it from showConfigDiff and reviewBootConfig; delete bootConfigDiffLine.
5. normalizeSelectEntries accepts enabled; renderBootConfigPort and the display select call ensureSelectEntries; delete bootConfigOption.

**Depends on.** WEB-1.

**Owner decision.** None.

**Check here.** C2; C4 with a scratch APERTAR_BOOT_CONFIG: change the display, Save asks once with window.confirm; Config editor Save still shows its diff; `grep -c 'bootConfig\.' WCP` = 0.

**Needs the Pi.** Nothing beyond WEB-1.

## WEB-6. IMX585 resolution pills read the Mode Ladder reply; mode tables hand-copied in a private string format

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| mismatch | major | M | yes | fix-now | WCP-04-F1, WCP-04-F12, WCP-04-F15, WCP-05-F6, X-state-consistency-3 (WebUI part) |

**Where.** `P:8910-8960` (imx585ClassModes, imx585ClassRows reading state.ladderServer.pool); `P:9021-9032`, `P:9078-9088` (families, alias table); `P:8756-8770` (imx283Bases); `P:8935` and dispatchers `P:9036, 9130, 9236, 9247, 9268, 9281, 9293, 9313` (imx585Selected).

**Problem.** The main Resolution pills, the crop row and imx585BaseCommands take IMX585 sizes from the Mode Ladder pool (filled only by get_mode_ladder), and fall back to a JS copy of Core's class tables. Two features are coupled through a private cache; changing the ladder reply breaks the resolution pills; four sources hold the same facts (Core tables, JS tables, pool, fps_max). The tables are mini string formats ('1920x1080b 3840x2160 ...' split on /[xb]/). The IMX585 family shape (8 pills, 1.85:1 at 2072/1036 with an alias for 2076/1038) depends on the port driver (CAM-1). Dispatch uses an imx585Selected predicate next to inline indexOf for the other sensors.

**Apertar way.** Rule WEB-8: per-sensor option arrays in the page are the one source and copies of Core and QML lists are kept by hand (imx477ResolutionOptions U:5112-5121, IMX585 U:5249-5290). Inline `sensorNameLower(snapshot).indexOf("imx585") !== -1` (U:4890, 4976, 5119, 5171).

**Rework.**
1. imx585ClassRows and imx585LadderFamily: delete the state.ladderServer.pool read; the JS class tables are the source, as upstream.
2. Write the tables as arrays of {width, height, binned} objects or 'WxH' strings with a separate binned list; same for imx283Bases.
3. Next to each table one line naming its Core copy (Imx585Modes.hpp / Imx283Modes.hpp), as CAM-22 asks on the Core side.
4. Aliases (P:9078-9088): follow CAM-1's answer: with the 1.6.0 names restored they go; with the port driver kept they stay and are documented with Core's migratedImx585CropResolution.
5. Replace imx585Selected(snapshot) with the inline indexOf; keep the early returns.
6. get_mode_ladder then serves only the ladder (fetch moves per WEB-7).

**Depends on.** CAM-1 (driver names), CAM-22.

**Owner decision.** None here; the driver question is CAM-1's.

**Risk.** A size the probe refuses is still offered by the page; Core refuses it with its sentence (rule WEB-20), as upstream.

**Check here.** C2; C4 under `--simulate` (whether the simulated sensor can be named imx585 is unconfirmed; else feed a saved imx585 /api/state snapshot to renderSnapshot in the devtools console): Resolution pills render before the Modes panel was ever opened; Network panel shows no get_mode_ladder on page load.

**Needs the Pi.** Nothing.

## WEB-7. Mode Ladder editor re-implements Core's ladder rules in JS, and they already differ

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| new-ground | major | L | yes | ask-owner | WCP-04-F5, WCP-04-F2, WCP-04-F3, WCP-04-F7 (wrong comments) |

**Where.** `P:7628-8480` (about 45 functions); `P:7765-7866`, `P:8047-8086` (ladderArranged, ladderDefaultMax, normalizeLadderDraft, ladderDraftProblem, ladderOrderProblem, ladderSpans, ladderWithMode, 200 ms auto-save); `P:8004-8015` (ladderRequest); `P:8394-8400` (fetch from renderModeLadder); Core `src/camera/ModeLadder.hpp:206-256`, `App:14095-14107`.

**Problem.** The page sorts rungs by quality, invents default maxes (25/33/50/+25), and refuses a draft Core would only warn about ("never used": JS refuses at P:7859-7860, Core warns at ModeLadder.hpp:243). set_mode_ladder dry_run exists in Core but the page never sends it; the first editor (920beb0) showed Core's dry-run messages and that was dropped. The comment at P:7628-7633 still says the editor asks Core (dry_run) and saves with Save ladder; there is no dry run and no Save button. ladderRequest is a second fetch wrapper "because dry runs skip the patch", and renderModeLadder starts a fetch on every poll.

**Apertar way.** No precedent of this size; nearest is the favourites editor (U:7315-7400): list from state, add/remove, one command with a joined string, no client rule engine. Core is the single source of truth (rule WEB-20: page disables, Core refuses). Read-only queries use sendCommand (refreshAudioCaptureCapabilities U:11100-11113). Side data loads on panel open (setSettingsPanel U:6162-6167).

**Rework.**
1. Core (camera editor, ModeLadder.hpp): quality order and the default maxes move into validate/arrange; an empty threshold is filled by place.
2. Page: on each edit send `sendCommand({cmd: "set_mode_ladder", resolutions, dry_run: "true"})` and show Core's errors and warnings per row; the debounced save sends the same without dry_run.
3. Delete ladderArranged, ladderDefaultMax, normalizeLadderDraft, ladderDraftProblem, ladderOrderProblem, ladderSpans, ladderWithMode (about 250 lines); ladderRowStates reads Core's from/ceiling per resolution.
4. fetchModeLadder calls sendCommand({cmd: "get_mode_ladder"}); delete ladderRequest.
5. Fetch from setSettingsPanel("modes") only; the ladder_active-change refetch moves to the fetchState handler, only while the Modes panel is open.
6. Rewrite or delete the comments at P:7628-7633 and P:8665 to match the code.
7. Keep: card, rows, crop picture, pool tiles.

**Depends on.** WEB-6 (pool read gone first); CAM-17, CAM-19 page steps land here too.

**Owner decision.** Move the ladder rules into Core and show its dry-run answer (recommended; cost: an L change across ModeLadder.hpp and about 250 page lines, retest of the approved editor), or keep the JS rules as documented new ground (cost: two rule sets the original developer must change together; they differ already)?

**Risk.** The approved editor behaviour must survive; Core must give the same default maxes the page gave.

**Check here.** C1 with the ModeLadder.hpp change, C2; host test of ModeLadder if one exists in tools/; C4 Modes panel: add a rung, Core's warning shows on the row, reload keeps the order.

**Needs the Pi.** One ladder take on an IMX585 to see the rungs switch at the same thresholds as before.

## WEB-8. Clip-name composer: about 570 lines of drag-and-drop and long-press for one template string

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| new-ground | major | M | yes | ask-owner | WCP-07-F1, WCP-01-F10, WCP-07-F2, WCP-07-F10, WCP-07-F12 |

**Where.** `P:14453-15024` (CLIP_* constants, clipUi, 22 clip* functions); CSS `P:1455-1589` (.clip-row, .clip-ghost z-index 9999, drop markers); `P:14577-14588` (clipRawCommand); `P:14960-14972` (Custom pill). Touch UI twin: Apertar-UI `qml/ClipNameCard.qml` (601 lines), `qml/ClipNamePill.qml`.

**Problem.** HTML5 drag for mouse, Pointer Events long-press with a ghost, setPointerCapture and navigator.vibrate for touch, hit testing, an inline pill editor and a 350 ms debounced save, for one setting changed rarely. State sits in clipUi with UPPER_CASE constants and one-letter fields; a generic raw /api/command wrapper serves one preview command; a Custom pill is forced disabled-but-active by DOM pokes. The touch UI has a second copy with its own drag. Untested by hand (KB drop-frames README:102).

**Apertar way.** No drag anywhere upstream (draggable, dragstart, setPointerCapture, vibrate: 0 hits); highest z-index 100 (U:1994). Ordered lists use Up/Down/Remove buttons (favourites U:7354-7375, moveFavoriteItem U:6505). Choices are buildOptionButtons grids (U:9147-9167); free values settings-input + Apply. Rule WEB-12 (state), rule WEB-17 (camelCase option lists like toggleOptions U:4066), rule WEB-3 (sendCommand; the one raw fetch is purpose-named, U:11503-11515).

**Rework.**
1. Keep presets (buildOptionButtons over clipNamePresetOptions), a token palette that inserts {token} at the caret, and the preview line.
2. Replace the pill row with one settings-input holding the template plus Apply (set_clip_name_template); preview on input via preview_clip_name.
3. Delete clipPointerDrag, clipAttachPill, clipBindRow, clipDropIndex, clipOverRow, clipShowMarker, clipApplyDrop, the text-pill editor, .clip-ghost and the drop-marker CSS (about 570 -> 80 lines).
4. Fields to state.clipName*; constants to clipNamePresetOptions / clipNameTokenGroups in the option-list block near fpsPresets.
5. clipRawCommand -> fetchClipNamePreview(template), sending only preview_clip_name.
6. Drop the Custom pill; setText("settingsClipNamesValue", "Custom") already shows it.
7. Same shape in ClipNameCard.qml (TextField + token buttons), UI editor, same commit series.
8. Tokens removed by REC-30 ({cam}, {model}, {date_}) leave the palette in the same change.

**Depends on.** REC-30 (token list).

**Owner decision.** Replace drag-and-drop by a text field with a token palette in both UIs (recommended; cost: no drag, a typed template), or keep drag as documented new ground with z-index <= 100 (cost: about 1170 lines of drag code across the two UIs)?

**Risk.** The two UIs diverge if only one changes.

**Check here.** C2; C4: pick a preset, insert a token, preview updates, Apply saves, reload shows it; works at 420 px with touch emulation.

**Needs the Pi.** Nothing.

## WEB-9. White dropdowns scoped to the Controls panel by panel and id, dark again for some pin selects

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| mismatch | major | S | yes | ask-owner | WCP-02-F2, WCP-02-F7 |

**Where.** `P:35-36` (--select-bg/--select-fg); `P:3484-3559`; `P:17348` (buildControlsPinSelect adds controls-pin-select); `P:17453` (buildControlsNewRow does not).

**Problem.** `[data-panel="controls"] .settings-select, #hardwareDevices .settings-select` turn one panel's dropdowns white ("like CineMate's web GUI"), then `.controls-pin-select` makes pin selects dark again. One control class has three looks in one panel. A new GPIO row's pin select is white while saved rows are dark, until Save and reload (WCP-02-F7; class names confirmed, render probable).

**Apertar way.** One .settings-select look (U:1519-1555, U:1603-1609); no panel- or id-scoped rule in the upstream sheet. Rule WEB-19: dark zinc look, no light theme.

**Rework.**
1. Delete P:3484-3559 and the two tokens.
2. Drop controls-pin-select from buildControlsPinSelect.
3. If dark selects are hard to read, change .settings-select page-wide in a separate commit offered upstream.

**Owner decision.** Remove the white Controls dropdowns (recommended; cost: they look like every other select), or keep them as a page-wide change to .settings-select proposed to the original developer (cost: a visible change to his whole page)?

**Check here.** C4 Controls panel: every select dark; + Add GPIO button: new row matches saved rows.

**Needs the Pi.** Nothing.

## WEB-10. Media list lost size, fps and frame count, per-row Download/Delete and Clear selection

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| removed | minor | S | yes | fix-now | WCP-02-F8, WCP-03-F3, WCP-06-F4 |

**Where.** `P:2298-2396` (card CSS); `P:6376-6390` (toolbar); `P:11816-11926` (card build); `P:12784-12789` (Info filled for cDNG only); `P:12909-12922` (viewer Download).

**Problem.** Cards show duration, DROP, name, format, date and TC. Size, fps and frames appear only in the viewer Info, which is filled only for cDNG: for ProRes, H.264, MLV, stills and audio the WebUI shows them nowhere. Single Download and Remove exist only inside the viewer; selection starts by an 800 ms long press that a mouse user cannot find, and there is no Clear button. Core still sends size_text and fps_text (App:9276-9280).

**Apertar way.** Per-row stat pills frames/duration/fps/size and Updated time (.media-stat U:1402-1416, built U:7735-7790; mediaFrameCountLabel U:7571, mediaFpsLabel U:7584); per-row Download/Delete (U:7765-7790); Select All / Clear / Download Selected / Delete Selected always visible (U:4020-4022).

**Rework.**
1. Card foot: add size_text and mediaFpsLabel(item) on one line under the format label.
2. Viewer Info for non-cDNG items: fill size, fps, frames from the /api/media item.
3. Toolbar: a visible Select button next to the sort select that sets mediaSelecting, and a Clear button while selecting; long press stays as a shortcut.
4. Handoff: single-item Download and Remove moved into the viewer.

**Depends on.** WEB-2, WEB-3.

**Owner decision.** None (per-row buttons stay in the viewer; only the facts and a visible Select/Clear come back).

**Check here.** C4 with a --simulate media folder holding a ProRes or H.264 file: card shows size and fps; Select and Clear work with a mouse.

**Needs the Pi.** Nothing.

## WEB-11. Record button greyed without media; Core's reason never shown; "has media" decided by two fields

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| removed | minor | S | yes | fix-now | WCP-07-F6, WCP-05-F8 |

**Where.** `P:15772-15773` (recordButton.disabled with !hasMedia); `P:10891`, `P:15253-15255` (hasMedia = media_alive ?? media_mounted, twice); `P:19218, 19232, 19244` (toggleRecord guards on media_mounted); `App:11359` (mediaGateError).

**Problem.** The record button is disabled without usable media, so the operator gets a grey button and no reason; Core's mediaGateError() sentence never reaches him. toggleRecord still tests media_mounted while the button follows media_alive. The `!== undefined` fallback is dead: Core always sends both fields.

**Apertar way.** The button stays live; toggleRecord answers 'No media mounted.' (U:10709-10712, U:10723-10726, U:10735-10738); recordButton.disabled only for writes pending, photo, command in flight (U:9805-9806). `const hasMedia = !!(snapshot && snapshot.media_mounted);` (U:6766, U:9358). Rule WEB-20.

**Rework.**
1. Core (core-app editor, same commit): state field media_gate_error = mediaGateError(), empty when usable.
2. renderSnapshot: drop !hasMedia from recordButton.disabled.
3. Both hasMedia lines: `const hasMedia = !!(snapshot && snapshot.media_alive);`.
4. toggleRecord guards use the same test and toast `snapshot.media_gate_error || "No media mounted."`.

**Owner decision.** None.

**Check here.** C3 shows media_gate_error; C4 with the media folder removed: button live, press shows Core's sentence.

**Needs the Pi.** Pull the card: press Record, the toast names the reason.

## WEB-12. ISO and WB badges no longer say Auto

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| removed | minor | S | yes | ask-owner | WCP-07-F5 |

**Where.** `P:15398-15406`, `P:15507`; comment `P:15398`.

**Problem.** In auto the badges read 'ISO ' + iso_actual and kelvin + 'K', so ISO Auto at 800 and manual ISO 800 look the same on the badge and in the settings summary. The comment says "green whenever the camera set it"; the code keeps Auto white. The owner tested the current form ("works well", e25fd2b).

**Apertar way.** `setText("isoBadge", snapshot.iso_auto ? "ISO Auto" : ("ISO " + isoLabel))`, WB with 'Auto' (U:9494-9496).

**Rework.**
1. isoBadge: snapshot.iso_auto ? "ISO Auto " + isoInUse : "ISO " + isoLabel (fallback "ISO Auto" when iso_actual is 0); WB likewise "WB Auto " + kelvin + "K".
2. Fix the comment at P:15398 or delete it.

**Owner decision.** Add the word Auto back in front of the live value (recommended; cost: a slightly longer badge), or keep value-only badges and tell the original developer (cost: auto and manual look the same)?

**Check here.** C4: ISO Auto shows "ISO Auto 800"; manual shows "ISO 800".

**Needs the Pi.** Nothing.

## WEB-13. Timecode: upstream labels renamed, the favourite split in two, the card lost its value pill

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| removed | minor | S | yes | ask-owner | WCP-05-F2, WCP-05-F3, WCP-03-F14 |

**Where.** `P:9796-9827` (timecodeDisplayName, timecodeChoices); `P:11176-11182` (two favourite blocks); `P:5080-5094` (card without settingsTimecodeValue); Core `App:13284-13294` (target=); touch UI `qml/SettingsPage.qml:20,1218-1220`.

**Problem.** Stored values stay 'Free Run' / 'Rec Run' but every label in both UIs reads 'Time of Day' / 'Clip' (Core 2c259b9, UI 08cefcf). set_timecode_mode gained target=ui|files|both (additive, old default kept: conforms); the quick-access favourite now shows two blocks to every operator, and the card lost its current-value pill. The touch-UI side (X-stock-behaviour-8: the tap no longer changes the files' timecode) is the UI editor's.

**Apertar way.** timecodeModeLabel returns 'Rec Run' / 'Free Run' (U:5852, favourite U:7042); touch UI the same (ui-upstream CameraPage.qml:1693-1710). One 'Timecode Mode' favourite. Card head shows the value: `<div class="online-pill" id="settingsTimecodeValue">Free Run</div>` (U:3016).

**Rework.**
1. timecodeDisplayName returns the stored words; hold back Core 2c259b9 and UI 08cefcf from the merge and offer the rename as its own proposal.
2. Favourite: one 'Timecode Mode' block sending target=both, value text from timecodeSummaryLabel so a split state stays visible.
3. Card: add online-pill#settingsTimecodeValue with timecodeSummaryLabel.
4. Keep target= in Core and the two rows on the Timecode card.

**Owner decision.** Restore Free Run / Rec Run in the merge and propose the rename separately (recommended; cost: the owner's clearer names wait for the original developer), or ship the rename (cost: labels the original developer did not choose change in both UIs)?

**Check here.** C4: card and favourite read Free Run / Rec Run; favourite sends target=both (Network panel).

**Needs the Pi.** Nothing.

## WEB-14. ISO Auto offered by the page's own rule wherever Clear HDR is off

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| stock | minor | S | yes | fix-now | X-stock-behaviour-10 (WebUI half) |

**Where.** `P:8660-8668` (availableIsoOptionsForSnapshot: `const autoAllowed = !(snapshot && snapshot.clear_hdr);`).

**Problem.** The page offers Auto in every lossless mode on every sensor; Core keeps auto ISO only in IMX585 lossless and silently undoes it on the IMX477. The operator taps Auto and the camera stays manual. The page decides by its own rule instead of Core's.

**Apertar way.** Rule WEB-20: Core enforces, the page only disables matching controls. 1.6.0 forced manual ISO in lossless on every sensor (CC:2484@upstream-1.6.0).

**Rework.**
1. Core publishes iso_auto_allowed from the sanitiser's own rule (CAM-14 / REC-4 step 5).
2. availableIsoOptionsForSnapshot: `const autoAllowed = snapshot && snapshot.iso_auto_allowed === true;`; Auto is shown disabled ({value: "Auto", enabled: false}) when false (rule WEB-19: unavailable choices disabled).
3. Same change in the touch UI (UI editor).

**Depends on.** CAM-14, REC-4.

**Owner decision.** None here (the Core rule is CAM-14's question).

**Check here.** C3 shows iso_auto_allowed; C4 with an imx477 --simulate config in lossless: Auto pill disabled.

**Needs the Pi.** Nothing.

## WEB-15. Loading a preset from the WebUI library drops frameBufferBarEnabled

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| bug | minor | S | no | fix-now | X-state-consistency-6 |

**Where.** `P:19028-19112` (buildPresetApplyPayload allow-list; P:19109); Core writer `App:7787`, reader `App:14454`.

**Problem.** d44b177 added frameBufferBarEnabled to Core's preset writer and reader and the touch UI uses it, but the page's allow-list lacks it (`grep frameBufferBarEnabled WCP` = 0 hits, confirmed). A preset loaded from the WebUI library leaves the buffer bar as it was; the same preset loaded on the touch screen restores it. Every other missing key is missing upstream too.

**Apertar way.** The allow-list mirrors Core's preset keys (U preset import list; the port appended 17 keys in the same loop, P:19080-19121, which conforms).

**Rework.** Add "frameBufferBarEnabled" next to "recordingFrameEnabled" at P:19109. cameraPreviewTdn joins the list only if APP-47 makes it a preset field.

**Owner decision.** None.

**Check here.** C4: save a preset with the bar on, switch it off, load the preset from the WebUI: bar on.

**Needs the Pi.** Nothing.

## WEB-16. APERTAR_* names and *_env greying in operator text; pre-roll switch not shaped like an upstream toggle

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| mismatch | minor | S | unknown | fix-now | WCP-07-F7, WCP-07-F8, WCP-06-F10 (env field), WCP-03-F12 (env-name part) |

**Where.** `P:5818`, `P:15827-15855`, `P:16183`, `P:16210`, `P:13845-13856`; Core `App:262-268`.

**Problem.** Operator text says 'Set by APERTAR_STORAGE_PREROLL', 'Forced off by APERTAR_MEDIA_TRIM=0.', 'Forced off by APERTAR_CLIP_MERGE=0.', 'Set by APERTAR_CDNG_FRAMES_PER_FOLDER'; four *_env state fields grey the controls. The pre-roll auto switch is built as ['On','Off'] (reversed), sends value on/off instead of enabled, greys by a DOM loop and hides with .hidden =; the port's own set_media_trim switch next to it already has the upstream shape.

**Apertar way.** Upstream Core has 35 APERTAR_* getenv knobs and the page shows none: developer overrides, never surfaced. On/Off: `buildOptionButtons(id, toggleOptions, formatToggleLabel(b), ...)` sending `enabled: "true"|"false"` (U:10109-10115, U:4066); unavailable choices {enabled:false} (U:9950-9954). Rule WEB-15.

**Rework.**
1. Core: APP-9 drops the four env overrides and the *_env fields.
2. Page: delete the _env reads, notes and disable logic, and the storage_preroll_auto_env copy in mergeCameraStateFields.
3. Pre-roll: `buildOptionButtons("storagePrerollAutoOptions", toggleOptions, formatToggleLabel(auto), async (v) => { try { await sendCommand({cmd: "set_storage_preroll", enabled: v === "On" ? "true" : "false"}); } catch (error) { showToast(error.message, true); } })`; Core reads enabled (keep value as an alias only if the touch UI sends it); hide rows with classList.toggle("hidden").

**Depends on.** APP-9.

**Owner decision.** None.

**Check here.** C3: no *_env fields; C4: `grep -c 'APERTAR_' WCP` = 0; pre-roll switch reads Off | On.

**Needs the Pi.** Nothing.

## WEB-17. Page parses Core's display text: write speed, buffer note; Log reason hard-coded for IMX585

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| protocol | minor | S | no | fix-now | WCP-04-F10, WCP-07-F4, WCP-07-F9 |

**Where.** `P:7945-7949` (`/^([0-9.]+) MB\/s$/.exec(system.write_speed_result_text)`); `P:15467-15480` (buffer_note regex; 60 %, 12 frames, 90 % fixed); `P:15456-15457` (Log 'Not applied' text); Core `App:9349`, `src/util/BufferBudget.hpp:33,341`, `CC:12511-12514`.

**Problem.** The card-speed warning reads a number out of Core's display text (0 during 'Testing...', gone after a rewording). The buffer info parses a log-style note and states fixed numbers although the fraction, queue depth and stop percent are configurable. The Log note always blames IMX585 SDR compression, also in --simulate, without a capture session, or on another sensor.

**Apertar way.** Rule WEB-13: render reads data fields from the snapshot; Core words reasons (errorReply sentences). State carries scalars the page formats (media_free_bytes, record_time_left_minutes in /api/state@upstream-1.6.0).

**Rework.**
1. Core (core-app editor): write_speed_mbps (from mediaSpeedLastWriteSpeedMBps) in system state; buffer_ram_budget_mib, buffer_ram_frames, buffer_frame_mib, buffer_queue_frames, buffer_ram_percent, buffer_stop_percent_setting in bufferSettingMembers; cdng_log_reason (short sentence, empty when applied) beside cdng_log_applied.
2. Page: read write_speed_mbps; format the buffer numbers; show cdng_log_reason; delete both regexes and the fixed numbers.

**Depends on.** WEB-18 (same member list).

**Owner decision.** None.

**Check here.** C3 shows the new scalars; C4: buffer info shows the configured fraction after changing it in the hardware file.

**Needs the Pi.** Nothing.

## WEB-18. Buffer and pre-roll settings published twice by Core; renderSnapshot copies system.* to the top level

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| protocol | minor | S | unknown | fix-now | WCP-07-F3 |

**Where.** `P:15215-15222` (copy loop over Object.keys(snapshot.system)); `P:13841-13860`, `P:14027-14032`; Core `App:252-269`, `App:301-311`, `App:9587`.

**Problem.** bufferSettingMembers() is flat in settingsBody and the settings event, and nested under system in /api/state through bufferMembers (confirmed App:309, App:393, App:9587). renderSnapshot copies buffer_*/storage_preroll_* from system to the top level, so render changes the snapshot shape; the same slice reads clip_merge_* and frames_per_folder from system directly.

**Apertar way.** Settings are top-level snapshot fields (settingsBody); system is telemetry read as `const systemState = snapshot.system || {}` (U:9378); upstream never writes into snapshot.system.

**Rework.**
1. Core: /api/state emits bufferSettingMembers() at the top level beside the other settings; bufferMembers keeps only the gauge (buffer_used, buffer_capacity, buffer_fill, buffer_mode, buffer_unit).
2. Page: delete the copy loop; read frames_per_folder* and clip_merge_* from the top level.

**Owner decision.** None.

**Check here.** C3 before/after: buffer_* settings appear once, at the top level; C4 buffer cards unchanged.

**Needs the Pi.** Nothing.

## WEB-19. Mode Ladder lock wired into the two generic pill builders; two lock mechanisms

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| mismatch | minor | S | yes | fix-now | WCP-04-F4, WCP-05-F1 |

**Where.** `P:10446-10447`, `P:10718-10735` (createFavoritePillGrid / normalizeChoiceOptions); `P:15029-15053` (buildOptionButtonsInto); `P:8478-8480`; callers `P:11144, 11158, 11161, 11166, 15929, 15978, 15990`; select delegate `P:20684-20690`.

**Problem.** Options gain `locked`; both generic builders keep locked pills enabled and call the feature toast showLadderLockWarning(false) themselves. Selects use a second mechanism (data-ladder-lock plus a document click delegate). The favourites Bit Depth block is greyed through bitDepthBlock.lastChild.

**Apertar way.** The builders are generic: `button.disabled = !option.enabled;` (createPillGrid U:6608, buildOptionButtons U:9158). The caller gives the refusal: Sound Recorder `if (!audioOptions.hasInputDevices) { showToast("No audio input device detected.", true); return; }` (U:6992-6995).

**Rework.**
1. Rename locked to a generic `blocked` (looks disabled, stays clickable): both builders add the disabled class, keep the button enabled, call onSelect.
2. Ladder-locked callers (Resolution and Crop P:15978/15990, favourites Bit Depth P:11161) start onSelect with `if (state.snapshot && state.snapshot.ladder_active === true) { showLadderLockWarning(false); return; }`.
3. Selects keep the one data-ladder-lock delegate.
4. Pass the ladder-locked class through createFavoriteSelectBlock instead of bitDepthBlock.lastChild.

**Owner decision.** None (the greyed-but-clickable behaviour stays).

**Check here.** C2; C4 with ladder_active true: tapping a greyed Resolution pill shows the warning; other disabled pills stay silent.

**Needs the Pi.** Nothing.

## WEB-20. Inline SVG icons (13 places) where the page uses /icons PNGs

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| mismatch | minor | S | unknown | fix-now | WCP-04-F9, WCP-03-F1 (SVG part) |

**Where.** `P:7644-7650` (ladderIcons, innerHTML); `P:4733`; `P:6351-6455` (playback overlay, 6 inline svg); one built in JS near `P:11833`. 13 `<svg` in the port page, 0 upstream.

**Problem.** A second icon mechanism in one page; SVG strings go in through innerHTML.

**Apertar way.** Rule WEB-9: PNG icons from src/web/icons via GET /icons/<name> (`<img class="icon-image" src="/icons/folder.png" alt="">` U:2448; CSS url('/icons/camera.png') U:616); reuse the touch UI's icon names (refresh, previous, next, play, delete, film exist). Rule WEB-16: innerHTML only to clear.

**Rework.**
1. Playback: img.icon-image with the existing /icons PNGs.
2. Ladder chevron/down: a PNG from the touch UI set, or a text glyph as the chips already use; delete ladderIcons.
3. Any icon missing from src/web/icons is copied from Apertar-UI's icon folder under the same name and added to the /icons route list (App:7124-7151@upstream-1.6.0 pattern).

**Owner decision.** None.

**Check here.** C1 (route list), C4: icons render; `grep -c '<svg' WCP` = 0.

**Needs the Pi.** Nothing.

## WEB-21. Hiding by the hidden attribute with [hidden] patches; attribute and id selectors in CSS

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| mismatch | minor | S | no | fix-now | WCP-03-F5, WCP-02-F5 |

**Where.** Markup `P:5769-5827`, `P:5868-5936`, `P:6147-6229` (17 elements with `hidden`); 26 `.hidden =` script sites; CSS `P:3137, 3184-3185, 3266, 3364, 3420, 3542, 3575, 3978`; `P:5932` (inline style="display:none").

**Problem.** Two hiding mechanisms: five `[hidden]` rules exist only to beat display:flex, so each new class with a display rule needs its own patch. CSS also keys on [data-panel], [data-used], [data-output], [data-ladder-lock], #hardwareDevices and #remoteControlsRows where upstream uses classes only.

**Apertar way.** `.hidden { display: none !important; }` (U:1975), toggled with classList; the one `.hidden =` upstream is on an <option> (U:9526). 0 attribute and 0 id selectors in U:15-2420. Rule WEB-19, rule WEB-17.

**Rework.**
1. class="... hidden" on the 17 elements; classList.toggle("hidden", ...) at the 26 sites; delete the five [hidden] rules.
2. [data-output] -> class output; [data-used] -> option class used; #remoteControlsRows .pill-button -> class remote-pill; [data-ladder-lock] -> class ladder-locked; [data-panel]/#hardwareDevices scoping goes with WEB-9.
3. The upload input: class hidden instead of the inline style.

**Owner decision.** None.

**Check here.** C2; C4: every card that showed or hid before still does (Boot Config message, Controls rows, playback pages); `grep -c '\[hidden\]' WCP` = 0.

**Needs the Pi.** Nothing.

## WEB-22. Cards filed under the wrong topic: indicators in Live preview, a Performance card in System, Value Lists in Controls

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| mismatch | minor | S | no | fix-now | WCP-03-F7, WCP-03-F9, WCP-03-F10 (placement part) |

**Where.** `P:5274-5291` (four switches in Live preview); `P:5781-5830` (Performance card: preview_tdn, fps_phase_lock, media trim, frames_per_folder, clip_merge); `P:10093-10101` (arrangeSettingsPanels); `P:6137`, `P:6163-6170` (Value Lists at the end of Controls).

**Problem.** Recording frame, buffer bar, red timecode and audio outline switches sit in the Live preview read-out card ('Current preview transport and monitoring endpoint for the web feed.'). One System card mixes camera_settings.conf switches with [storage] keys, so media settings split across two panels. Value Lists (FPS/ISO/shutter/WB lists) sit under Controls ('What each button, knob and pin does.') without a copy sentence.

**Apertar way.** Overlays are select-blocks in Assist tools ('Manage monitoring overlays and assist modes.', U:3180-3215). Panels by topic; arrangeSettingsPanels moves media cards into the Media panel (U:6119-6128). Rule WEB-2, rule WEB-23 (every card an h3 and one copy sentence).

**Rework.**
1. Move the four switches into Assist tools as one settings-option-group of four select-blocks.
2. Preview TDN -> Live preview / Monitoring; FPS phase lock -> Record; Trim, Frames per folder, Merge -> a recording-media card added to moveSettingsCards(mediaPanel, ...); delete the Performance card.
3. Value Lists -> the Record panel (or Modes) with one copy sentence.

**Owner decision.** None.

**Check here.** C4: each switch is found by settings search under its new card; toggles still send the same commands.

**Needs the Pi.** Nothing.

## WEB-23. On/Off switches from new classes (.switch-field, .ladder-pair); a label wraps the Log pills

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| mismatch | minor | S | no | fix-now | WCP-01-F2, WCP-01-F3, WCP-03-F6, WCP-03-F13 |

**Where.** CSS `P:860-876` (.switch-field, .settings-card-head.wrap-head), `P:1184-1186` (.pill-grid.ladder-pair); markup `P:4980-4990` (Speed Ramp head), `P:5087-5094` (Timecode grids), `P:5171-5176` (ladder Off/On); `P:4913-4917` (label around #settingsCdngLogOptions).

**Problem.** A grid class named after the Mode Ladder became the general switch (Speed Ramp, UI timecode, file timecode, ladder Off/On), and an upstream card (Timecode) changed its look through it. Speed Ramp puts 'Allow speed ramping' and its pills in the card head through .switch-field. A <label> without `for` wraps the Log pill grid: a click on 'Log' or its note presses the first pill (probable, not run). Upstream has the same label shape once (Timelapse U:2828-2831), so the defect is shared.

**Apertar way.** Gyro Data card: head = title, copy, online-pill#settingsGyroDataValue; pill-grid below the head (U:2939-2948). Two-state switch = field-stack + input-label + pill-grid two-col (U:2805-2813; .two-col U:759). Rule WEB-15.

**Rework.**
1. Speed Ramp head: title + copy + note + online-pill#settingsSpeedRampValue (render sets it as for Gyro); below, field-stack with `<span class="input-label">Allow speed ramping</span>` and pill-grid two-col#settingsSpeedRampOptions (keeps the label and Off/On of UI-DESIGN.md:71).
2. ladder-pair -> two-col on the two Timecode grids and the ladder Off/On grid; delete .pill-grid.ladder-pair, .switch-field, .settings-card-head.wrap-head*.
3. P:4913: `<label class="field-stack field-span-2">` -> `<div class="field-stack field-span-2">`. The upstream Timelapse label can take the same fix in a separate upstream-candidate commit.

**Owner decision.** None.

**Check here.** C4: click the 'Log' label text: no pill changes; Speed Ramp and Timecode switches look like Gyro Data at 420 px.

**Needs the Pi.** Nothing.

## WEB-24. Config editor Check goes through set_controls with a fake "h" revision; Save diff step kept

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| mismatch | minor | S | no | fix-now | WCP-10-F7, WCP-10-F12 |

**Where.** `P:18795` (`controlsCall({ cmd: "set_controls", base: state.configRevision || "h", text, dry_run: "true", ... })`, confirmed); `P:18918-18927` (Save: POST /api/config with X-Apertar-Revision); `P:18854-18887` (showConfigDiff); `P:20884`.

**Problem.** Check and Save reach the same HardwareConfigStore::replace through two transports. "h" is not a revision (an absent file is h0000000000000000, HardwareConfigText.hpp:315) and the store compares base even on a dry run, so Check before the file has loaded always answers stale. Save now shows a line diff first and needs a second click: a small, useful change to upstream behaviour (8be1ab5).

**Apertar way.** One path per file: GET/POST /api/config (App:7168/7175@upstream-1.6.0); route options from the query string via queryParameterValue (rule WEB-5); saveConfigButton -> saveConfigFile in one click (U:11556, U:10330).

**Rework.**
1. With HW-19 step 2: Check posts to /api/config?dry_run=1 with the same header and body as Save; Core reads the flag with queryParameterValue.
2. Disable Check until state.configRevision is set; delete the "h" fallback.
3. Keep the diff before Save; render it through renderDiffBox (WEB-5 step 4). Handoff: Save asks for a second click after showing the diff.

**Depends on.** HW-19, WEB-5.

**Owner decision.** None.

**Check here.** C4: open Config, press Check at once: disabled until loaded, then answers; Save shows the diff, second click writes.

**Needs the Pi.** Nothing.

## WEB-25. Settings search: MutationObserver and elements inserted at runtime

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| new-ground | minor | M | yes | fix-later | WCP-05-F4, WCP-01-F12, WCP-01-F11 (duplicate .settings-search-empty) |

**Where.** `P:10183-10289` (settingsSearch, applySettingsSearch, observer at P:10272-10279); CSS `P:1814-1869` (P:1862 and P:1865-1869 declare .settings-search-empty twice).

**Problem.** The search inserts a label per panel and #settingsSearchEmpty at runtime, and while a query is active a MutationObserver on .settings-panels re-runs the filter 250 ms after any change. The observer is a refresh path the original developer will not expect next to renderSnapshot; elements that exist only after a search are not in the HTML string. The class-only hiding (.search-hidden separate from .hidden) is correct and stays.

**Apertar way.** No search upstream; no Mutation/Intersection/Resize observer (0 hits); one refresh path renderSnapshot (U:9327); static elements in the HTML string (rule WEB-1).

**Rework.**
1. Put the per-panel label and #settingsSearchEmpty in the static HTML with class hidden.
2. Drop the observer; call `if (settingsSearch.active) applySettingsSearch();` at the end of renderSnapshot and after the async card loaders in setSettingsPanel.
3. Move the fields into state (settingsSearchActive, settingsSearchTimer).
4. Merge the two .settings-search-empty rules.
5. Handoff: document the search as new ground (data-search keywords per card); its own commit, out of squash d44b177.

**Owner decision.** None.

**Risk.** Cards rebuilt outside renderSnapshot need the explicit re-filter call.

**Check here.** C4: search 'buffer', open Controls while searching: results stay filtered; 420-560 px layout.

**Needs the Pi.** Nothing.

## WEB-26. Parallel CSS vocabulary: ladder buttons and tile re-create upstream ones; four chip classes

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| duplication | minor | M | no | fix-later | WCP-01-F4, WCP-01-F6 |

**Where.** `P:883-893` (.ladder-add, .ladder-add.remove), `P:1236-1245`, `P:1275-1312` (.ladder-box), `P:8361`, `P:8370`; chips `P:1416-1453` (.value-chip), `P:1476-1535` (.clip-pill), `P:2167` (.pb-chip), `P:3208` (.action-chip).

**Problem.** Activate/Deactivate are a new white-fill and red-outline button pair; .ladder-box has exactly the .preset-row values. Four chip classes draw one chip and one remove button with small differences. A later change to the upstream buttons or tiles does not reach these.

**Apertar way.** primary-button / danger-button with size modifier .preset-action (U:1632-1706, U:1932); tile .preset-row (U:1887-1896). One class per component, variants by extra class (.pill-button + .active/.disabled U:763-803).

**Rework.**
1. Activate = primary-button preset-action; Deactivate = danger-button preset-action; delete .ladder-add*.
2. .ladder-box -> preset-row; keep .ladder-row / .ladder-pool-item only for the badge and crop frame.
3. One .chip base and .chip-remove; .chip.token / .text / .sep / .flicker-free as modifiers; drag-only properties on the composer modifier (or gone with WEB-8). .pb-chip goes with WEB-3.

**Depends on.** WEB-3, WEB-8.

**Owner decision.** None.

**Risk.** preset-action min-width 108 vs 72: check the tile at 420 px.

**Check here.** C4 at 420 px: ladder tile and value-list chips look as before.

**Needs the Pi.** Nothing.

## WEB-27. Stylesheet order and breakpoints: 741 lines inside the pill-button group, media queries at 1119/719/419

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| mismatch | minor | S | unknown | fix-later | WCP-01-F7, WCP-02-F4, WCP-01-F11 (one-line rules, colour literals, mono stack) |

**Where.** `P:850-1590` (ladder, value-list, clip-name CSS between .pill-button.active P:843 and .pill-button.disabled P:1591); `P:1371-1380` (second 560 px block); `P:1632` (.online-pill variants before the base); `P:2452, 2458, 2499, 2865, 2879, 2894, 2929, 3439, 3569` (nine component-side media blocks); `P:1838-1869`, `P:1509`, `P:1578`, `P:917-918`.

**Problem.** A reader of the pill states finds 741 lines of unrelated card CSS in between; responsive rules are no longer in one place. The playback blocks use 1119/719/419 and min-width 1120, so at exactly 720/1120/420 px the settings overlay and the playback overlay take different layouts. Some rules are one-liners, colours #fbbf24 (x6), #f59e0b, #90ee90 are literals, and a third monospace stack appears.

**Apertar way.** .pill-button rules together (U:763-803); one block per breakpoint at the end, max-width only: 1120 (U:2034), 720 (U:2062), 480 (U:2190), 560 (U:2319), 420 (U:2391). Multi-line rules; shared colours as :root tokens (U:16-42); mono stacks U:526, U:1567. Rule WEB-19.

**Rework.**
1. Keep .pill-button.* together; move the ladder, value-list and clip-name blocks after .preset-row; move .online-pill variants after the base rule.
2. Move the component media rules into the end blocks (1119 -> 1120, 719 -> 720, 419 -> 420); write min-width 1120 rules as the base and undo them in the 1120 block; Controls 720 rules into the 720 block; keep the landscape block as one block at the end.
3. Multi-line rules; the crop and amber colours (UI-DESIGN.md:88-90) as :root tokens; reuse U:1567's mono stack.

**Owner decision.** None.

**Check here.** C4 at 419, 420, 719, 720, 1119, 1120 px: settings and playback overlays switch layout at the same widths.

**Needs the Pi.** Nothing.

## WEB-28. Clip viewer: stale badges on non-cDNG items, blank after a hold, freeze on a short WAV

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| bug | minor | S | no | fix-later | WCP-06-F5, WCP-06-F6, WCP-06-F7 |

**Where.** `P:12766-12797` (pbvOpen non-cDNG branch); `P:12795-12798`, `P:12875-12886`, `P:12021-12033` (hold); `P:12545-12575`, `P:12189` (pbvTick audio clock).

**Problem.** (a) Next from a cDNG clip with drops onto a ProRes clip keeps DROP N, the fps badge, time, TC and metadata rows of the previous clip. (b) A clip opened during a take gets a 409 hold; when the take ends the stage stays black and Play does nothing until Back and reopen. (c) With sound on, when the WAV ends before the frame span the picture stands while the badge says PLAYING (probable).

**Apertar way.** No precedent (viewer is new).

**Rework.** Function names per WEB-2.
1. openClipViewer: before the format branch clear the fps, time and TC text, hide the drop badge, clear the metadata grid (or fill it per WEB-10).
2. applyClipHold(""): `if (wasHeld && !viewer.timeline) void reloadClipViewer();`.
3. Clip tick: when audio.ended in the waiting branch, switch to the wall clock from the current time (audio off, clock base = t, clock start = now) and turn audio back on at the loop.

**Depends on.** WEB-2.

**Owner decision.** None.

**Check here.** C4 with a --simulate media folder holding one cDNG and one ProRes item: Next clears the badges.

**Needs the Pi.** (b) start a take from the touch UI, open a clip in the WebUI, stop: picture appears. (c) a take whose WAV is shorter than the frames.

## WEB-29. Crop picture and ladder names assume the IMX585 3840x2160 readout on every sensor

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| bug | minor | M | no | fix-later | WCP-01-F9, WCP-04-F6 |

**Where.** `P:912-930` (.crop-frame fixed 78x44/160x90/64x36); `P:7642` (`const ladderCropArea = { width: 3840, height: 2160 }`); `P:7686`, `P:7696-7710`, `P:7903-7924`.

**Problem.** Every window is clamped into a 16:9 3840x2160 area. On the IMX283 (5472x3648, 3:2) the 3840x2160 crop shows 'Whole sensor area, no crop', the 5.5K window is clipped, and non-IMX585 names call any 3840-wide mode '4K SDR' and any 1920-wide '2K SDR binned'. Same for IMX477 4056. Probable (read from code); 16:9 was chosen for the IMX585 (6707b08) and not revisited when IMX283 arrived.

**Apertar way.** Geometry passes from script through a custom property: --preview-aspect-ratio (U:266, set U:5447).

**Rework.**
1. Readout area = the largest window_w/window_h in the get_mode_ladder pool (or a sensor field Core publishes).
2. Set --crop-aspect on the frame and use aspect-ratio instead of the fixed heights; delete ladderCropArea.
3. Keep the IMX585 rule of UI-DESIGN.md:92 (3840x2200 drawn as 3840x2160).
4. Non-IMX585 names: by size ('3840x2160 10-bit').

**Owner decision.** None.

**Check here.** C4 with an imx283 --simulate config (if smoke_core.sh's sim supports it): the 3840x2160 crop draws as a crop.

**Needs the Pi.** get_mode_ladder on an IMX283 to confirm the pool windows.

## WEB-30. Exact shutter angle leaves no pill active (60 fps at 22.5 deg)

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| bug | minor | S | no | fix-later | WCP-03-F4 |

**Where.** `P:7172-7181` (formatAngle -> toFixed(2), confirmed); `P:7605-7621`; `P:15284-15286`.

**Problem.** 22.5 deg at 60 fps becomes 1042 us, shown as 22.51 deg; pills compare labels by string, so none is active. 15 deg at 60 fps shows 14.99 deg. Probable (assumes Core echoes the sent us).

**Apertar way.** The shown angle snapped to the nearest shutterOptions label (U:4690).

**Rework.** formatAngle: return the label of a list entry within 0.05 deg (the tolerance already used at P:7612), else the exact value. Keep the exact value for flicker-free angles (86.4, 172.8) as ff33d2d intends; delete the two-line comment or keep one line.

**Owner decision.** None.

**Check here.** C4: 60 fps, tap 22.5 deg: the pill stays active.

**Needs the Pi.** Nothing.

## WEB-31. Boot Config reboot wait polls /api/buffer and misreports a slow shutdown

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| bug | minor | S | no | fix-later | WCP-10-F6 |

**Where.** `P:20355-20403` (waitForCameraAfterReboot, rebootForBootConfig).

**Problem.** The wait fetches /api/buffer (a port route) every 2.5 s; if no fetch fails within 60 s it says 'The camera kept answering, so it did not reboot.' and stops. Core stops the camera before the web server (App:8185-8190), so a take that drains for more than 60 s gives the false message, then the reboot happens anyway. Probable.

**Apertar way.** requestRestartSystem sends restart_system and toasts 'Restart requested.' (U:11324-11334); reconnection is the 1 s fetchState poll and the loading overlay (rule WEB-13, WEB-22).

**Rework.** Poll /api/state (or watch fetchState's success after a failure); drop the never-down branch (the restart_system reply already confirms the request); bootConfigSleep goes with it.

**Depends on.** WEB-5.

**Owner decision.** None.

**Check here.** C4: Save and Reboot against --simulate (restart_system refused or stubbed): the card waits and does not claim 'did not reboot' after 60 s.

**Needs the Pi.** Record 4K, fill the buffer, Save and Reboot: one message, correct.

## WEB-32. FPS caps re-applied in JS on top of Core's fps_max; an empty if-branch

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| duplication | minor | S | no | fix-later | X-state-consistency-5 (WCP part), WCP-04-F13 |

**Where.** `P:7480-7512` (availableFpsOptionsForSnapshot), `P:7503-7506` (empty branch holding a comment).

**Problem.** fps_max (Core's maximumFpsForSettings) already holds the IMX477 uncompressed table and the 4K/2K lossless caps; the page re-applies imx477MaximumUncompressedFps and the 30/24/60 caps after it. Values agree today; two copies drift (core-map 4.5: 33/50 fps once blocked by four caps). The IMX585 branch is an if with only a comment.

**Apertar way.** 1.6.0 had no fps_max; the JS caps were its mechanism (U:4992-5020). With Core publishing the ceiling, Core is the source (rule WEB-20).

**Rework.** In availableFpsOptionsForSnapshot: when coreMax > 0 use it alone (plus the h264_max_fps cap); run the old JS caps only when fps_max is absent; the empty branch disappears with it.

**Owner decision.** None.

**Check here.** C4: FPS pills on --simulate unchanged for imx477 4K lossless and imx585.

**Needs the Pi.** Nothing.

## WEB-33. Comments: ticket ids, Cinemate references, banners, stale text in a page with no comments

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| slop | minor | S | no | fix-later | WCP-01-F1, WCP-02-F6, WCP-03-F15, WCP-04-F7, WCP-04-F8 (comment part), WCP-05-F9, WCP-06-F3, WCP-07-F11 (comment part), WCP-08-F3, WCP-10-F11; page part of X-slop-1 |

**Where.** CSS `P:196, 230, 587, 850, 859, 916, 1398, 1841, 1979, 2505, 3107, 3320-3561`; script `P:6673-6685, 7172-7173, 7565-7576, 7626-7633, 7900, 8263-8266, 8482-8483, 10123, 11649-12817, 14453-14455, 16416-16578, 18758-18889, 19868-19871`.

**Problem.** T31/T33/T34/T43/T49/T50/T51, O1, R2, Q2, 'Request 24', 'as in Cinemate', "Cinemate's cropDiagram", 'Port of Cinemate's settings-editor config.txt tab', '// ---- Mode Ladder (T34) ---' banners, a reference to playclock.js that exists only in the KB, and stale text (wrong panel name, 'pin | function | active | Test', 'pin dropdowns keep the dark look'). The port adds hundreds of comment lines to a page whose upstream script has 2.

**Apertar way.** Rule WEB-18: no comments, banners or JSDoc (2 lines in 7573, U:8474-8475); 0 CSS comments upstream.

**Rework.** One pass over the file: delete ticket tokens, Cinemate references, banners and history; delete comments that restate code; keep at most one-line hazard reasons (fetchBufferState lock-free; CSS order '/* after .no-media so it wins */'). The comments made wrong by other items are rewritten there (WEB-7). Either port the KB's playclock checks as tools/ host test or drop the reference.

**Owner decision.** None.

**Check here.** `grep -nE '\b(T[0-9]{2}|Q[0-9]|O[0-9]|Request [0-9]+)\b|[Cc]ine[Mm]ate|// ----' src/web/WebControlPage.cpp` = 0; C1, C2.

**Needs the Pi.** Nothing.

## WEB-34. Operator text: long card copy, env names, core.py, board-specific numbers, separator and glyphs

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| slop | minor | S | no | fix-later | WCP-03-F12, WCP-04-F8 (UI text part), WCP-04-F11, WCP-05-F7, WCP-07-F11 (glyph part), WCP-10-F13; X-slop-12 |

**Where.** `P:4912` (data-search 'log cinemate'), `P:5195` ('Resolutions array'), `P:5792` ('about six times faster ...'), `P:5813` ('(as before)'), `P:5863` (Boot Config copy, 305 characters), clip-name hint (247 characters), `P:8178-8180` ('about 69 fps measured at 4K 12-bit'), `P:8263-8266` ('add modes with core.py'), 32 lines with ' · ', '…' (15), '×' (16), 'pending: N, merging X', `P:19828` (toast without period).

**Problem.** Operators read ticket-note language: env names (WEB-16), history, a Cinemate search keyword, programmer words, an unmeasured speed claim, a board-specific encoder number shown on every board, and a tool (core.py) that is in neither repo. Separators and glyphs differ from the rest of the page.

**Apertar way.** Rule WEB-23: card copy is one sentence of about 6-15 words ending in a period ('Fan control and temperature management.' U:3632); summaries join with ' • ' (30 uses, 0 '·'); ASCII '...' ('Finishing...', 'Testing...'); toasts end with a period ('Write speed test started.' U:11307).

**Rework.**
1. One sentence per card copy; drop env names, '(as before)', the Cinemate keyword, the speed claim; 'Resolutions array' -> 'Resolutions'.
2. 'Sensor probe off: add modes with core.py ...' -> 'Sensor probe off: no modes to activate.'
3. Drop '69 fps' and keep 'watch the buffer bar' (or let Core publish the measured limit).
4. Replace ' · ' with ' • ', '…' with '...', '×' with 'x' in user-visible strings; 'Pending ' + n.
5. 'Storage pre-roll started.' with the period.

**Owner decision.** None.

**Check here.** `grep -c ' · \|…\|core\.py' WCP` = 0; C4 visual check of the cards.

**Needs the Pi.** Nothing.

## WEB-35. Dead CSS rules and dead ladder helpers

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| slop | minor | S | no | fix-later | WCP-01-F5, WCP-02-F9 |

**Where.** `P:1028-1034, 1045-1055, 1131-1134, 1156-1182, 1301-1306, 1314-1319, 1339-1342` (.ladder-row.dragging/.drop-target, .ladder-handle, .ladder-thr, .ladder-row-buttons, .ladder-pool-number, .ladder-add.on-ladder, .select-note.ladder-on, .ladder-icon-button*); `P:8106-8114` (createLadderIconButton, no caller); `P:7644-7650` (ladderIcons.handle/up/remove); `P:3288-3301` (.controls-output-item, .controls-output-title).

**Problem.** About 60 lines of rules with no element and a helper with no caller, left from removed iterations (920beb0, 1ef94fe) and the d44b177 squash.

**Apertar way.** Every upstream class family has an element; no dead rules.

**Rework.** Delete the listed rules, createLadderIconButton and the unread ladderIcons entries (the rest goes with WEB-20).

**Owner decision.** None.

**Check here.** For each deleted class `grep -c '<class>' WCP` = 0 outside CSS; C2; C4 Modes and Controls panels unchanged.

**Needs the Pi.** Nothing.

## WEB-36. Player pacing tuned on a Pi 5 only

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| board | minor | S | yes | keep-and-document | WCP-06-F13 |

**Where.** `P:12209-12218` (0.35 s look-ahead), `P:12247-12255` (two lanes at 640 w), `P:12599`.

**Problem.** Constants come from Pi 5 decode times (4fa0432: 180 ms per lossless frame). A Pi 4 or CM4 decodes slower; the page should degrade to 'PLAYING • N FPS' rather than stall. Unconfirmed.

**Apertar way.** No precedent (playback in the page is new).

**Rework.** No code change now. Handoff: the constants and the board they were measured on; measure a Pi 4 in the Pi-model stage and adjust only if it stalls.

**Owner decision.** None.

**Check here.** Nothing here.

**Needs the Pi.** Pi 4 or CM4: play a 4K lossless cDNG clip from the WebUI and note the shown fps.

## WEB-37. WebUI-only panels (Modes, Controls) and three editors of apertar-hardware.conf

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| new-ground | nit | S | yes | keep-and-document | WCP-03-F10 (panel part), WCP-03-F11 |

**Where.** `P:4750-4773` (nav entries), `P:6137-6235` (Controls pane, Hardware card, Config text editor).

**Problem.** Two settings panels have no touch-UI counterpart, and apertar-hardware.conf now has three editors (Controls form, Hardware form, text), each with its own message, pending box, Reload and Save. Both are deliberate (854fe43, 6777ebe, f5fe41b).

**Apertar way.** Rule WEB-23: mirror the touch UI's panels; WebUI-only features only where a browser adds value. conv-hardware-config: one hand-edited file, a raw text editor (U:3840-3870).

**Rework.** Keep both panels and all three editors. Handoff: name the two WebUI-only panels and why; state that the forms and the text editor end in the same revision-checked store. The shared message/pending/save plumbing and the cross-card save loss are HW-40 and HW-27.

**Owner decision.** None.

**Check here.** Nothing.

**Needs the Pi.** Nothing.

## WEB-38. Small duplications: flicker-free maths, ladder toast, raw createElement, typeof number checks

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| duplication | nit | S | no | fix-later | WCP-04-F14, WCP-06-F10 (typeof part) |

**Where.** `P:7590-7601` (JS copy of Core flickerFreeShutterAngles); `P:7982-7993` (showLadderLockWarning drives the toast element and timer itself); `P:8484-8657` (18 raw document.createElement next to createDomElement P:10676); `P:13835-13856` (typeof === "number" for cdng_log_bits, buffer_stop_percent, storage_preroll_fps).

**Problem.** Small drift risks inside the page.

**Apertar way.** showToast (U:7804); createDomElement(tag, class, text) (U:6555); the snapshot merge uses isFiniteNumber + Number() (U:8640-8676). JS mirrors of Core tables are accepted (rule WEB-8, U:4966-5005).

**Rework.** showToast gains an optional link element and showLadderLockWarning calls it; renderValueListsEditor uses createDomElement; the three merge lines use isFiniteNumber + Number(). The flicker-free copy may stay (rule WEB-8), or Core publishes the merged angle list.

**Owner decision.** None.

**Check here.** C2; C4: ladder lock toast and value-list editor unchanged.

**Needs the Pi.** Nothing.

---

## Page steps owed to other lists (fixed in their commit)

| Item there | Page step |
| --- | --- |
| HW-1 / APP-1 | Delete Edit file and Use This Text (WEB-1 steps 1-3, 5) |
| HW-4 / APP-3 | bootConfigPost -> sendCommand set_boot_config (WEB-1 step 4) |
| HW-13 | controlsState and controlsCall -> state fields and sendCommand (WCP-09) |
| HW-14 | Remote controls card into the Controls panel; delete the 5 s loadRemoteControls loop (WCP-03-F8, WCP-10-F9) |
| HW-19 | Check and Undo through POST /api/config (WEB-24) |
| APP-5 | Readers switch from result.code to the reply or a re-read (Boot Config, set_controls) |
| APP-7 | get_controls read becomes fetch('/api/config') |
| APP-8 | Try button greys rows whose action is run_scriptN |
| APP-9 | Delete the *_env greying (WEB-16) |
| APP-19 | `uiState.audio_recorded_outline_enabled === true` at P:16157 |
| APP-27 | /api/buffer recording read as buffer_recording (WEB-4) |
| APP-36 | Update the clip-info reader at P:12743 |
| APP-47 | cameraPreviewTdn in the preset allow-list if it becomes a preset field (WEB-15) |
| CAM-1 | IMX585 alias entries P:9078-9085 follow its answer (WEB-6 step 4) |
| CAM-17 | WebUI builds the ladder line from ladder_rung, ladder_tops and the get_mode_ladder reply |
| CAM-19 | Hide the ladder card when raw_recording is false (P:9488-9496 pattern) |
| CAM-14 / REC-4 | Read iso_auto_allowed (WEB-14) |
| REC-18 | Check WCP for body.busy readers |
| REC-30 | Drop {cam}, {model}, {date_} from the token palette (WEB-8) |
| X-stock-behaviour-11 (REC-3 / APP-13) | Grey the media-trim switch when Core says the helper is missing |

## Conforms to original Apertar (for the handoff)

- The page stays one raw string in webControlPageHtml(); no external CSS, JS or CDN (rule WEB-1). The page script passes `node --check` at cinemate-port.
- State-changing calls use sendCommand with flat payloads and Core's error text in showToast(error.message, true): set_fps_speed_ramp, set_value_steps, set_mode_ladder, set_storage_preroll, frames per folder (rule WEB-3, WEB-14).
- Lists travel as one comma string (values: rest.join(",")); value-list state under "ui" as arrays, with set_favorites_order as precedent.
- Ceilings come from Core state (fps_max, fps_take_max, iso_max), and the ladder lock, WB Auto in Clear HDR and media gates are refused in Core and only mirrored in the page (rule WEB-20).
- Recording frame, buffer bar, red timecode, audio outline, Preview TDN, FPS phase lock, media trim and clip merge switches are exactly the upstream toggle recipe (toggleOptions, formatToggleLabel, enabled "true"/"false").
- mergeCameraStateFields and applyCommandSnapshotPatch extended in place with new case arms (rule WEB-13).
- New colours as :root tokens in the upstream token block; status pill and dot pre-roll states follow the upstream state-class pattern; take cues are state classes on existing elements.
- New panels follow the nav + settings-panel[data-panel] + settingsPanelMeta pattern and reuse /icons PNGs for nav icons; lazy loads per pane sit in setSettingsPanel next to fetchPresetLibrary and fetchConfigFile.
- IMX283 helpers copy the shape of the IMX294 helpers; resolutionCommandPayload and cropRatioLabelForResolutionValue extended in the upstream if-chains; the old IMX585 branch of normalizedResolutionForSnapshot removed, not left dead.
- set_timecode_mode target= is additive with the old default.
- Playback keeps upstream helpers and routes: setText, showToast, mediaSelectionKey, mediaSelectionQuery, fetchMediaLibrary, /api/media/delete-selected and /api/media/download-selected, user_activity as the upstream raw fetch; the folder button is greyed in a take as on the touch UI.
- The /api/buffer reply is flat scalar JSON like /api/state; upstream fetchState and fetchPresetLibrary are untouched.
- Preset import allowedKeys: 17 keys appended to the same list and loop.
- requestStoragePreroll has the requestMediaSpeedTest shape; Reload with unsaved Boot Config edits asks window.confirm; reboot uses the existing restart_system command; Boot Config On/Off pills use buildOptionButtons.
- The Config text editor is extended in place (same textarea id, gutter, Check, diff, revision).
- The GPIO chip setting is back on the Controls page with per-chip checks (Core 04fe197).

## Dropped or left to another list

| Finding | Reason |
| --- | --- |
| WCP-05-F10 | Dropped by the unit skeptic: upstream reaches into builder output the same way (U:7116) |
| WCP-01-F12 | Merged into WEB-25 as "keep" (the class-only hiding is correct) |
| WCP-08-F4 | Not a change: the fast poll stays in WEB-4's shape; handoff sentence there |
| WCP-10-F10 | Not separate work: toggleRecord's input moves with WEB-4 step 7; behaviour is an owner decision and stays |
| WCP-03-F8, WCP-10-F9 | Same as HW-14 (Remote controls card and its 5 s loop); fixed there |
| WCP-10-F1, WCP-10-F3 | Also sources of HW-4 / HW-1; the page half is WEB-1, fixed in one commit with them |
| X-protocol-security-1, -7 | Core half in HW-1 / HW-4 (APP-1 / APP-3); page half in WEB-1 |
| X-state-consistency-3 | WebUI copy in WEB-6; touch-UI lists are the UI editor's; Core comment is CAM-22 |
| X-state-consistency-5 | WCP part is WEB-32; QML and App fallbacks are the UI editor's and APP-39 |
| X-state-consistency-9 (conform_fps control), -14 | CAM-18 and APP-47; page follows (WEB-15 note) |
| X-stock-behaviour-10 | Core half CAM-14; WebUI half WEB-14 |
| X-stock-behaviour-2, -11 | Core first-run writer HW-9; trim default REC-3 / APP-13; page greying listed above |
| X-stock-behaviour-1, -3 to -9, -12, -13 | Not WebUI: done (display fallback) or camera, recording, UI lists |

## Same problem in another list (fix once)

| Here | There |
| --- | --- |
| WEB-1 | HW-1, HW-4, APP-1, APP-3 |
| WEB-4 | APP-27 |
| WEB-6 | CAM-1, CAM-22 |
| WEB-7 | CAM-17, CAM-19 (page steps) |
| WEB-8 | REC-30; Apertar-UI ClipNameCard.qml (UI editor) |
| WEB-14 | CAM-14, REC-4 |
| WEB-16 | APP-9 |
| WEB-24 | HW-19 |
| WEB-37 | HW-27, HW-40 |
