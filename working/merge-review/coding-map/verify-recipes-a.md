# verify-recipes-a: RECIPES r1, r2, r3 (first 3 of 6)

Checked @cinemate-port (Apertar-Core 01f170c, Apertar-UI 7ea9afc) and @upstream-1.6.0.

## Discrepancies
1. r1 QML step, both: `Button {` is not a type in CameraPage.qml (imports: QtQuick, Apertar 1.0, TimelapseIntervals.js; no QtQuick.Controls). Also the ISO dropdown sits in a Row whose four TopDropdownStat widths are computed to fill the row, so an extra child overflows.
2. r2 QML step, both: applyIso(v) is at 24 spaces inside `if (root.controlBridge) {`, else-branch sets root.iso = v. Diff shows it at 20 spaces without guard.
3. r2 BRIDGE step, both: no getter, signal, setter (setSharpness) or member; as typed it does not compile.
4. r2 CAM step, both: reader line missing; note says "matching reader below it" but reader (CC:819 fork, 657 up, `key == "iso"`) is ABOVE writeCaptureSettings (936 / 742).
5. r3 WEBPAGE step, both: set_sharpness line placed right after set_iso in the unbraced else chain, so it runs on every ISO click (Number("Auto") = NaN). No sharpnessOptions element or buildOptionButtons, so no picker although the example says "badge with a picker".

## Checked and correct
- r1: applyIso exists (UI hpp:180 fork, 112 up); set_iso branch in ApertarCoreApp.cpp (fork 12968, up 9242) matches both diff lines; same:true true both. QML context lines (CameraPage.qml 3102-3110 fork, 2940-2948 up) match.
- r2: settingsBody (fork 313/321, up 167/174), settingsEvent (CC 173 fork, CC 145 up), buildWebStateJson (fork 9298/9485, up 7711/7861) are the three copies; `uint32_t iso = 800;` in CaptureSettings (Types.hpp 158 / 127); applySettingsLocked(next, false) = no reconfigure; controlsForSettings, controlInfoHas, writeCaptureSettings exist; Core handler lines match; `sharpness` absent from code (example is new); applyCoreState next to setIso (fork 1561, up 1374); isoBadge/set_iso web lines match in both modes (fork 15402/15944, up 9495/9888), up-override correct.
- r3: id="isoBadge" class badge, renderSnapshot, 1 s poll (fork 20954, up 11609), /api/state uses buildWebStateJson, "compiled in" note true; both diffs' context lines match their mode.

## Recheck

Second checker. Re-derived each item @cinemate-port (Core 01f170c, UI 7ea9afc) and @upstream-1.6.0.

| # | Item | Verdict | Why |
| --- | --- | --- | --- |
| 1 | r1.steps[0] QML | corrected differently | Confirmed: CameraPage.qml:1-3 (both refs) imports only QtQuick, Apertar 1.0, TimelapseIntervals.js, so `Button` is not a type. Confirmed: the top Row (CameraPage.qml:3033 fork, 2877 up) holds four TopDropdownStat of width `(parent.width - root.topSettingsButtonSize - (root.topControlsSpacing * 4)) / 4` plus the settings button (width `root.topSettingsButtonSize`, :3190 fork), so it is full. The first checker's hand-made Rectangle+MouseArea is long and not the Apertar way: Apertar has its own button, `ActionTile` (qml/ActionTile.qml, `property string label`, `signal clicked()`, width 200; same file in both refs, used in SettingsPage.qml:2504 up and ClipNameCard.qml:364 fork). Correction uses ActionTile, placed after the Row with x/y from existing root properties (topControlsSideMargin :109, topControlsTopMargin :110, topStatHeight :112, both refs). Parent of the Row is `Item { id: dynamicOverlay }`, so x/y apply. |
| 2 | r2.steps[0] QML | stands, extended | Confirmed: applyIso(v) at 24 spaces inside `if (root.controlBridge) {` with `else { root.iso = v }` (CameraPage.qml:3103-3107 fork, 2941-2945 up). Map's minus line is at 20 spaces and drops the guard; the copied else would still write root.iso. Correction kept, else body simplified. Also found while re-deriving: the copy keeps `isOpen: root.openDropdown === "iso"` and the "iso" toggle key (both refs), so ISO and sharpness would open together; on the fork it also keeps `displayValue: root.controlBridge ? root.controlBridge.isoInUse : ""` (:3092), so it would show the ISO; and a fifth TopDropdownStat overflows the full Row (see 1). Note field corrected for these. |
| 3 | r2.steps[2] BRIDGE | stands, severity imprecise | Confirmed: iso has Q_PROPERTY (hpp:17), getter `QString iso() const;` (hpp:99 fork / 64 up), `void isoChanged();` (:223 / :147), `void setIso(const QString &value);` (:344 / :246), `QString m_iso = QStringLiteral("800");` (:382 / :279), setIso body (.cpp:2481 / 2239). Map diff calls setSharpness and names sharpness/sharpnessChanged without declaring any. A sketch, not false about the code, so imprecise, not wrong. Corrected diff adds the four declarations and the setter body, each next to its iso twin. |
| 4 | r2.steps[4] CAM | stands | Confirmed: reader is `loadPersistedCaptureSettings` (CC.cpp:776 fork / 616 up); `else if (key == "iso")` at :819 / :657 is ABOVE `void writeCaptureSettings` at :936 / :742 (writer line :943 / :748). Map says "the matching reader below it" and shows no reader line, so the value would be saved and never loaded. Correction names the function. |
| 5 | r3.steps[0] WEBPAGE | stands | Confirmed: set_iso is the unbraced `else` of the Auto/Lock chain inside the isoOptions callback (WCP.cpp:15937-15948 fork, 9883-9892 up), so a line added after it runs on every ISO click, with Number("Auto") = NaN. No picker element or buildOptionButtons call for sharpness, although the example says "a badge with a picker". The isoOptions call sits inside renderSnapshot (:15214 fork / :9327 up), so `snapshot` is in scope; `showToast` exists (:12990 / :7804); buildOptionButtons(containerId, options, currentValue, onClick, columns) (:15025 / :9146). Correction kept, HTML lines merged. Also: the map's set_iso context line has 6 code spaces, real is 12; the correction drops that line. |

## Final discrepancies

Map prefix convention: context lines carry one leading space before the code, + lines carry "+".

### 1. RECIPES.r1.steps[0] (QML), both, wrong
- Map says (diff): `+            Button {` / `+                text: "ISO 800"` / `+                onClicked: if (root.controlBridge) root.controlBridge.applyIso("800")` / `+            }`, placed inside the top Row; note "Add the button next to the ISO dropdown. It calls the bridge method the dropdown already uses."
- Code says: Apertar-UI/qml/CameraPage.qml:1-3@cinemate-port and @upstream-1.6.0 `import QtQuick` / `import Apertar 1.0` / `import "TimelapseIntervals.js" as Intervals` (no QtQuick.Controls). Row at :3033 fork / :2877 up, four stats of width `(parent.width - root.topSettingsButtonSize - (root.topControlsSpacing * 4)) / 4` plus the settings button: the Row is full. Apertar's button: qml/ActionTile.qml:6 `property string label: ""`, :24 `signal clicked()` (both refs).
- Corrected note: `Add a button under the top row (the row is full). It calls the bridge method the ISO dropdown already uses. Apertar's own button is ActionTile: this page does not import QtQuick.Controls.`
- Corrected diff:
```
                 onOptionSelected: function(v) {
                     if (root.controlBridge) {
                         root.controlBridge.applyIso(v)
                     …
         }   // end of the top Row
+        ActionTile {
+            x: root.topControlsSideMargin
+            y: root.topControlsTopMargin + root.topStatHeight + 8
+            label: "ISO 800"
+            onClicked: if (root.controlBridge) root.controlBridge.applyIso("800")
+        }
```

### 2. RECIPES.r2.steps[0] (QML), both, imprecise
- Map says (diff): `                 onOptionSelected: function(v) {` / `-                    root.controlBridge.applyIso(v)` / `+                    root.controlBridge.applySharpness(v)`; note "Copy the ISO dropdown block and point it at the new property and method."
- Code says: Apertar-UI/qml/CameraPage.qml:3102-3107@cinemate-port (2940-2945@upstream-1.6.0): `                onOptionSelected: function(v) {` / `                    if (root.controlBridge) {` / `                        root.controlBridge.applyIso(v)` / `                    } else {` / `                        root.iso = v` / `                    }`. Same block: `isOpen: root.openDropdown === "iso"` (both), `displayValue: root.controlBridge ? root.controlBridge.isoInUse : ""` (fork :3092). Row is full (see 1).
- Corrected note: `Copy the ISO dropdown block and point it at the new property and method. Give it its own dropdown key instead of "iso", drop any displayValue/valueItalic lines, and change the /4 widths to /5: the row is full.`
- Corrected diff (tail, from onOptionSelected):
```
                 onOptionSelected: function(v) {
                     if (root.controlBridge) {
-                        root.controlBridge.applyIso(v)
+                        root.controlBridge.applySharpness(v)
-                    } else {
-                        root.iso = v
                     }
```

### 3. RECIPES.r2.steps[2] (BRIDGE), both, imprecise
- Map says: note "A property QML can show, a method QML can call, and one line that reads Core's state."; diff adds the Q_PROPERTY, applySharpness and a setSharpness(...) call only.
- Code says: Apertar-UI/src/ApertarControlBridge.hpp@cinemate-port :17 `Q_PROPERTY(QString iso READ iso NOTIFY isoChanged)`, :99 `QString iso() const;`, :223 `void isoChanged();`, :344 `void setIso(const QString &value);`, :382 `QString m_iso = QStringLiteral("800");`; .cpp:2481 `void ApertarControlBridge::setIso(const QString &value)` (upstream hpp :64/:147/:246/:279, .cpp:2239).
- Corrected note: `A property QML can show (getter, signal, setter and member, like iso), a method QML can call, and one line that reads Core's state.`
- Corrected diff:
```
     Q_PROPERTY(QString iso READ iso NOTIFY isoChanged)
+    Q_PROPERTY(QString sharpness READ sharpness NOTIFY sharpnessChanged)
     QString iso() const;
+    QString sharpness() const { return m_sharpness; }
     Q_INVOKABLE bool applyIso(const QString &displayValue);
+    Q_INVOKABLE bool applySharpness(const QString &value);
     void isoChanged();
+    void sharpnessChanged();
     void setIso(const QString &value);
+    void setSharpness(const QString &value);
     QString m_iso = QStringLiteral("800");
+    QString m_sharpness;

+bool ApertarControlBridge::applySharpness(const QString &value)
+{
+    if (!sendCoreCommand(QStringLiteral("set_sharpness"), { { QStringLiteral("value"), value.toDouble() } }))
+        return false;
+    setSharpness(value);
+    return true;
+}

+void ApertarControlBridge::setSharpness(const QString &value)
+{
+    if (m_sharpness == value)
+        return;
+    m_sharpness = value;
+    emit sharpnessChanged();
+}

 // in applyCoreState, next to setIso(…):
+        setSharpness(QString::number(state.value(QStringLiteral("sharpness")).toDouble()));
```

### 4. RECIPES.r2.steps[4] (CAM), both, wrong
- Map says: note "... copy 2 of the state, and saving it."; diff `// writeCaptureSettings, and the matching reader below it:` then only `output << prefix << "iso=" << s.iso << '\n';` and the + sharpness output line.
- Code says: Apertar-Core/src/camera/CameraController.cpp@cinemate-port :776 `CaptureSettings loadPersistedCaptureSettings(...`, :819-820 `            else if (key == "iso")` / `                settings.iso = static_cast<uint32_t>(std::stoul(value));`, :936 `void writeCaptureSettings(...)`, :943 `    output << prefix << "iso=" << s.iso << '\n';` (upstream :616, :657-658, :742, :748). Reader is above the writer.
- Corrected note: `The field, a setter like setIso, the libcamera control, copy 2 of the state, and saving and loading it.`
- Corrected diff (last block, replacing from `// writeCaptureSettings, and the matching reader below it:`):
```
 // loadPersistedCaptureSettings (the reader, above the writer):
             else if (key == "iso")
                 settings.iso = static_cast<uint32_t>(std::stoul(value));
+            else if (key == "sharpness")
+                settings.sharpness = std::stof(value);

 // writeCaptureSettings (the writer):
     output << prefix << "iso=" << s.iso << '\n';
+    output << prefix << "sharpness=" << s.sharpness << '\n';
```

### 5. RECIPES.r3.steps[0] (WEBPAGE), both (diff and up.diff), wrong
- Map says: note "Three places in the one big string: the element, the render of each poll, and the command."; diff `// the option click` / `       await sendCommand({ cmd: "set_iso", value: Number(value) });` / `+      await sendCommand({ cmd: "set_sharpness", value: Number(value) });`; example "as a badge with a picker".
- Code says: Apertar-Core/src/web/WebControlPage.cpp:15937-15948@cinemate-port (9883-9892@upstream-1.6.0): `      buildOptionButtons("isoOptions", availableIsoOptionsForSnapshot(snapshot), ...async (value) => {` ... `          else` / `            await sendCommand({ cmd: "set_iso", value: Number(value) });` / `        } catch (error) {` / `          showToast(error.message, true);`. Picker element :4528 / :2553 `<div class="pill-grid" id="isoOptions"></div>`. Inside renderSnapshot (:15214 / :9327).
- Corrected note: `Four places in the one big string: the badge, the picker element, the render of each poll, and the picker's buildOptionButtons call that sends the command.`
- Corrected diff (fork; for up.diff only the isoBadge context line differs and stays as the map has it: `      setText("isoBadge", snapshot.iso_auto ? "ISO Auto" : ("ISO " + isoLabel));`):
```
 <!-- the page HTML: next to the ISO badge and the isoOptions picker -->
+<span id="sharpnessBadge" class="badge"></span>
+<div class="pill-grid" id="sharpnessOptions"></div>

 // renderSnapshot: runs after every 1 s poll
       setText("isoBadge", "ISO " + isoLabel);
+      setText("sharpnessBadge", "Sharp " + snapshot.sharpness);

 // the picker, next to buildOptionButtons("isoOptions", ...) in renderSnapshot
+      buildOptionButtons("sharpnessOptions", ["0", "1", "2", "4"], String(snapshot.sharpness), async (value) => {
+        try {
+          await sendCommand({ cmd: "set_sharpness", value: Number(value) });
+        } catch (error) {
+          showToast(error.message, true);
+        }
+      });
```
