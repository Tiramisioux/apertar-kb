# verify-recipes-b: recipes r4, r5, r6 (second half of 6)

Refs: fork Core 01f170c, UI 7ea9afc; upstream-1.6.0 worktrees. Plumbing (buildRows, chainHTML, showRecipe, nodeOrder, badges): all node ids used (BTN, HWIN, HUB, QML, UICONF, RENDER, CAM, RECS, DISK) exist in N; step sort order is right; val()/isFork() handle up-overrides and fork:true correctly. No plumbing defect.

## r4 Map a button or encoder
- Step BTN (conf lines, `[neorotary4]`, `encoder0_cw=`, `enabled=true`): true both modes (NeoRotary4Input.cpp loadConfig upstream:383-428; HardwareConfigText.hpp:53,940 fork).
- Fork claim "applies without a Core restart": true (ApertarCoreApp.cpp:12255-12317 applyHardwareText restarts changed drivers). Upstream "read once at start": true (neoRotary4Input_.start only at ApertarCoreApp.cpp:6887).
- Context lines in HWIN (fork `{"iso_up", "ISO", "ISO up", ...}` ActionCatalog.hpp:39; upstream `if (action == "iso_up" ...) return "iso_up";` in all three *Input.cpp) occur. HUB context `if (const auto mode = pcfSettingStepMode(action, "iso")) {` occurs (fork 10481, upstream 8789).
- Imprecise: an unknown action name passes through both normalizers unchanged (fork ActionCatalog.hpp:122 "unknown names pass through"; upstream NeoRotary4Input.cpp:215 `return action;`, ButtonActionList.hpp:113 normalizeButtonMapping). The catalog / normalizeSingleAction edit is needed only for aliases (and, on the fork, for the label in list_actions). The hub step is what makes the action work. Text says a new name "goes in" / "all three files", implying it is required.

## r5 Change how the preview looks
- Context lines all occur and indentation matches (CameraPage.qml:2118 fork; SettingsBridge.hpp:17, .cpp:324, 525; CameraPreviewItem.hpp:15; PreviewWindowRenderer.cpp:705, 1120). Same in upstream.
- Wrong: the steps are incomplete and not marked with "…", so typed in as shown it does not compile or draw. Missing: SettingsBridge getter, setter, NOTIFY signal, member (Q_PROPERTY alone fails moc); CameraPreviewItem.cpp setter/member/signal; `bool zebraEnabled` in PreviewWindowRenderer.hpp:129 state struct and its copy at PreviewWindowRenderer.cpp:1907 (+ cache compare 1951); `needsProcessing` (2042, 2277, 2447) so the shader is skipped when only the new aid is on; the `glUniform1i(...)` calls (2100, 2328). Also serializeCurrentSettings/apply (SettingsBridge.cpp:2142, 2234) for presets.
- Example not sound: a centre cross already exists (Center marker, type "Crosshair", CameraPage.qml:2625, set_center_marker_enabled in Core). Both modes.

## r6 Change what is written to disk
- Wrong: ImageDescription (270) is already written from the clip name: CdngEncoder.cpp:1673-1674 fork (`appendAscii(ifd, 270, metadata.clipName); // ImageDescription`), CdngEncoder.cpp:1553-1554 upstream. Adding `appendAscii(ifd, 270, metadata.imageDescription)` writes tag 270 twice (invalid TIFF). The DISK check would show the clip name.
- Wrong note: "TIFF wants tags in number order: 270 goes before 272". IfdBuilder.hpp:101-105 sorts by tag in build (identical upstream); existing code adds 285 before 271.
- Context lines occur: `out.uniqueCameraModel = uniqueCameraModelForSensor(sensorFamily, dngModel);` (fork CameraController.cpp:4070, upstream 3158); `std::string uniqueCameraModel = "Blackmagic Micro Cinema Camera";` (CdngEncoder.hpp:87 / 77); `if (!metadata.model.empty())` + `appendAscii(ifd, 272, metadata.model);` (1679-1680 / 1559-1560).
- Not checked: first frame name `_000000001.dng` (frame index base).

## Recheck

Second checker. Every claim re-read at fork (Core 01f170c, UI 7ea9afc) and upstream-1.6.0 worktrees.

| # | Item | Verdict | Why |
| --- | --- | --- | --- |
| 1 | r6 example + CAM/RECS/DISK diffs | stands | Tag 270 is already written from the clip name: CdngEncoder.cpp:1673-1674@cinemate-port, :1553-1554@upstream-1.6.0. No 315 (Artist) anywhere in src/ in either tree; 272 is written only at CdngEncoder.cpp:1680 / :1560, so the RECS context is the one IFD writer. `out` is `CdngEncoder::Metadata` (CameraController.cpp:4056@cinemate-port), the struct at CdngEncoder.hpp:31 whose field list holds `uniqueCameraModel = "Blackmagic..."` (:87 fork, :77 upstream). Correction as reported. |
| 2 | r6 RECS note | stands | IfdBuilder::buildAt calls sort() first (IfdBuilder.hpp:113-115), sort() orders by tag (:101-105); file identical in both trees. Existing code adds 285 before 271. Wording tightened. |
| 3 | r5 RENDER file/note/diff | stands, severity imprecise, corrected differently | The note's mechanism is true, but the diff as shown never sets or uploads the uniform: zebra needs PreviewCacheState field (PreviewWindowRenderer.hpp:129), copy in currentPreviewState (.cpp:1907), glUniform1i (.cpp:2100, 2328), needsProcessing (.cpp:2042, 2277; else passthrough, 2284) and the cache compare (.cpp:1951). Same lines upstream (range 1890-2470 byte-identical). Corrected diff uses greppable context lines and the invertPreview names from item 5. |
| 4 | r5 UICONF note/diff | stands, imprecise, corrected differently | The setter is the only writer of UI.conf: `if (!m_externalSettingsSyncing) m_settings.setValue("zebraEnabled", value);` SettingsBridge.cpp:613@cinemate-port, :603@upstream. Diff shows reads only. Correction adds the setter line and a "…" for getter/signal/member; presets in the note. |
| 5 | r5 example | stands | Centre cross exists: `visible: guideOverlay.centerMarkerEnabled && guideOverlay.centerMarkerType === "Crosshair"` CameraPage.qml:2625,2634@cinemate-port, :2488,2497@upstream; drawn in QML. No "invert" in PreviewWindowRenderer.cpp in either tree, so invertPreview is new. |
| 6 | r4 up.forget | stands (official, imprecise) | Upstream: all three normalizeSingleAction end `return action;` (GpioInput.cpp, NeoRotary4Input.cpp, Pcf8574Input.cpp, just above normalizeAction); normalizeButtonMapping only drops a mapping on a parse error (ButtonActionList.hpp:113-119); no validator; unknown names reach the hub, which logs at ApertarCoreApp.cpp:8954. Only aliases need the *Input.cpp edit. |
| 7 | r4 HWIN fork note | dropped | Wrong correction. On the fork an unlisted name is an ERROR: hwconf::validate classify() knows only catalog names (ActionCatalog.hpp:181-186) and adds `unknown_action` with error=true, "Core logs it and does nothing" (HardwareConfigText.hpp:960-964); HardwareConfigStore.cpp:336-341 refuses the save ("Not saved: ... new error"). So the fork note "goes in the one list" is right. |
| 7 | r4 HWIN up.note | stands (official, imprecise) | Same evidence as 6. |

## Final discrepancies

### F1. RECIPES.r6 example + steps[CAM].diff + steps[RECS].diff + steps[DISK].diff (both, wrong)
- Map says: example "An extra DNG tag: ImageDescription (270)"; CAM `+    out.imageDescription = "Apertar";`; RECS `+        std::string imageDescription;` / `+        if (!metadata.imageDescription.empty())` / `+            appendAscii(ifd, 270, metadata.imageDescription);`; DISK `exiftool -ImageDescription ...`
- Code says: src/cdng/CdngEncoder.cpp:1673-1674@cinemate-port and :1553-1554@upstream-1.6.0 `if (!metadata.clipName.empty())` / `appendAscii(ifd, 270, metadata.clipName); // ImageDescription`. Tag 270 already written; recipe writes it twice.
- Corrected:
  - example: `An extra DNG tag: Artist (315)`
  - CAM diff:
    ```
         out.uniqueCameraModel = uniqueCameraModelForSensor(sensorFamily, dngModel);
    +    out.artist = "Apertar";
    ```
  - RECS diff:
    ```
             std::string uniqueCameraModel = "Blackmagic Micro Cinema Camera";
    +        std::string artist;

             if (!metadata.model.empty())
                 appendAscii(ifd, 272, metadata.model);
    +        if (!metadata.artist.empty())
    +            appendAscii(ifd, 315, metadata.artist);
    ```
  - DISK diff: `exiftool -Artist /Volumes/…/cDNG_…/…_000000001.dng`

### F2. RECIPES.r6.steps[RECS].note (both, wrong)
- Map says: "A field, and the tag in the IFD. TIFF wants tags in number order: 270 goes before 272."
- Code says: src/cdng/IfdBuilder.hpp:113-115 (both trees) `uint32_t buildAt(...)` { `sort();` ...; :101-105 sorts `a.tag < b.tag`.
- Corrected: `A field, and the tag in the IFD. The IfdBuilder sorts tags by number itself, so the order of the appendAscii lines does not matter.`

### F3. RECIPES.r5.steps[RENDER] file + note + diff (both, imprecise)
- Map says: file "src/CameraPreviewItem.hpp + src/PreviewWindowRenderer.cpp"; note "The item carries the flag to the renderer, which passes it to the shader as a uniform."; diff has only Q_PROPERTY, `uniform int uCenterCross;`, glGetUniformLocation.
- Code says: zebra also needs src/PreviewWindowRenderer.hpp:129 `        bool zebraEnabled = false;`, PreviewWindowRenderer.cpp:1907 `        state.zebraEnabled = m_item->zebraEnabled();`, :2042/:2277 `    const bool needsProcessing = state.zebraEnabled`, :2100/:2328 `glUniform1i(... state.zebraEnabled ? 1 : 0);`, :1951 cache compare (all @cinemate-port, same lines @upstream-1.6.0).
- Corrected (names follow F5):
  - file: `src/CameraPreviewItem.hpp / .cpp + src/PreviewWindowRenderer.hpp / .cpp`
  - note: `The item carries the flag into the renderer's state; the renderer uploads it as a uniform. Add it to needsProcessing and the cache compare too, or the shader is skipped.`
  - diff:
    ```
         Q_PROPERTY(bool zebraEnabled READ zebraEnabled WRITE setZebraEnabled NOTIFY zebraEnabledChanged)
    +    Q_PROPERTY(bool invertPreviewEnabled READ invertPreviewEnabled WRITE setInvertPreviewEnabled NOTIFY invertPreviewEnabledChanged)
         …  getter, setter, signal, member: copy zebra's

     // PreviewWindowRenderer.hpp, PreviewCacheState
             bool zebraEnabled = false;
    +        bool invertPreviewEnabled = false;

     // currentPreviewState
             state.zebraEnabled = m_item->zebraEnabled();
    +        state.invertPreviewEnabled = m_item->invertPreviewEnabled();

     // fragment shader
         uniform int uZebraEnabled;
    +    uniform int uInvertPreview;
    +    // if (uInvertPreview == 1) colour.rgb = 1.0 - colour.rgb;

     // after linking the program (and the 2D and planar ones)
             m_uZebraEnabledLoc = glGetUniformLocation(m_processProgram, "uZebraEnabled");
    +        m_uInvertPreviewLoc = glGetUniformLocation(m_processProgram, "uInvertPreview");

     // drawing (both paths)
         const bool needsProcessing = state.zebraEnabled
    +                                 || state.invertPreviewEnabled
         …
    +        glUniform1i(m_uInvertPreviewLoc, state.invertPreviewEnabled ? 1 : 0);
    ```

### F4. RECIPES.r5.steps[UICONF] note + diff (both, imprecise)
- Map says: note "A property stored in UI.conf, read at start and again when the file changes (so a WebUI change shows up)."; diff shows Q_PROPERTY, constructor read, pollExternalSettings only.
- Code says: the write to UI.conf is in the setter: src/SettingsBridge.cpp:613@cinemate-port, :603@upstream-1.6.0 `    if (!m_externalSettingsSyncing) m_settings.setValue("zebraEnabled", value);`; getter/signal/member SettingsBridge.hpp:111,333,446@cinemate-port (99,307,414@upstream); presets SettingsBridge.cpp:2142,2234@cinemate-port (2033,2121@upstream).
- Corrected (names follow F5):
  - note: `A property stored in UI.conf, read at start and again when the file changes (so a WebUI change shows up). Copy zebraEnabled's getter, setter, signal and member; add it to serializeCurrentSettings and the preset apply too.`
  - diff:
    ```
         Q_PROPERTY(bool zebraEnabled READ zebraEnabled WRITE setZebraEnabled NOTIFY zebraEnabledChanged)
    +    Q_PROPERTY(bool invertPreviewEnabled READ invertPreviewEnabled WRITE setInvertPreviewEnabled NOTIFY invertPreviewEnabledChanged)
         …  getter, signal, member: copy zebra's

     // setter (copy setZebraEnabled): this line writes UI.conf
         if (!m_externalSettingsSyncing) m_settings.setValue("zebraEnabled", value);
    +    if (!m_externalSettingsSyncing) m_settings.setValue("invertPreviewEnabled", value);

     // constructor
         m_zebraEnabled = m_settings.value("zebraEnabled", false).toBool();
    +    m_invertPreviewEnabled = m_settings.value("invertPreviewEnabled", false).toBool();

     // pollExternalSettings
         setZebraEnabled(m_settings.value(QStringLiteral("zebraEnabled"), m_zebraEnabled).toBool());
    +    setInvertPreviewEnabled(m_settings.value(QStringLiteral("invertPreviewEnabled"), m_invertPreviewEnabled).toBool());
    ```
    (The setter's `+` line lives in the new setInvertPreviewEnabled, not under zebra's line; the zebra line is the pattern to copy.)

### F5. RECIPES.r5.example (+ QML diff names) (both, wrong)
- Map says: "A new aid: a centre cross"
- Code says: qml/CameraPage.qml:2625,2634@cinemate-port and :2488,2497@upstream-1.6.0 `visible: guideOverlay.centerMarkerEnabled && guideOverlay.centerMarkerType === "Crosshair"`. The aid exists, drawn in QML, not a shader.
- Corrected:
  - example: `A new aid: invert the preview`
  - QML diff:
    ```
                 zebraEnabled: root.settingsState ? root.settingsState.zebraEnabled : false
    +            invertPreviewEnabled: root.settingsState ? root.settingsState.invertPreviewEnabled : false
    ```
  - UICONF and RENDER diffs: as in F4 and F3.

### F6. RECIPES.r4.up.forget (official, imprecise)
- Map says: "A new action name goes into all three *Input.cpp files. The hardware file is read once at start: restart Core"
- Code says: upstream normalizeSingleAction ends `    return action;` in GpioInput.cpp, NeoRotary4Input.cpp, Pcf8574Input.cpp; unknown names reach handleSingleHardwareInputAction, which logs `Hardware input action ignored: unknown action` only when no block matches (ApertarCoreApp.cpp:8954@upstream-1.6.0).
- Corrected: `Aliases for a new action (sharp_plus) go into all three *Input.cpp files; the name itself only needs the hub. The hardware file is read once at start: restart Core`

### F7. RECIPES.r4.steps[HWIN].up.note (official, imprecise)
- Map says: "Upstream keeps the action names in each input class: add the new names to normalizeSingleAction in all three files."
- Code says: as F6; upstream normalizeSingleAction maps aliases and passes other names through (`    return action;`).
- Corrected: `Upstream keeps the aliases in each input class: add them to normalizeSingleAction in all three files. A name with no aliases passes through as is.`

(The fork HWIN note stays: on the fork an uncatalogued name is a validation error and the WebUI refuses the save, HardwareConfigText.hpp:960-964, HardwareConfigStore.cpp:336-341@cinemate-port.)
