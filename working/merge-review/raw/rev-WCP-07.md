# Review WCP-07 (stage 2): WebUI JS, snapshot merge/patch, clip-name composer, renderSnapshot

Scope: `/home/user/build/review/diffs/WCP.part07.diff` = `src/web/WebControlPage.cpp` new-file lines 13893-16360 @cinemate-port.
Upstream compare: `/home/user/wt/core-upstream/src/web/WebControlPage.cpp` @upstream-1.6.0. Yardstick: `raw/conv-webui.md` (ids S*, I*, N*, R*),
`raw/conv-core-command-plane.md` (C1-I09). All claims confirmed (read in code) unless labelled.
Note: the hint "playback overlay, viewer" does not match this slice; only the hook `pbSnapshotChanged(snapshot)` (16029) is here.

## Verdict in one paragraph

Most of the slice follows the upstream pattern closely: new state fields merged in the existing `if (source.x)` style, new
`case` arms in `applyCommandSnapshotPatch`, On/Off toggles built exactly as recipe R1, Core enforces the new locks (N2), and
the extended commands stay backward compatible. The foreign part is the clip-name composer: 572 lines of drag and drop with its
own module-level state object, UPPER_CASE constants and a second `fetch` wrapper, where an upstream feature of this kind is
20-40 lines. Smaller drifts: buffer fields read from `system` by copying them to the top level, a debug note parsed by regex,
env-var names shown to the operator, the ISO/WB "Auto" word lost on the badges, and the record button greyed without media
(which also blocks `--simulate`).

## Findings

| Id | Sev | Cat | Title |
| --- | --- | --- | --- |
| F1 | major | new-ground | Clip-name composer: 572 lines of DnD + long-press for one template string |
| F2 | minor | mismatch | Composer state outside `state`, UPPER_CASE constants, one-letter fields, comments |
| F3 | minor | mismatch | `system.buffer_*` / `storage_preroll_*` copied to the snapshot top level instead of read via `systemState` |
| F4 | minor | mismatch | Buffer note parsed by regex; 60 % / 12 frames / 90 % hard-coded in UI text |
| F5 | minor | removed-upstream-behaviour | ISO / WB badges no longer say "Auto" |
| F6 | minor | removed-upstream-behaviour + bug | Record button greyed without media: "No media mounted." toast unreachable; `--simulate` cannot record |
| F7 | minor | slop | `APERTAR_*` env-var names in operator text; `_env` state flags |
| F8 | minor | mismatch | Pre-roll auto switch: `value on/off`, On/Off order, post-hoc disabling, `hidden` attribute |
| F9 | minor | bug | Log "Not applied" note blames SDR sensor compression in every not-applied case (simulate, no session, other sensors) |
| F10 | nit | duplication | `clipRawCommand` second `/api/command` wrapper |
| F11 | nit | slop | ~25 narrating comment lines, non-ASCII `·` `…` `×` in strings, "pending: 0" status text |
| F12 | nit | slop | "Custom" preset pill forced disabled-but-active by poking the DOM after `buildOptionButtons` |

### F1. Clip-name composer is far larger than the Apertar way (new-ground, major, deliberate yes)

- Port: 14453-15024 @cinemate-port (diff lines 256-826): `CLIP_PRESETS`, `CLIP_TOKEN_GROUPS`, `clipUi`, 22 `clip*` functions. Two
  drag systems: HTML5 `dragstart`/`dragover`/`drop` for the mouse (`clipAttachPill`, `clipBindRow`) and Pointer Events
  long-press 300 ms with a cloned ghost, `setPointerCapture`, `navigator.vibrate`, `touchmove` blocking (`clipPointerDrag`),
  plus hit testing (`clipDropIndex`, `clipOverRow`, `clipShowMarker`), inline text-pill editor, 350 ms debounced auto-save.
- Upstream: no drag and drop anywhere (`grep -c dragstart` upstream WCP = 0). Feature size 20-40 lines in 3-5 places
  (conv-webui section 0: SMPTE toggle, fan mode, media speed). Choices are `buildOptionButtons` pill grids (I6, WCP:9147-9167
  @upstream-1.6.0); free values are `settings-input` fields with an Apply button (R3).
- Deliberate: yes. Commit 014a2bf message: "a drag-and-drop pill composer"; the touch UI has the matching
  `qml/ClipNameCard.qml` (Apertar-UI 606f137), so the web card mirrors the touch UI (N6).
- Verdict: simplify. Keep presets, token palette and preview (they mirror the touch UI and Core's tokens). Drop reordering by
  drag.
- Rework: (1) presets: `buildOptionButtons("clipNamePresets", clipNamePresetOptions, ...)` as now. (2) template: one
  `<input class="settings-input" id="settingsClipNameInput">` holding the template string, `setFormValue` keeps focus (I6),
  `input` event -> `preview_clip_name` -> `setText("clipNamePreview", ...)`; Apply button -> `set_clip_name_template` (R3).
  (3) palette: `buildOptionButtons("clipNamePalette", tokenOptions, "", (v) => insert "{v}" at the caret)`. Delete
  `clipPointerDrag`, `clipAttachPill`, `clipBindRow`, `clipDropIndex`, `clipOverRow`, `clipShowMarker`, `clipApplyDrop`,
  `clipMakePill`'s editor, the ghost/marker CSS. Estimated 572 -> ~80 lines.
- Risk: the operator loses drag reordering on the web page (keeps it on the touch UI); token syntax becomes visible in the
  input. Core and `ClipName.hpp` unchanged.

### F2. Composer naming and state (mismatch I2, I7, I9, S6; minor)

- Port: `const clipUi = { items, savedTemplate, dirty, saveTimer, seq, dragging, ... }` 14491; `CLIP_DEFAULT_TEMPLATE`,
  `CLIP_PRESETS`, `CLIP_TOKEN_GROUPS`, `CLIP_TOKEN_INFO` 14456-14490; items `{ t: "tok", v: ... }`; `{ v: "date", ... }`.
- Upstream: one `state` object holds all client state including timers (`WCP:4204-4266`, `state.wbCommitTimer` 4219);
  module-level names are only option arrays `<thing>Options` in camelCase (4039-4127) plus `state`, `favoriteItemMeta`,
  `settingsPanelMeta`. `grep '^    const [A-Z][A-Z_]* '` upstream: 0 hits.
- Rework: `state.clipNameItems`, `state.clipNameSaveTimer`, `state.clipNameDirty` etc. in the `state` literal; constants
  renamed `clipNamePresetOptions`, `clipNameTokenGroups` and moved to the option-list block; field names `type`/`value`.
  Mostly moot after F1.

### F3. Buffer fields copied out of `system` (mismatch I3; minor)

- Port 15222-15230 (diff 874-881): `for (const key of Object.keys(systemFields)) if ((key.startsWith("buffer_") ||
  key.startsWith("storage_preroll_")) && snapshot[key] === undefined) snapshot[key] = systemFields[key];` then reads
  `snapshot.buffer_setting`, `snapshot.storage_preroll_active`; patches `snapshot.buffer_setting` /
  `snapshot.storage_preroll_auto` (14024-14032). The same slice reads sibling system fields directly:
  `systemState.media_trim_enabled`, `systemState.clip_merge_enabled`, `systemState.frames_per_folder` (16165-16229).
- Core: `bufferSettingMembers()` App:245-268 @cinemate-port is emitted inside `"system":{` (App:9565, 9587) for `/api/state`,
  and at top level in `settingsBody` for socket replies.
- Upstream: system telemetry is read through `systemState` (`systemState.write_speed_running` WCP:9879-ish, port 15862);
  `ensureSnapshotShape` WCP:4276-4292 guarantees `snapshot.system` exists.
- Rework: delete the copy loop; read `systemState.buffer_*` / `systemState.storage_preroll_*` in `renderSnapshot`; in the
  patch arms write `systemState.buffer_setting` / `systemState.storage_preroll_auto`. `shownFps()` (8683) and
  `frameBufferBar` (16419, other unit) follow.
- Related, other unit: `frameBufferBar` (16419) is a second module-level state object with its own timer (I2); move its
  fields to `state.frameBuffer*`.

### F4. Buffer note parsed by regex, Core constants hard-coded (mismatch C1-I09 / flat scalars; duplication; minor)

- Port 15461 (diff 1037): `/ram budget (\d+) MiB .*frame ([\d.]+) MiB = (\d+) frames/.exec(bufferNote)`; text 15479-15480:
  "up to 60 % of free memory", "If the buffer gets 90 % full", "A small queue of 12 frames".
- Core already sends `buffer_stop_percent` (App:258) but the UI does not use it. The note is a free English log line
  (`bufferbudget` plan text); rewording it in Core silently drops the short form in the UI.
- Upstream: state carries scalars the page formats (`media_free_bytes`, `time_left_percent`, `record_time_left_minutes`),
  never parsed prose.
- Rework: Core adds `buffer_ram_budget_mib`, `buffer_ram_frames`, `buffer_frame_mib`, `buffer_queue_frames`,
  `buffer_ram_percent` to `bufferSettingMembers`; UI formats them and uses `buffer_stop_percent` for the 90 %.

### F5. "Auto" lost on ISO and WB badges (removed-upstream-behaviour; minor)

- Port 15399-15407 (diff 977-985): `isoLabel = snapshot.iso_auto ? (isoInUse > 0 ? String(isoInUse) : "Auto") : ...`;
  `setText("isoBadge", "ISO " + isoLabel)`; `settingsIsoSummary` same; WB badge shows `wb_actual_kelvin` when auto.
  Green (`system-value`) is set only by `isoSetByCamera` (Clear HDR hold / ceiling, 8673-8681: "Auto stays white") and
  `wb_auto_after_clear_hdr`.
- Upstream 9494-9496: `setText("isoBadge", snapshot.iso_auto ? "ISO Auto" : ("ISO " + isoLabel))`, `"WB " + whiteBalanceLabel`.
- Effect: ISO Auto at 800 and manual ISO 800 look identical on the main badge and the summary. The comment at 15398
  ("green whenever the camera set it") does not match the code.
- Rework: keep the number and the word: `"ISO Auto " + isoInUse` / `"WB Auto " + kelvin + "K"` (falls back to "ISO Auto");
  fix or drop the comment.

### F6. Record button greyed without media (removed-upstream-behaviour + bug; minor)

- Port 15762-15763 (diff 1161-1163): `recordButton.disabled = !(isRecording || ...) && (!hasMedia || ...)`; `hasMedia` now
  from `media_alive` (15253-15255).
- Upstream: button stays live; `toggleRecord` answers with "No media mounted." (WCP:10709-10712, 10723-10726, 10735-10738
  @upstream-1.6.0). Port keeps those toasts (19219, 19233, 19245) but they are now unreachable, and they still test
  `media_mounted`, not `media_alive`.
- Bug, failing input: Core started with `--simulate` (or `APERTAR_MEDIA_REQUIRE_MOUNT=0`) and no drive: Core allows the take
  (`mediaGateBypassed()` App:11331-11337, used at 11138) but `media_alive` = `mediaSnap.mounted()` = false (App:9556), so the
  WebUI greys REC. Desk testing with `--simulate` (fork-log:138) can no longer start a take from the WebUI.
- Rework: drop `!hasMedia` from `recordButton.disabled`; switch the three `toggleRecord` guards to the same `hasMedia`
  source; or Core sends `media_usable` (= `mediaGateError().empty()`) and the page gates on that.

### F7. Env-var names in operator text (slop / env knobs; minor)

- Port: "Set by APERTAR_STORAGE_PREROLL" (15853), "Forced off by APERTAR_MEDIA_TRIM=0." (16183), "Forced off by
  APERTAR_CLIP_MERGE=0." (16222), frames-per-folder env note (`frames_per_folder_env`, env `APERTAR_CDNG_FRAMES_PER_FOLDER`,
  App:266); state flags `storage_preroll_auto_env`, `media_trim_env_off`, `clip_merge_env_off`, `frames_per_folder_env`.
- Upstream: WCP contains 0 `APERTAR_` strings. Upstream env knobs exist only as developer overrides read in Core
  (`APERTAR_HARDWARE_CONFIG` App:4254, `APERTAR_H264_*` CC:4333-4384 @upstream-1.6.0), never surfaced in the UI. Each of
  these four settings already has a conf key and a command.
- Rework: Core drops the four env overrides (one source of truth: `apertar-hardware.conf` + command); delete the `_env`
  fields and the UI notes. If one must stay for the developer, do not mirror it in the UI. Deliberate: unknown.

### F8. Pre-roll auto switch shaped differently from upstream toggles (mismatch I5, I6, I11, R1; minor)

- Port 15836-15853 (diff 1196-1215): `buildOptionButtonsInto(autoContainer, ["On", "Off"], ...)`, sends
  `{ cmd: "set_storage_preroll", value: "on" | "off" }`, then loops `button.disabled = true` when `fromEnv`; rows hidden via
  the `hidden` attribute (`prerollRow.hidden`, `prerollAutoRow.hidden`, `prerollLast.hidden`, `fpfEnvNote.hidden`,
  `clipMergeLast.hidden`).
- Upstream: `buildOptionButtons(id, toggleOptions /* ["Off","On"] */, formatToggleLabel(b), ...)` with
  `enabled: "true"|"false"` (WCP:10109-10115); unavailable choices passed as `{ enabled: false }` (9950-9954); hiding by
  `classList.toggle("hidden", ...)` (13 uses, attribute form 0 on elements).
- Rework: `buildOptionButtons("storagePrerollAutoOptions", toggleOptions.map((v) => ({ value: v, enabled: !fromEnv })),
  formatToggleLabel(snapshot.storage_preroll_auto), ... { cmd: "set_storage_preroll", enabled: ... })` (Core already
  accepts true/false; rename the field to `enabled` there); use `classList.toggle("hidden", ...)`.

### F9. Log "Not applied" note is sensor-specific and wrong in other cases (bug / pi-compat; minor)

- Port 15491-15493 (diff 1024-1025): when `cdng_log_applied === false` the note always says "in SDR the sensor chip already
  compresses the raw stream, so Log works in Clear HDR (16-bit)".
- Core: `cdngLogApplicableLocked()` = `!simulateCamera_ && session_ && session_->cdngLogApplicable(settings_)` (CC:12511-12514).
  Failing input: `--simulate`, or no capture session, or a sensor without companded SDR (IMX283): the note blames IMX585 SDR
  compression. Probable for IMX283 (the rule inside `cdngLogApplicable` not read; command to settle:
  `grep -n cdngLogApplicable src/camera/*.cpp`).
- Rework: Core sends `cdng_log_reason` (short sentence) and the UI shows it, the upstream way of Core-worded refusals (N2, N7).

### F10. `clipRawCommand` (duplication; nit)

- Port 14383-14392: second `fetch("/api/command")` wrapper to skip the optimistic patch and re-render for
  `preview_clip_name`. Upstream has one precedent for a raw fetch (`notifyStandbyActivity` WCP:11503-11515).
- Rework: name it for what it does, `fetchClipNamePreview(template)`, sending only `preview_clip_name`; use `sendCommand` for
  everything else (already so for `set_clip_name_template`).

### F11. Comments, non-ASCII, status wording (slop; nit)

- ~25 comment lines in this slice ("Requests overlap: each one clears only the switch it started.", "Raw takes say what the
  sensor delivers ...", "media_alive comes from the media watcher ..."). Upstream: 2 JS comment lines in the whole file (I9).
  Port file: 341.
- `·` (resolution badge, ladder sub-lines), `…` ("Switching to Resolution n…"), `×` (clip-x). Upstream WCP: 0 of these;
  upstream writes "..." ("Finishing...", "Testing...").
- "pending: 3, merging C0004" (16217) lowercase fragment; upstream read-outs are capitalised labels (N7).
- Rework: delete comments that restate code; ASCII `|` or `/` and `...`; `"Pending " + n`.

### F12. "Custom" preset pill hack (slop; nit)

- Port 14570-14576: after `buildOptionButtons`, `customButton.disabled = true; classList.remove("disabled");
  classList.toggle("active", ...)`. Upstream shows a non-preset value in the `select-value-pill` of the topline
  (WCP:2581-2584), not as a fake pill. Rework: drop the Custom pill; `setText("settingsClipNamesValue", "Custom")` already
  does it.

## Abstractions (inventory section 4)

| Name | Verdict | Reason |
| --- | --- | --- |
| `clipUi` + 22 `clip*` functions | simplify | F1/F2: presets + input + palette in ~80 lines, state in `state` |
| `clipRawCommand` | simplify | F10: one purpose-named fetch for `preview_clip_name` |
| `buildOptionButtonsInto(container, ...)` | keep | Needed for containers built in code (Value Lists 8593-8645); `buildOptionButtons(id, ...)` kept as the wrapper, signature unchanged |
| `frameBufferBar` (16419) | rework-to-upstream-pattern | I2: fields and timer belong on `state`; defined in another unit |
| `.system-value`, `markActiveSystemValue`, `isoSetByCamera` | keep | Small, one class, mirrors "camera decided" from Core fields; tested on camera (e25fd2b). Fix F5 so Auto is still named |
| option flags `locked`, `system` | keep | Extend `normalizeChoiceOptions` in place like `enabled`; Core enforces the lock (CC:10643) |
| `state.fpsSwitchingTo`, `state.ladderServer` | keep | Follow I2 (on `state`) |

## Conforms

- `mergeCameraStateFields` tail (13907-13932): 15 new fields in the existing one-line `if (typeof source.x === ...)` style.
- `applyCommandSnapshotPatch`: new `case` arms beside their neighbours; 4 UI toggles as R1 step 5 (`uiState.<x>_enabled = boolValue`).
- Recording frame, buffer bar, red timecode, audio outline, Preview TDN, FPS phase lock, media trim, clip merge switches:
  exactly R1/I4/I5 (`toggleOptions`, `formatToggleLabel`, `enabled: "true"|"false"`, try/catch `showToast(error.message, true)`).
- Frames/RAM and Log pills: R2 with `buildOptionButtons(..., 2)`, disabled while recording (N3).
- N2 holds: ladder lock refused in Core (CC:10643, 11400, 11448, 11577), WB Auto in Clear HDR refused in Core
  (CC:11299-11302) and only mirrored in the page.
- N8 holds: every new command is in the `help` list (App:12930).
- Protocol compatible: `set_iso_auto` without `enabled` stays Auto (App:12995-13000); `set_timecode_mode` without `target`
  sets both (patch 14069-14076); `media_mounted` still sent beside `media_alive`, and the page falls back to it.
- `cropRatioEnabled` (15249) is back to the upstream expression.
- No T/Q ticket numbers in this slice's code or UI text.
- Safety-stop REC/READY behaviour (15754-15775) is an owner decision (fork-log:138, c5db8b2), not reported.

## Skeptic

Checked at `cinemate-port` 01f170c (`git show cinemate-port:<path>`) against `/home/user/wt/core-upstream` (upstream-1.6.0).

| id | verdict | why |
| --- | --- | --- |
| F1 | corrected | Confirmed: block 14453-15024, 0 `dragstart`/`draggable`/`setPointerCapture`/`navigator.vibrate` upstream. Deliberate (014a2bf body). Fixed path (`src/util/ClipName.hpp`); added that the touch UI twin `qml/ClipNameCard.qml` (601 lines, drag) must be reworked in the same step or the two UIs diverge. |
| F2 | stands | `clipUi`/`CLIP_*` at 14456-14495 confirmed; upstream `state` literal 4204+, `toggleOptions` 4066, 0 UPPER_CASE consts. |
| F3 | corrected | Copy loop 15215-15222 confirmed. Cause found: Core sends `bufferSettingMembers()` twice, flat in `settingsBody` (App:309) and in events/replies, and nested under `system` in /api/state (App:9587 via `bufferMembers`). Upstream never patches `snapshot.system` from events, so "patch systemState" would be new ground. Rework moved to Core: settings fields at the top level, only the gauge under `system`. |
| F4 | corrected | Regex 15469 and fixed 60 % / 12 / 90 % text 15478-15480 confirmed; fraction is configurable (BufferBudget.hpp:33, 341), queue depth per media profile (MediaProfile.hpp:131). Unmatched note falls back to the raw text, so a reworded log degrades, not breaks. `buffer_stop_percent` is the active/last take's value (BufferBudget.hpp:222-225), 0 before a take: Core must send the configured one. |
| F5 | corrected | Code confirmed (15398-15406, summary 15507). Deliberate and owner-tested: fork-log e25fd2b "badges show iso_actual/wb_actual_kelvin ... tested (Patrik: works well)". Severity minor kept; rework keeps the value and adds the word. |
| F6 | corrected | Gate confirmed (15772-15773). Deliberate: 438a342 "the WebUI follows media_alive" and that diff adds `!hasMedia`. The `--simulate` point is weaker than claimed: upstream's own toggleRecord guards on `media_mounted` too, so a desk without media was already blocked client-side; the port's new defect is the split (button on `media_alive`, guards 19218/19232/19244 on `media_mounted`) and Core's richer `mediaGateError()` sentence (App:11359+) never reaching the operator. |
| F7 | corrected | Strings 15852, 16183, 16210, HTML 5818; Core 262-268 confirmed; commands for all four exist (App:12829, 12857, 12900, 13194). Category changed to mismatch: upstream Core has 35 `getenv("APERTAR...")` knobs but WCP shows none (0 `APERTAR_` strings). |
| F8 | stands | 15841-15850 confirmed; upstream 10109-10115. Stronger: the port's own `set_media_trim` (16184) already uses `toggleOptions`/`enabled`, so pre-roll is the odd one even inside the port. |
| F9 | stands | Note 15456-15457 fixed text; `cdngLogApplicableLocked` CC:12511-12514 false on simulate / no session; session check returns false without libcamera too. |
| F10 | corrected | Line was wrong: `clipRawCommand` is 14577-14588. Rest stands. |
| F11 | corrected | Lines: status string at 16221-16222. Glyph counts confirmed file-wide (port 32/15/16 vs upstream 0). |
| F12 | corrected | Lines were wrong: 14960-14972. Rest stands; absorbed by F1. |

## Final findings

### WCP-07-F1 [new-ground, major] Clip-name composer: ~570 lines of drag-and-drop + long-press for one template string
- where: src/web/WebControlPage.cpp:14453-15024@cinemate-port; Apertar-UI qml/ClipNameCard.qml, qml/ClipNamePill.qml@cinemate-port (606f137)
- port: `CLIP_*` constants, `clipUi` object, 22 `clip*` functions: HTML5 DnD for mouse, Pointer Events long-press with ghost / `setPointerCapture` / `navigator.vibrate` for touch, hit testing, inline text editor, 350 ms debounced auto-save, preview via raw fetch. Touch UI twin is 601 lines with its own drag.
- apertar way: No drag and drop in upstream WCP (`dragstart`, `draggable`, `setPointerCapture`, `vibrate` = 0). Choices are `buildOptionButtons` pill grids (WebControlPage.cpp:9147-9167@upstream-1.6.0); free values a `settings-input` + Apply button.
- matters: The original developer would maintain a mini drag framework (twice: JS and QML) for a setting changed rarely; an order of magnitude beyond any upstream card.
- rework: Keep presets (`buildOptionButtons('clipNamePresets', ...)`), a token palette (pills that insert `{token}` at the caret) and the preview line. Replace the pill row with one `settings-input` holding the template + Apply (`set_clip_name_template`); preview on input via `preview_clip_name`. Delete `clipPointerDrag`, `clipAttachPill`, `clipBindRow`, `clipDropIndex`, `clipOverRow`, `clipShowMarker`, `clipApplyDrop`, the text-pill editor and ghost/marker CSS (~570 -> ~80 lines). Same shape in `ClipNameCard.qml` (TextField + token buttons). `src/util/ClipName.hpp` and the two commands unchanged.
- effort M; deliberate yes (014a2bf: "a drag-and-drop pill composer"; UI 606f137 "untested by hand").

### WCP-07-F2 [mismatch, minor] Composer state outside `state`, UPPER_CASE constants, one-letter fields
- where: src/web/WebControlPage.cpp:14456-14495@cinemate-port
- port: `const clipUi = { items, savedTemplate, dirty, saveTimer, ... }`; `CLIP_DEFAULT_TEMPLATE`, `CLIP_PRESETS`, `CLIP_TOKEN_GROUPS`, `CLIP_TOKEN_INFO`; items `{t, v}`.
- apertar way: One `state` object holds client state and timers (WebControlPage.cpp:4204-4266@upstream-1.6.0, e.g. `wbCommitTimer`); module lists are camelCase (`toggleOptions` 4066@upstream-1.6.0); no UPPER_CASE consts upstream.
- matters: A second state container and naming scheme read as foreign code.
- rework: Fields to `state.clipName*`; rename to `clipNamePresetOptions` / `clipNameTokenGroups` in the option-list block; `type`/`value` field names. Largely absorbed by F1.
- effort S; deliberate no.

### WCP-07-F3 [mismatch, minor] Buffer/pre-roll setting fields published twice by Core; page copies `system.*` to the top level
- where: src/web/WebControlPage.cpp:15215-15222@cinemate-port; src/web/WebControlPage.cpp:13841-13860, 14027-14032@cinemate-port; src/ApertarCoreApp.cpp:252-269, 301-311, 9587@cinemate-port
- port: `bufferSettingMembers()` (setting, note, safety stop, pre-roll, frames_per_folder, clip_merge) is flat in `settingsBody` and events, and nested under `system` in /api/state via `bufferMembers`. renderSnapshot loops `Object.keys(snapshot.system)` and copies `buffer_*`/`storage_preroll_*` to the top level; the same slice reads `systemState.clip_merge_*` / `frames_per_folder` directly.
- apertar way: Settings are top-level snapshot fields (settingsBody); `system` holds telemetry read via `const systemState = snapshot.system || {}` (WebControlPage.cpp:9378@upstream-1.6.0); upstream never writes into `snapshot.system` from events.
- matters: Two access paths for one field set; render mutates the snapshot shape; one Core helper feeds two JSON places.
- rework: Core: /api/state emits `bufferSettingMembers()` at the top level beside the other settings; `system` keeps only the gauge (`buffer_used`, `buffer_capacity`, `buffer_fill`, `buffer_mode`, `buffer_unit`). Page: delete the copy loop; read `frames_per_folder*` / `clip_merge_*` from the top level too.
- effort S; deliberate unknown.

### WCP-07-F4 [mismatch, minor] Buffer note parsed by regex; 60 % / 12 frames / 90 % hard-coded
- where: src/web/WebControlPage.cpp:15467-15470@cinemate-port; src/web/WebControlPage.cpp:15478-15480@cinemate-port
- port: `/ram budget (\d+) MiB .*frame ([\d.]+) MiB = (\d+) frames/.exec(buffer_note)` (falls back to the raw note); info text fixes 60 %, 12 frames, 90 %, while the fraction is configurable (BufferBudget.hpp:33, 341), the queue depth comes from the media profile (MediaProfile.hpp:131) and the stop percent from `[storage]`.
- apertar way: State carries scalars the page formats (`media_free_bytes`, `record_time_left_minutes` in /api/state, ApertarCoreApp.cpp@upstream-1.6.0); no prose parsing in upstream WCP.
- matters: A changed config shows wrong numbers; rewording the Core log line drops the page back to the raw debug line.
- rework: Core adds `buffer_ram_budget_mib`, `buffer_ram_frames`, `buffer_frame_mib`, `buffer_queue_frames`, `buffer_ram_percent`, `buffer_stop_percent_setting` to `bufferSettingMembers`; page formats them (`buffer_stop_percent` alone is the active/last take's value, 0 before a take).
- effort S; deliberate no.

### WCP-07-F5 [removed-upstream-behaviour, minor] ISO / WB badges no longer say Auto
- where: src/web/WebControlPage.cpp:15398-15406@cinemate-port; src/web/WebControlPage.cpp:15507@cinemate-port
- port: In auto, `isoBadge` = `'ISO ' + iso_actual`, `wbBadge` = `wb_actual_kelvin + 'K'`; green only for Clear HDR hold / camera ceiling (`isoSetByCamera`: "Auto stays white"). Comment says "green whenever the camera set it".
- apertar way: `setText("isoBadge", snapshot.iso_auto ? "ISO Auto" : ("ISO " + isoLabel))`, `'WB ' + whiteBalanceLabel` with "Auto" (WebControlPage.cpp:9494-9496@upstream-1.6.0).
- matters: ISO Auto at 800 and manual ISO 800 look the same on the badge and the settings summary; comment contradicts code.
- rework: Keep the value, add the word: `'ISO Auto ' + isoInUse`, `'WB Auto ' + kelvin + 'K'` (fallback `ISO Auto` / `WB Auto`); fix the comment. Owner sign-off needed (he tested the current form).
- effort S; deliberate yes (comment 15398; fork-log e25fd2b "tested (Patrik: works well)").

### WCP-07-F6 [removed-upstream-behaviour, minor] Record button greyed without media; guards test a different field
- where: src/web/WebControlPage.cpp:15772-15773@cinemate-port; src/web/WebControlPage.cpp:15253-15255@cinemate-port; src/web/WebControlPage.cpp:19218, 19232, 19244@cinemate-port; src/ApertarCoreApp.cpp:11331-11370@cinemate-port
- port: `recordButton.disabled` adds `!hasMedia` (`media_alive` = `mediaSnap.mounted()`); toggleRecord guards still test `media_mounted` and show "No media mounted."; Core's `mediaGateError()` sentence ("The card was pulled while mounted. Eject and mount it again ...") is never shown because the button is dead.
- apertar way: Button stays live; toggleRecord answers "No media mounted." (WebControlPage.cpp:10709-10712, 10723-10726, 10735-10738@upstream-1.6.0); `recordButton.disabled` only for writes pending / photo / command in flight (9805-9806@upstream-1.6.0).
- matters: Operator gets a grey button with no reason; two fields decide "has media" in one flow; with `--simulate` or `APERTAR_MEDIA_REQUIRE_MOUNT=0` Core would accept the take (`mediaGateBypassed`) but the page refuses (upstream refused there too via `media_mounted`).
- rework: Drop `!hasMedia` from `recordButton.disabled`; guards use `hasMedia`; better, Core sends `media_gate_error` (= `mediaGateError()`, empty when usable) and toggleRecord toasts that sentence.
- effort S; deliberate yes (438a342: "the WebUI follows media_alive"; that diff adds `!hasMedia`).

### WCP-07-F7 [mismatch, minor] APERTAR_* env-var names in operator text; `_env` state flags
- where: src/web/WebControlPage.cpp:5818, 15852, 16183, 16210@cinemate-port; src/ApertarCoreApp.cpp:262-268@cinemate-port
- port: "Set by APERTAR_STORAGE_PREROLL", "Forced off by APERTAR_MEDIA_TRIM=0.", "Forced off by APERTAR_CLIP_MERGE=0.", "Set by APERTAR_CDNG_FRAMES_PER_FOLDER"; state `storage_preroll_auto_env`, `media_trim_env_off`, `clip_merge_env_off`, `frames_per_folder_env` disable the controls.
- apertar way: Upstream Core has env knobs (35 `getenv("APERTAR...")`, e.g. `APERTAR_HARDWARE_CONFIG`) but WCP has 0 `APERTAR_` strings: they are developer overrides, never surfaced.
- matters: Experiment knobs leak into the operator UI and make a second source of truth beside `apertar-hardware.conf` + command.
- rework: Drop the four env overrides in Core (conf keys and `set_storage_preroll` / `set_media_trim` / `set_clip_merge` / `set_frames_per_folder` exist, App:12829-13194), delete the `_env` fields, notes and disable logic.
- effort S; deliberate unknown.

### WCP-07-F8 [mismatch, minor] Pre-roll auto switch not shaped like an upstream toggle
- where: src/web/WebControlPage.cpp:15827-15855@cinemate-port; src/ApertarCoreApp.cpp:12900-12906@cinemate-port
- port: `buildOptionButtonsInto(container, ["On","Off"])`, sends `value: on|off`, then loops `button.disabled = true` when env-set; rows hidden with `.hidden =`.
- apertar way: `buildOptionButtons(id, toggleOptions /* ["Off","On"] */, formatToggleLabel(b), ... { enabled: "true"|"false" })` (WebControlPage.cpp:10109-10115, 4066@upstream-1.6.0); unavailable choices as `{enabled:false}` options (9950-9954); hiding via `classList.toggle('hidden')`. The port's own `set_media_trim` (16184@cinemate-port) already follows this.
- matters: Reversed pill order and a different payload field for the same kind of switch, inside one settings page.
- rework: `buildOptionButtons('storagePrerollAutoOptions', toggleOptions, formatToggleLabel(auto), ... sendCommand({cmd:'set_storage_preroll', enabled}))`; Core reads `enabled`; `classList.toggle('hidden')`. Env disable goes with F7.
- effort S; deliberate no.

### WCP-07-F9 [bug, minor] Log "Not applied" note always blames IMX585 SDR compression
- where: src/web/WebControlPage.cpp:15456-15457@cinemate-port; src/camera/CameraController.cpp:12511-12514@cinemate-port
- port: `cdng_log_bits > 0 && cdng_log_applied === false` -> fixed text "in SDR the sensor chip already compresses the raw stream, so Log works in Clear HDR (16-bit)".
- apertar way: Core words the reason, the page shows it (errors are Core sentences via `errorReply`, ApertarCoreApp.cpp@upstream-1.6.0).
- matters: `--simulate`, no capture session, a build without libcamera (session check returns false) or another sensor get a wrong IMX585-specific reason.
- rework: Core sends `cdng_log_reason` (short sentence, empty when applied) beside `cdng_log_applied`; page shows it.
- effort S; deliberate no.

### WCP-07-F10 [duplication, nit] clipRawCommand: second /api/command wrapper
- where: src/web/WebControlPage.cpp:14577-14588@cinemate-port
- port: Generic raw fetch wrapper beside `sendCommand`, used only for `preview_clip_name`.
- apertar way: `sendCommand` is the command path; the one raw fetch precedent, `notifyStandbyActivity` (WebControlPage.cpp:11503-11515@upstream-1.6.0), is purpose-named.
- matters: A generic second wrapper invites bypassing the optimistic patch/rollback path.
- rework: Rename to `fetchClipNamePreview(template)`, sending only `preview_clip_name`.
- effort S; deliberate yes (written to avoid toasts and the optimistic patch).

### WCP-07-F11 [slop, nit] Narrating comments, non-ASCII glyphs, lowercase status fragment
- where: src/web/WebControlPage.cpp:14453-14455, 15398, 15877-15880, 16221-16222@cinemate-port
- port: Narrating comments through the slice; `·` (32), `…` (15), `×` (16) in the file; "pending: N, merging X".
- apertar way: 2 `//` comment lines in the upstream script; 0 of these glyphs, `...` used ("Finishing...", "Testing..."); capitalised read-outs.
- matters: Reads differently from the rest of the file.
- rework: Delete comments that restate code; ASCII separators and `...`; `"Pending " + n`.
- effort S; deliberate no.

### WCP-07-F12 [slop, nit] "Custom" preset pill forced disabled-but-active via DOM pokes
- where: src/web/WebControlPage.cpp:14960-14972@cinemate-port
- port: After `buildOptionButtons`: `customButton.disabled = true; classList.remove('disabled'); toggle('active')`.
- apertar way: The current non-list value shows in the topline value pill (WebControlPage.cpp:2578-2581@upstream-1.6.0, `whiteBalanceValue`).
- matters: Works around the shared builder instead of using it.
- rework: Drop the Custom pill; `setText('settingsClipNamesValue', 'Custom')` (14960) already shows it. Absorbed by F1.
- effort S; deliberate no.
