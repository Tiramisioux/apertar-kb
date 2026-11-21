# Fix log: slop and bad solutions in the cinemate port, and how each was fixed

Asked for by Patrik on 2026-11-17. It has two jobs:

1. **A record.** One entry per fix commit on the improvement branch (`claude/awesome-pasteur-qzsiow`), in the
   same order as `git log`, under the same subject. Reading this page top to bottom is reading the commit
   history with the thinking added.
2. **Something to learn from.** Each entry says how the problem could have been spotted, which options there
   were, why one was chosen, and which rule it teaches. Written for an intermediate coder: you know C++, a
   camera stack and git, you are newer to this code base, to Qt/QML and to C++ files of this size. A C++ or Qt
   idea that an entry leans on gets one line of explanation the first time it appears.

To follow along in git:

```bash
git -C ~/Documents/Apertar/Apertar-Core log --reverse --oneline cinemate-port..claude/awesome-pasteur-qzsiow
```

```bash
git -C ~/Documents/Apertar/Apertar-Core show <sha>
```

## How an entry is laid out

| Part | Holds |
| --- | --- |
| Title | `<n>. <commit subject>`, then repo and sha. `n` counts in commit order per repo (C = Core, U = UI, D5 / D2 = the imx585 / imx283 driver) |
| Kind, finding | One of the kinds below, and the id in `fix-list.md` |
| What was there | What the port did, with `path:line@cinemate-port` and a few lines of the code |
| Why it is a problem | What goes wrong, or what the original developer would trip over. How original Apertar does the same kind of thing, with `path:line@upstream-1.6.0` |
| How to spot it | The grep, the question or the smell that finds this kind of problem |
| Options | The ways it could be fixed, one line each, with the cost of each |
| Chosen, and why | The reasoning: why this option fits Apertar best, what was given up |
| After | The same few lines of code after the fix |
| Checked | What was run here (build, host test, a browser against `--simulate`) and what still needs the camera, with the command |
| Rule | The one-line rule to take away. Rules collect in `apertar-conventions.md` |

Kinds: **mismatch** (the port did it its own way where original Apertar has a pattern), **removed** (something
original Apertar offers went missing), **stock** (a stock camera would behave differently after the merge),
**slop** (internal numbers, narrated history, leftovers, over-built code), **bug**, **board** (works on one
Raspberry Pi model only), **protocol**, **security**.

A commit that only moves or renames gets a short entry. A commit that changes a design gets the full table.

---

## Entries

## C1. hw, web: the GPIO chip is a setting again, for pins on another chip

Apertar-Core `04fe197`. Kind: **removed** (and a hidden **board** assumption). Finding: owner request 16.

**What was there.** Linux shows every GPIO controller as a "chip", `/dev/gpiochipN`. The Pi's 40-pin header is one
chip. A USB or I2C expander, or a microcontroller with a GPIO driver, is another. Original Apertar lets the
hardware file say which chip the pins are on:

```ini
[gpio_buttons]
enabled=true
chip=auto            # or /dev/gpiochip13
d17=rec
```

Core's readers still honour it on the port (`src/hardware/GpioInput.cpp:343`, `TriggerOutput.cpp:305`,
`RecordingIndicatorOutput.cpp:340` @`cinemate-port`). But the port's Controls page had taken the field away
(`c140c4f`, `f5fe41b`), with this comment in `src/hardware/ControlsModel.hpp:263`:

```cpp
        };   // poll_ms (chips without edge events) and chip stay text-only: the Pi 5's header needs neither
```

And the page's checker assumed every pin number is a header pin. One map for all pins, keyed by the number only
(`src/hardware/HardwareConfigText.hpp:856-870` @`cinemate-port`):

```cpp
    std::map<long, std::pair<std::string, size_t>> claims;      // GPIO number -> who holds it
    ...
        if (!facts.dpiLines.empty() && gpio <= 27)
            add(line, true, "gpio_dpi", ... " is held by the DPI overlay ...");
```

**Why it is a problem.**

| Problem | Effect |
| --- | --- |
| The setting exists in original Apertar (`src/hardware/GpioInput.cpp:431` @`upstream-1.6.0`) and went missing from the port's own UI | A contribution that hides an upstream ability reads as a step back to the original developer |
| "The Pi 5's header needs neither" is a statement about one board | The same thinking shows up elsewhere in the port; it is what the board-support sweep looks for |
| Line 3 of an expander was checked against the header's rules | A valid file was refused: "GPIO 3 is the SCL line of I2C bus 1", "held by the DPI overlay" |
| Apertar's own camera has a DPI screen that holds GPIO 0 to 27 (upstream issue 1) | There, another chip is the only way to have GPIO buttons. The port's page offered none |

**How to spot it.** Ask of every simplification in a UI: "what could the file do before that the page cannot do
now?" Then grep the reader for the keys it still parses and compare with what the page offers:

```bash
grep -n 'key == "' src/hardware/GpioInput.cpp | head -30
```

A comment that names one board ("the Pi 5's ...") as the reason to drop something is a flag by itself.

**Options.**

| Option | Cost |
| --- | --- |
| A. Put the text field back as it was before `c140c4f`, nothing else | 2 lines. But the checker still refuses valid files, and the pin dropdowns still list header pins 4 to 27 |
| B. Field back, and teach the checker and the page that a pin belongs to a chip | About 200 lines in six files. The page then really supports what the file can say |
| C. A new `[gpio_chips]` section that names chips, with every pin written as `chip:line` | A new file format. Original Apertar already has `chip=` per section; this would be a second way to say the same thing |

**Chosen: B, and why.** A is not honest: the page would offer a setting and then reject its use. C invents
format where upstream already has one, which is exactly the kind of mismatch this campaign removes. B keeps
upstream's `chip=` key as the only truth and makes the port's own additions (checker, page) agree with the
reader. What was given up: the tally light's chip gets no field of its own on the page (its row has no settings
card); the page honours the value from the file. Where the checker cannot know (no chip list, as in a host
test), it checks nothing new: `facts.gpioChips` empty means "do not judge".

Three details worth knowing:

- Buttons, encoders and switches share ONE chip. The reader copies `chip=` from `[gpio_buttons]` and from
  `[gpio_encoders]` into the same variable, so the line further down the file wins. The checker now mirrors
  that (`gpioInputChip`) and warns when both sections set it.
- The checker used to limit switch pins to 0..27 while the reader takes 0..63. A checker that is stricter
  than the reader refuses files that would work. It now follows the reader.
- `chip=auto` and the header's real path (`/dev/gpiochip0`) are the same chip. The claim key folds both to
  `"auto"`, so a button on `auto` pin 17 and a trigger on `/dev/gpiochip0` line 17 still collide.

**After.** The settings list (`ControlsModel.hpp`):

```cpp
            {"debounce_ms", "Debounce (ms)", "number", "60", "", 0, 1000},
            {"chip", "GPIO chip", "text", "auto", "", 0, 0},
            {"poll_ms", "Poll every (ms)", "number", "12", "", 2, 1000},   // read only when the chip gives no edge events
```

The claim map has a two-part key now. `std::pair<std::string, long>` is "chip and line together", so the same
line number on two chips are two different keys (`HardwareConfigText.hpp`):

```cpp
    std::map<std::pair<std::string, long>, std::pair<std::string, size_t>> claims;   // (chip, line) -> who
    auto claim = [&](const std::string &chip, long gpio, ...) {
        const bool header = onHeader(chip);
        ...
        if (!header) {                          // another chip: only "does this line exist" applies
            if (const GpioChipFact *fact = chipFact(chip); fact && gpio >= fact->lines)
                add(line, true, "gpio_line", ...);
            return;
        }
        ... the I2C bus 1 and DPI checks, header only ...
    };
```

The page asks one question in three places (pins taken, pin owners, default pin of a new control):

```js
      if (controlsState.dpiLines.length > 0 && controlsGpioChipOnHeader(controlsInputGpioChip()))
        for (let pin = 0; pin <= 27; ++pin)
          taken.add(pin);                                // the DPI display holds the header's
```

**Checked.**

| Check | Result |
| --- | --- |
| Core builds with and without libcamera, `-Wall -Wextra` | ok |
| The 17 host tests | pass |
| A host check of the new rules, 14 cases (header unchanged, other chip free of DPI and bus 1, line beyond the chip refused, same number on two chips, missing chip, two `chip=` lines) | pass |
| The page in headless Chromium against `apertar-core --simulate`, two chips faked into `get_controls` | chip list, chip line on the card, line limit 27 then 3, save writes `chip=/dev/gpiochip13`, a new button's pin list is 0 to 3 |
| On a Pi with a second gpiochip | **not done**. Needs for example an MCP2221 or an I2C expander with a kernel driver: pick it on Config, Hardware, add a button, press it, read `journalctl -u apertar-core | grep 'GPIO input'` |

A slip caught on the way: the new JS helper was first named `controlsChipLines`. The page already has a
`const controlsChipLines` (its "chips" are the little action pills). Two declarations of one name in one script
is a syntax error that kills the whole page. The helpers are named `controlsGpio...` now. In a 21 000-line page
with no modules, grep a new name before using it.

**Rule.** A page may be simpler than the file, but it must not contradict the reader. When a UI checks input,
it checks what the reader accepts: not more, not less.

---

## C2. core: the default hardware file template is the 720x720 screen again

Apertar-Core `7dc6f7a`. Kind: **stock**. Findings: App-2-F1, X-knobs-2, X-stock-behaviour-1 (blocker).

## U1. ui: the display fallback is the 720x720 square screen again

Apertar-UI `6a59d83`. Same finding, the UI half. The two commits belong together.

**What was there.** Two port commits (`7c41a27` in the UI, `7af9f13` in Core) changed what the camera does when
it has no display settings. The UI's built-in fallback (`src/DisplayConfigBridge.cpp:11-12` @`cinemate-port`):

```cpp
constexpr int kDefaultUiWidth = 1920;
constexpr int kDefaultUiHeight = 1080;
...
    m_uiLayout = QStringLiteral("landscape_large");
    m_hdmiExternalOnly = true;
```

and the `[display]` block of the hardware file Core offers when there is none
(`src/ApertarCoreApp.cpp:5089-5098` @`cinemate-port`):

```ini
ui_width=1920
ui_height=1080
ui_layout=landscape_large
hdmi_external_only=true
```

**Why it is a problem.** Those are the values of one rig: Patrik's camera with an HDMI monitor. Original Apertar's
camera has a 720x720 square touch screen, and its defaults say so (`src/DisplayConfigBridge.cpp:11-12`
@`upstream-1.6.0`: `720`, `720`, `"square"`, `false`). `hdmi_external_only=true` tells the touch UI to stay off
the built-in screen. After a merge, a stock camera with no hardware file (a fresh install) or with a file from
before these keys existed would start with its touch UI hidden and laid out for a screen it does not have.

The port commit's own reason was real: with the file moved away during a test, the rig came up square. But the
cure changed the default for everyone to fix one machine's missing file.

**How to spot it.** A default is a statement about the *stock* product. When a diff changes a literal in a
default, a fallback or a template, ask: "whose hardware is this value true for?" Search a diff for changed
defaults like this:

```bash
git diff origin/main cinemate-port -- src | grep -E '^[-+].*(kDefault|= *(true|false);|QStringLiteral\()' | head -40
```

**Options.**

| Option | Cost |
| --- | --- |
| A. Restore the four values in both places | 14 lines. An HDMI rig must carry its `[display]` keys in its own file, as it did before `7c41a27` |
| B. Keep HDMI as default, add detection ("is a DPI panel connected?") | New logic in a boot path the original developer tuned for cold-start time; and a wrong guess hides the touch UI |
| C. Keep the port's values and document them | The stock camera breaks. Not an option for a merge |

**Chosen: A, and why.** It is the smallest change and gives back exactly the original behaviour, which is what
"a stock camera must not notice the merge" means. B might be a good feature one day, but it is a feature, to be
offered to the original developer by itself, not smuggled in as a default. Nothing is lost for the HDMI rig as long
as its file says what it is.

**After.** Both places read as in 1.6.0 again: `720`, `720`, `square`, `hdmi_external_only=false`. Checked by
diffing the six default lines against the `upstream-1.6.0` worktree: no difference.

**Checked.**

| Check | Result |
| --- | --- |
| Core builds with and without libcamera; 17 host tests | ok |
| UI builds (Qt 6.4.2, QML ahead of time) | ok |
| The six UI default lines against `upstream-1.6.0` | identical |
| On the Pi | **before deploying**: `grep -A8 '^\[display\]' ~/apertar-hardware.conf` must show `ui_width`, `ui_height`, `ui_layout` and `hdmi_external_only`. With them, nothing changes for the rig |

Still open, next to this: the port also removed the code that writes a first hardware file when none exists
(`c9d841f`). That is finding X-stock-behaviour-2 and gets its own commit.

**Rule.** Defaults, fallbacks and templates describe the stock camera. Your rig's settings live in your rig's file.

---

## U2. ui: audio meter red outline is off by default

Apertar-UI `2d9cf94`. Finding: X-stock-behaviour-13. Reviewed by a second agent: accept.

**What was there.**

The port added the outline switch with default on. Every place that stated the default said true (all @cinemate-port, tip of lane/ui1):
src/SettingsBridge.hpp:485  bool m_audioRecordedOutlineEnabled = true;
src/SettingsBridge.cpp:371  m_audioRecordedOutlineEnabled = m_settings.value("audioRecordedOutlineEnabled", true).toBool();
qml/SettingsPage.qml:2993   enabled: root.settingsState ? root.settingsState.audioRecordedOutlineEnabled : true
qml/CameraPage.qml:3897,4094  && (!settingsState || settingsState.audioRecordedOutlineEnabled)
qml/ExternalMonitorWindow.qml:994  && (!settingsBridge || settingsBridge.audioRecordedOutlineEnabled)) ? "#73fb2c36"

**Why it is a problem.** A UI.conf with no key for this switch (a fresh install, or a camera upgraded from 1.6.0) got the outline on. A stock camera then drew a red outline on the audio meter during every take with sound. Apertar 1.6.0 has no such outline at all (grep for it in /home/user/wt/ui-upstream/src/SettingsBridge.cpp finds nothing), so a stock camera looked different after the merge. The port's own neighbouring indicators show how an optional aid is set up: off by default, at SettingsBridge.cpp:368-369 (recordingFrameEnabled, frameBufferBarEnabled, both `false`) with QML guards like `!!settingsState && settingsState.recordingFrameEnabled` (CameraPage.qml:4347) and `: false` in SettingsPage.qml:2939.

**How to spot it.** grep -rn '<key>' src qml in the UI and in Apertar-Core/src. Every `value("<key>", true)`, `= true;` member, QML `: true` ternary and `(!bridge || bridge.<key>)` guard is a default saying on. Then ask: does 1.6.0 have this feature at all?

**Options.**

- Flip only the C++ default (cpp:371 and hpp:485): smallest change, but the QML fallbacks still say on, so a page shown before the bridge exists, or a monitor window without one, would still draw the outline.
- Flip the C++ default and the QML fallbacks, using the recording frame's guard pattern: 6 lines in 5 files, and every UI place says the same thing.
- Remove the feature or move it behind a hardware or build switch: bigger than needed. The owner wants the feature, just not on for a stock camera.

**Chosen, and why.** Option 2. The default is now false in the member initialiser and in the QSettings read. QSettings::value(key, default) returns the default when UI.conf has no such key. In QML, `!!x && x.flag` gives false when there is no bridge, while `!x || x.flag` gives true. The QML now matches the frame and buffer bar checks. A user who has already turned it on keeps it, because the value stored in UI.conf wins over the default. What was given up: Core and the WebUI still treat a missing key as on until a Core-lane commit changes ApertarCoreApp.cpp:1907 and WebControlPage.cpp:16157.

**After.**

```
src/SettingsBridge.hpp:485  bool m_audioRecordedOutlineEnabled = false;
src/SettingsBridge.cpp:371  m_audioRecordedOutlineEnabled = m_settings.value("audioRecordedOutlineEnabled", false).toBool();
qml/SettingsPage.qml:2993   enabled: root.settingsState ? root.settingsState.audioRecordedOutlineEnabled : false
qml/CameraPage.qml:3897,4094  && !!settingsState && settingsState.audioRecordedOutlineEnabled
qml/ExternalMonitorWindow.qml:994  && !!settingsBridge && settingsBridge.audioRecordedOutlineEnabled) ? "#73fb2c36"
```

**Checked.** Ran here: /home/user/build/bin/check_ui.sh /home/user/wt/lane-ui1 lane-ui1, which printed PASS with 0 warnings (the Qt UI build with QML compiled ahead of time). Nothing was run on a screen. Still needs the camera: remove the audioRecordedOutlineEnabled line from UI.conf, run `sudo systemctl restart apertar-ui` (or the camera's usual UI restart), then record with sound and check the audio meter has no red outline on the touch screen or on HDMI. Then switch Settings > Monitoring > Audio Recording Outline on and check the outline appears.

**Rule.** A new optional on-screen aid defaults to off everywhere its default is written (C++ member, QSettings read, QML fallback, Core's copy), so a stock camera looks as it did in 1.6.0.


---

## U3. ui: hdmi timecode stays white until red timecode is set in UI.conf

Apertar-UI `ac1fc28`. Finding: X-stock-behaviour-12. Reviewed by a second agent: accept.

**What was there.**

The port's commit da2a9b5 made the HDMI timecode follow the touch screen's switch, and that switch defaults to true (src/SettingsBridge.cpp:370@cinemate-port: m_settings.value("recordingRedTimecodeEnabled", true)).
qml/ExternalMonitorWindow.qml:1208@cinemate-port:
    color: root.recordingActive && (!settingsBridge || settingsBridge.recordingRedTimecodeEnabled) ? "#ff4d4d" : "white"
Result: a stock camera with no new key shows a red HDMI timecode. If the bridge is missing, the timecode also goes red.

**Why it is a problem.** This is a stock-behaviour change nobody asked for. In 1.6.0 the touch timecode is red during a take (qml/CameraPage.qml:3747@upstream-1.6.0: color: root.recording ? "#ff4d4d" : "white"). The HDMI timecode is always white (qml/ExternalMonitorWindow.qml:1129@upstream-1.6.0: color: "white"). A merged port must leave a stock camera looking the same. 1.6.0 already lets a default apply only until the user has stored a value: setDefaultCameraControlsOpacity returns early when m_settings.contains("cameraControlsOpacity") (src/SettingsBridge.cpp:458@upstream-1.6.0). Settings live in SettingsBridge, backed by UI.conf (UIC-5, UIC-13). The HDMI window builds its look from that bridge (QML-10) and guards reads that can be absent (QML-12).

**How to spot it.** For each new SettingsBridge default in a port commit, ask what 1.6.0 showed on each screen. grep the colour or visible line in qml/CameraPage.qml and qml/ExternalMonitorWindow.qml in /home/user/wt/ui-upstream. Watch for a commit message saying "X now follows it too". Watch for guards like (!settingsBridge || bridge.flag) that turn a feature on when the bridge is missing. The Qt idea: a read-only Q_PROPERTY may reuse another property's NOTIFY signal, so QML bindings re-check it whenever that signal fires (1.6.0 does this with valueStepsChanged).

**Options.**

- (a) HDMI follows the switch only once the key is stored in UI.conf: one read-only property using QSettings::contains, one QML line changed; cost: what HDMI does depends on whether the key is stored, which has to be documented
- (b) A separate HDMI key that defaults to off: a new Q_PROPERTY with getter, setter, signal, startup read, re-read when UI.conf changes, presets, and a Settings row with an icon (R3) or else a hidden UI.conf-only key; cost: about 5 files, plus a new setting the owner has to name and place
- (c) Put the HDMI timecode back to always white: one line; cost: drops the owner's feature on HDMI, and it is not one of the report's offered fixes

**Chosen, and why.** (a). It is the smallest change that makes both screens match 1.6.0 on a stock camera. It adds no new UI.conf key and no hidden setting. Once the operator has used the Red Timecode switch (off, then on again), the switch covers touch, HDMI and the WebUI, as the port intended and as its Settings text says. Given up: the Settings text "(touch screen, HDMI, WebUI)" does not mention that HDMI stays white until the switch has been used. Applying a preset whose value equals the current one does not store the key, so HDMI stays white then too, which is consistent. Known edge, left alone: the HDMI window runs as its own process. If the operator toggles the switch off and on before that process re-reads UI.conf, it sees the same value and gets no change signal. It then turns red only after the next settings change or a restart.

**After.**

```
Q_PROPERTY(bool recordingRedTimecodeSet READ recordingRedTimecodeSet NOTIFY recordingRedTimecodeEnabledChanged)

bool SettingsBridge::recordingRedTimecodeSet() const
{
    return m_settings.contains(QStringLiteral("recordingRedTimecodeEnabled"));
}

color: root.recordingActive && !!settingsBridge && settingsBridge.recordingRedTimecodeSet && settingsBridge.recordingRedTimecodeEnabled ? "#ff4d4d" : "white"
```

**Checked.** Run here: /home/user/build/bin/check_ui.sh /home/user/wt/lane-ui1 lane-ui1 printed PASS with 0 warnings (Qt UI built, QML compiled ahead of time). Nothing could be run on a screen here. Still needs the camera: (1) remove any recordingRedTimecodeEnabled line from ~/.config/CinePi/UI.conf, start the UI with an HDMI monitor attached, start a take: touch timecode red, HDMI timecode white. (2) In Settings -> Monitoring switch Red Timecode off and on, start a take: both red. (3) Switch it off, start a take: both white.

**Rule.** A new option must leave a stock camera looking like 1.6.0 on every screen, and the HDMI monitor counts as its own screen.



---

## C3. core, web: audio meter red outline is off by default here too

Apertar-Core `ff4c7c5`. Finding: X-stock-behaviour-13 (the Core half of U2). Made by hand, not by a worker.

**What was there.**

Core does not ask the touch UI for its settings. It reads `UI.conf` itself and keeps its own list of defaults for keys the file lacks, so that the state replies and the WebUI have a value for every setting:

```
src/ApertarCoreApp.cpp:1907   bool audioRecordedOutlineEnabled = true;
src/web/WebControlPage.cpp:16157   formatToggleLabel(uiState.audio_recorded_outline_enabled !== false)
```

**Why it is a problem.** U2 changed the touch UI: a missing key now means "no outline". Core's copy of the default still said "on". On a camera with no such key, the meter had no outline, and the WebUI's Settings pane showed the switch as On. Two programs disagreed about one setting because the default is written in two code bases.

**How to spot it.** When you change a default in the touch UI (`m_settings.value("<key>", <default>)` in `SettingsBridge.cpp`), grep the same key in `Apertar-Core/src`. Core's `UiSettingsSnapshot` struct (ApertarCoreApp.cpp, around line 1880) has a member for every UI.conf key Core publishes, each with its own initial value. In the WebUI string, look for `!== false` (reads "on unless told otherwise") against `=== true` (reads "off unless told otherwise").

**Options.**

- Leave Core alone: the UI is right, the WebUI label is wrong until someone flips the switch once.
- Flip both Core places: 2 lines.
- Make Core stop keeping defaults and publish "unset": a new idea in the protocol, and original Apertar keeps this same hand-written copy for every UI setting. Not ours to redesign.

**Chosen, and why.** Option 2. Original Apertar already lives with the two copies (rule UIC in `apertar-conventions.md`: Core reads UI.conf with its own defaults). The cheap, in-style fix is to keep the copies equal. The neighbours show the two spellings side by side: `recording_frame_enabled === true` for an aid that is off by default, `recording_red_timecode_enabled !== false` for one that is on.

**After.**

```
src/ApertarCoreApp.cpp:1907   bool audioRecordedOutlineEnabled = false;
src/web/WebControlPage.cpp:16157   formatToggleLabel(uiState.audio_recorded_outline_enabled === true)
```

**Checked.** Ran here: both Core builds and the 17 host tests pass. `apertar-core --simulate` with no UI.conf: `GET /api/state` gives `ui.audio_recorded_outline_enabled: false` and still `ui.recording_red_timecode_enabled: true`. The reply shapes are the same as before (only the page is one byte shorter). Still needs the camera: nothing beyond the check named in U2.

**Rule.** A UI.conf default exists three times: touch UI (`SettingsBridge.cpp`), Core (`UiSettingsSnapshot`), WebUI (`=== true` or `!== false`). Change all three in the same piece of work.

---

## C4. core: get_state sends media_state once

Apertar-Core `e4246ee`. Finding: X-protocol-security-6. Reviewed by a second agent: accept.

**What was there.**

src/ApertarCoreApp.cpp:12957@cinemate-port (line 12944 in the sweep report; it has moved since), in the get_state handler's `<<` chain:
    const MediaSnapshot mediaState = mediaSnapshot();
    ...
         << ",\"media_state\":\"" << mediaSnapshot().stateName() << "\""   // second snapshot, extra key
    ...
         << ",\"media_state\":\"" << mediaState.stateName() << "\""
         << ",\"media_alive\":" << (mediaState.mounted() ? "true" : "false")

**Why it is a problem.** The reply is JSON with the same key twice. Most parsers (QJsonDocument, JSON.parse) silently keep the last one, so nothing broke. But the two values come from two separate snapshots, so in a race they can disagree, and the reply is not valid as a clean object. Upstream get_state has no media_state key at all (0 hits in /home/user/wt/core-upstream/src/ApertarCoreApp.cpp). The key is the port's. Upstream builds each reply as flat JSON from values it reads once at the start of the handler (BRIEF "Apertar way": flat JSON, scalar values; conventions C1-S03 for the handleCommand chain).

**How to spot it.** Find keys that are written twice in one handler: `grep -o '\\\\"[a-z_]*\\\\":' file | sort | uniq -d` over the handler's lines. Watch for calls like `mediaSnapshot()` inside a `<<` chain when the handler already holds a local snapshot. To test, grep the raw reply text, because a JSON parser (and any smoke test built on one) hides duplicate keys.

**Options.**

- Delete the first line, the inline mediaSnapshot() one: one line, keeps media_state next to media_alive, both from the one snapshot (chosen)
- Delete the second line: also one line, but then media_state and media_alive come from two different snapshots
- Drop media_state completely to match upstream: breaks the port's WebUI and UI, which read the key

**Chosen, and why.** I deleted the inline mediaSnapshot() line, as the item said. The one media_state key left is read from the same `mediaState` local as media_alive, so the two fields always agree. Nothing was lost: the value is the same and the key position does not matter in JSON.

**After.**

```
         << ",\"recording_fault\":\"" << escapeJson(camera_.recordingFaultName()) << "\""
         << ",\"recording_has_dropped_frames\":" << (camera_.recordingHasDroppedFrames() ? "true" : "false")
    ...
         << ",\"media_state\":\"" << mediaState.stateName() << "\""
         << ",\"media_alive\":" << (mediaState.mounted() ? "true" : "false")
```

**Checked.** Here: the gate (`/home/user/build/bin/check_core.sh /home/user/wt/lane-core1 lane-core1 both tests`) passes. The remaining warnings (StandbyPowerButtonInput.cpp:26, App:4742, CC:7763/7916/1235) were already there and are not in the edited lines. The smoke test (`smoke_core.sh .../apertar-core 8137 /home/user/build/sim/smoke-core1.txt`) shows no diff against smoke-work.txt. That is expected: the script parses JSON, which folds the duplicate key, so it could never have shown it. So I checked the raw text: with `--simulate --web-port 8138`, `curl -s -X POST http://127.0.0.1:8138/api/command -d '{"cmd":"get_state"}' | grep -o '"media_[a-z]*":[^,]*'` now prints media_state once (before the change it would print it twice). Nothing needs the camera.

**Rule.** Read each value into one local at the top of a reply handler, write each key once, and build the reply from those locals.


---

## C5. core: the automatic storage pre-roll is off by default

Apertar-Core `0977dd6`. Finding: X-stock-behaviour-5. Reviewed by a second agent: accept.

**What was there.**

The port turned the pre-roll on whenever nothing was configured. Code in src/util/StoragePreroll.hpp:92-98@cinemate-port:
  inline bool automaticEnabled(const char *envValue, const PrerollConf &conf)
  {
      if (envValue && std::string(envValue) == "0") return false;
      if (envValue && std::string(envValue) == "1") return true;
      return conf.automatic.value_or(true);
  }
The published atomic also started as `std::atomic<bool> automatic{true};` (StoragePreroll.hpp:229). The hardware file template showed "# preroll=on" (src/ApertarCoreApp.cpp:5074).

**Why it is a problem.** Each time Core started, a card went in or a card was formatted, a stock camera wrote a 2 s take at the mode's highest fps. That is about 0.7-1.5 GB. It then deleted the take. While the take ran, Core refused record, photo, format, eject and standby with "Storage pre-roll is running". Original Apertar 1.6.0 has no pre-roll: an unmodified camera never writes media unless the operator asks. Under rule CAM-32 (capture modes and media actions exclude each other, refused with a sentence), the take that is hidden by default blocks the operator's own commands. The port's own plan said "default off at first, never a hidden step" (working/drop-frames/README.md:341).

**How to spot it.** Run `grep -rn "value_or(true)" src/` and, for each hit, ask whether a stock camera without that key would do something original Apertar never does. Also check `std::atomic<bool> x{true}` that mirrors a setting: its start value must match the parse default.

**Options.**

- value_or(false) plus the atomic's start value plus the texts that state the default: 8 lines across 4 files, no change in behaviour once someone has set the switch
- Remove the automatic triggers and keep only the manual command: also fixes it, but drops a feature the owner wants as an option and touches the watcher, the UI controls and set_storage_preroll
- Write preroll=off into the installed hardware file: hides the problem for new installs only and leaves the code default wrong

**Chosen, and why.** I took option 1, as the lead's note asked: only the default changes. The atomic's start value had to change as well. Core reads that atomic in get_state before the first refresh, so leaving it at true would have reported "auto on" for a moment. Nothing was given up. Anyone who wants the warm-up sets preroll=on once, from the WebUI, the Config pane or set_storage_preroll. README.md has no line about the pre-roll default, so nothing was added there (no drive-by doc changes).

**After.**

```
// APERTAR_STORAGE_PREROLL=0|1 (anything else counts as unset) beats the file; absent both: off.
    return conf.automatic.value_or(false);
    std::atomic<bool> automatic{false};
# preroll=on runs it when Core starts, when a card is inserted and after a format (default off); the command storage_preroll always works. Read at each request.
# preroll=off
    check(!automaticEnabled(nullptr, PrerollConf{}), "default off");
```

**Checked.**

Run here:
- The gate (`check_core.sh /home/user/wt/lane-core1 lane-core1 both tests`): both builds pass, and all 17 host tests pass, storage_preroll_test included, which now asserts default off.
- --simulate with no [media] key: `get_state` returns `storage_preroll_auto:false`. The WebUI page (Playwright) shows the On/Off row with Off selected. `set_storage_preroll` on, then off, flips the value.

Side effect, cleaned up: in simulate mode set_storage_preroll writes to /home/pi/apertar-hardware.conf. My test added a [media] section there and a .bak file. I put the file back to its earlier two lines ([gpio_buttons] chip=/dev/gpiochip13) and removed the .bak.

Still needs the camera: start Core with no preroll key, then run `journalctl -u apertar-core -b | grep "storage preroll"`. Expect "reason=start not requested (preroll is off ...)" and no pre-roll clip on the media. Insert a card and format it, and expect the same "not requested" line for each.

**Rule.** A new feature that writes media, uses time or blocks commands is off by default. The operator turns it on.


---

## C6. cdng: lossy DNG drops each file's pages after the write again

Apertar-Core `615b48c`. Finding: X-stock-behaviour-7. Reviewed by a second agent: accept.

**What was there.**

src/lossydng/LossyDngEncoder.cpp:102-105@cinemate-port. The page drop only ran in "writer" mode:
    // The same knob as the cDNG writer (APERTAR_DNG_DONTNEED); lossy takes have no sync thread, so "sync" leaves
    // the pages to the kernel like "off".
    if (dngPageCacheDrop() == DngPageCacheDrop::Writer)
        ::posix_fadvise(fd, 0, 0, POSIX_FADV_DONTNEED);
The default mode is Sync (src/cdng/CdngEncoder.cpp:84-106).

**Why it is a problem.** posix_fadvise(POSIX_FADV_DONTNEED) tells the kernel it may drop a file's cached pages. 1.6.0 calls it on every Lossy DNG file, with no condition (src/lossydng/LossyDngEncoder.cpp:82@upstream-1.6.0). The port changed the default to "sync", which means the drop runs on the once-a-second sync thread after the fsync. Only cDNG files reach that thread: noteWrittenFile is called only in the cDNG branch (src/camera/CameraController.cpp:5294). So a stock Lossy DNG take dropped nothing. Its frames stayed in the page cache until kswapd reclaimed them during the take, which is the pattern the port's own commit adac040 blames for lost frames.

**How to spot it.** grep -rn "dngPageCacheDrop() ==" src/ and, for each hit, ask what happens under the default value. A comment saying "X behaves like off" for the default mode is the smell.

**Options.**

- Drop in the writer for every mode except Off: a one-line condition change, and it brings back 1.6.0's behaviour under the default. Cost: none.
- Send lossy files through noteWrittenFile so the sync thread drops them: this needs the async lossy writer to report each finished path back to CameraController. More code and new coupling.
- Make the default mode depend on the format: this adds a new rule to a knob that both writers share, for no gain over option 1.

**Chosen, and why.** Option 1. In the lossy writer, "sync" now means the same as "writer", because lossy takes have no sync thread for the drop to run on. It is the smallest change and matches 1.6.0 exactly under the default. Given up: lossy files never get the cheaper drop of clean pages after the fsync. The drop runs while the pages are still dirty, which is exactly what 1.6.0 did.

**After.**

```
    // The same knob as the cDNG writer (APERTAR_DNG_DONTNEED). Lossy takes have no sync thread, so "sync" drops
    // here too, as 1.6.0 did after every file; only "off" leaves the pages to the kernel.
    if (dngPageCacheDrop() != DngPageCacheDrop::Off)
        ::posix_fadvise(fd, 0, 0, POSIX_FADV_DONTNEED);
```

**Checked.** Run here: /home/user/build/bin/check_core.sh /home/user/wt/lane-core1 lane-core1 both tests. It built with and without libcamera with 0 warnings, and all 17 host tests passed. The WebUI and socket did not change, so no simulator run was needed. Still needs the camera: a 3-minute Lossy DNG take with default settings and no APERTAR_DNG_DONTNEED set. Run `vmstat 1` during the take and check that the "cache" column stays flat and no frames are lost. Then repeat with APERTAR_DNG_DONTNEED=off to see the old growth for comparison.

**Rule.** When a shared knob changes its default, check every caller still does what it did before, above all callers that cannot use the new mode.


---

## C7. camera: preview temporal denoise switch leaves H.264, ProRes and photo mode alone

Apertar-Core `b923c06`. Finding: X-stock-behaviour-6. Reviewed by a second agent: accept.

**What was there.**

src/camera/CameraController.cpp:7306-7318@cinemate-port. Inside the session's start(), the lambda that picks the file libcamera loads strips TDN for every record format:
        std::string activePath;
        const auto loadablePath = [&](const std::string &path) {
            activePath = path;
            if (!settings.previewTdn) {
                std::string note;
                activePath = tuning::previewTuningPath(path, tuningPipeline, note);
Later, at :7412, `makeProresIspTuning(activePath, ...)` builds the ProRes ISP tuning from that stripped copy. Types.hpp:139 sets `bool previewTdn = false;` ("the raw DNGs never change").

**Why it is a problem.** For H.264 and ProRes the ISP picture is the recording. A switch named "Preview" therefore took temporal denoise out of every stock H.264 and ProRes take, including with a tuning file the user picked, and nothing told the operator. Commit e625c68 only talks about DNGs. Original Apertar loads the resolved tuning file as it is: `applyProcessTuningFile(tuningPath)` at src/camera/CameraController.cpp:5266-5271@upstream-1.6.0, and ProRes derives from `tuningPath`. The rules: N8 (no silent downgrade of what is recorded) and N13 (monitoring changes stay out of the recording). All four reports (X-stock-behaviour-6, X-knobs-4, CC-6-F2, CC-3-F7) agree on the format test. Only CC-3-F7 prefers flipping the default.

**How to spot it.** Ask "for which formats is this picture the recording?" each time a preview, monitor or ISP tweak is added. grep -n "previewTuningPath\|tuningPath\|activePath" src/camera/CameraController.cpp and look for a tuning or ISP change with no isProcessedVideoFormat test near it. Another sign is a commit or comment that says "the DNGs do not change" and says nothing about H.264 or ProRes.

**Options.**

- Strip only when the ISP output is not recorded: `!settings.photoModeEnabled && isProcessedVideoFormat(...)` keeps the full file. One line, keeps the speed gain for raw, and processed takes match 1.6.0 exactly. Cost: the switch does nothing in H.264/ProRes.
- Default previewTdn = true. Upstream look everywhere, but raw shooters lose the measured ISP speed gain and it changes a default the owner chose on purpose.
- Both. Safest, but it overrides the owner's default for raw without need.

**Chosen, and why.** Option 1, the format test, which is the fix the four reports agree on. I used the codebase's own wording for "the ISP output is the recording": `!photoModeEnabled && isProcessedVideoFormat(recordingFormat)`. The same expression is at CC:3507 and CC:11385. Photo mode counts as raw, because stills are developed from the raw frame (writeProcessedStill -> processRawFrameToRgbStill) and not from the ISP. What we give up: in H.264/ProRes the preview stays as expensive as in 1.6.0. Format change check: setRecordingFormat sets requiresReconfigure whenever the current or the next format is H.264/ProRes (CC:11385-11389). applySettingsLocked then calls session_->reconfigure, which runs stop() and then start(settings) (CC:7551-7556). start() runs loadablePath again. A photo-mode toggle also forces a reconfigure (CC:12725). So every change that flips the condition picks the tuning file again (confirmed in code). The journal line still prints "preview_tdn=off active=<path>" for processed formats, and it now shows the full file there. I left it unchanged.

**After.**

```
        // H.264 and ProRes record the ISP output, so they always get the tuning file as it is.
        const bool ispOutputRecorded = !settings.photoModeEnabled && isProcessedVideoFormat(settings.recordingFormat);
        std::string activePath;
        const auto loadablePath = [&](const std::string &path) {
            activePath = path;
            if (!settings.previewTdn && !ispOutputRecorded) {
```

**Checked.** Run here: /home/user/build/bin/check_core.sh /home/user/wt/lane-core1 lane-core1 both tests. Both builds and the 17 host tests pass. The remaining warnings (ApertarCoreApp.cpp:4742, and CC:1235, :7765, :7918 in the build without libcamera) are in code I did not touch. The changed lines sit inside the libcamera session start(), so --simulate cannot exercise them, and no command, state field or WebUI change needed a live run. Still needs the camera: with preview_tdn off, switch to H.264, then ProRes, then cDNG, and run `journalctl -u apertar-core | grep "tuning file"`. H.264 must show the original file as active; ProRes must show the derived file built from the original (the "ProRes colour:" line follows); cDNG must show `~/.cache/apertar-core/tuning/<name>_notdn.json`. Optionally record two dark ProRes takes, one before and one after this change, and compare the noise.

**Rule.** A monitoring or preview setting must never change what is recorded. If the recording comes from the same pipeline stage (here the ISP for H.264/ProRes), gate the preview tweak on the record format.

**Note from the lead.** The commit as pushed (`b923c06`) differs from the text above in one point: when I put it on the improvement branch I widened the test to `settings.photoModeEnabled || isProcessedVideoFormat(...)`, so photo mode also kept the full tuning file. That was wrong, and C10 takes it back. Read C10 for why.


---

## C8. core: test_input refuses script actions, a script needs a button press

Apertar-Core `d1dcdee`. Finding: X-protocol-security-2. Reviewed by a second agent: accept.

**What was there.**

src/ApertarCoreApp.cpp:12399-12421@cinemate-port (testInputReply) ran any saved action list for the key, scripts included:
            if (line.actions.empty() || (line.actions.size() == 1 && line.actions[0] == "none"))
                return errorReply(command.id, "Nothing is assigned to " + row.title + " " + line.label + ".");
            const bool turn = ...;
            handleHardwareInputAction(line.raw, !turn);
remoteN rows also skip the section-on check, so remote0=run_script1 plus test_input was enough.

**Why it is a problem.** test_input is reachable from the LAN (POST /api/command, the WebUI Try button). A client could save remote0=run_script1 and then fire it, and the runner runs /bin/bash -- <file> as pi, which has passwordless sudo on a stock image. So the LAN could start a root shell script with no one at the camera. In original Apertar handleHardwareInputAction is called only from the GPIO, NeoRotary and PCF8574 callbacks and the standby wake (core-upstream src/ApertarCoreApp.cpp:6786-6792, :8613): a script ran only after a physical press. The refusal is an operator sentence per CMD-28 / STY-10, and it sits at the top of the one command's block per CMD-4.

**How to spot it.** grep -n "handleHardwareInputAction" src/ApertarCoreApp.cpp and compare the callers with core-upstream: any caller that is a command handler, not an input callback, is a remote door. Ask: what is the worst action this command can fire, and who can send it?

**Options.**

- Refuse script actions in testInputReply with an operator sentence: a 4-line local change, keeps every other Try action working (chosen).
- Drop test_input altogether: closes the hole but loses the WebUI Try and Remote Controls feature.
- Restrict the script runner (executable, not group/world-writable): changes stock runner behaviour upstream already ships; needs the original developer; left as an optional later step.
- Refuse only in the WebUI JavaScript: useless, the socket and /api/command still accept the command (CMD-27: logic belongs in Core).

**Chosen, and why.** Option 1, as the lead asked: the first step of the verified fix only. It puts back the upstream guarantee (scripts need a press) at the one place the port added a remote door. Given up: a user can no longer Try a script line from the WebUI; they press the button. The runner path checks are untouched.

**After.**

```
            // A script starts from a physical press only, as in 1.6.0.
            for (const std::string &action : line.actions)
                if (hardware::scriptActionSlot(action) >= 0)
                    return errorReply(command.id, "Scripts run from a button, not from the WebUI.");
(line.actions holds each action already in canonical spelling; scriptActionSlot from src/hardware/ButtonActionList.hpp returns the slot 0-5 for run_script/script spellings, -1 otherwise.)
```

**Checked.** Here: the gate (both builds, 17 host tests) passes. In --simulate with the WebUI on 127.0.0.1:8147, set_controls saved remote0=run_script1, remote1=record_toggle, remote2=iso_up,script_2; test_input on remote0 and on remote2 (script inside a sequence) replied {"ok":false,"error":"Scripts run from a button, not from the WebUI."}; remote1 still started and stopped a take; Playwright calling the page's sendTestInput showed the sentence as a toast. The hardware file was restored to its earlier text afterwards. Needs the camera: map a GPIO button to run_script1 in Controls, press the button and check the script runs (e.g. it touches a file), then press Try on that row in the WebUI at http://<pi>:8000 and check the toast and that the file is not touched.

**Rule.** A path that fires hardware actions for a remote client must not reach actions upstream only allows on a physical press; refuse them in Core with an operator sentence.

**Note from the lead.** The worker's comment said "A script runs as root". It does not: the runner starts `/bin/bash` as the user Core runs as (the template says "Runs as pi, without automatic sudo", ApertarCoreApp.cpp:4334@upstream-1.6.0). A wrong "why" in a comment is worse than no comment, so the line was corrected before the push.



---

## C9. camera: preview temporal denoise is on by default, as in 1.6.0

Apertar-Core `3650027`. Findings: CC-3-F7, X-knobs-4, X-stock-behaviour-6 (the default half). Made by hand. **This one changes a default the owner chose on purpose: see "Chosen, and why".**

**What was there.**

```
include/apertar/core/Types.hpp:139@cinemate-port   bool previewTdn = false;   // Off (default) is much faster
```

The setting is saved as `preview_tdn=` in `camera_settings.conf`. When the file has no such line, the struct's initial value decides.

**Why it is a problem.** Temporal denoise (TDN) is the step in the Pi's image processor (the ISP) that blends each frame with the one before it. The tuning file asks for it. Apertar 1.6.0 loads the tuning file as it is. With the port's default, a camera upgraded from 1.6.0 gets a tuning copy without TDN in every raw mode, so its live picture is noisier than before, and nothing on screen says why. C7 already took the recordings (H.264, ProRes) out of it; this is the rest: the monitor picture of a stock camera.

**How to spot it.** For every new member of `CaptureSettings` (Types.hpp), ask: "what does a camera do that has never saved this key?" The initial value in the struct is the answer. If that answer is not what 1.6.0 does, a stock camera changes behaviour on upgrade.

**Options.**

- Keep off by default: the rig stays fast after a settings reset. A stock camera's preview is noisier than under 1.6.0.
- On by default: a stock camera is as before. The rig keeps off through its saved `preview_tdn=false`; only after a settings reset does it have to be switched off again.
- Off only in the heavy mode (4K Clear HDR 16-bit): a hidden coupling between a mode and a monitor setting. Original Apertar has no such automatic coupling for monitor aids.

**Chosen, and why.** On by default. The campaign's first rule is that a camera with no port-specific settings behaves as 1.6.0. The speed gain (about 37 ms down to 6 ms per frame in the ISP back end at 4K Clear HDR 16-bit, the owner's measurement) is real, and it stays one switch away. What was given up: after a factory reset of the settings, the rig drops frames in 4K Clear HDR 16-bit at 25 fps until the switch is turned off again. This is the owner's call to overturn: reverting this one commit restores "off by default" and nothing else.

**After.**

```
include/apertar/core/Types.hpp:139   bool previewTdn = true; // Temporal denoise in the preview ISP of raw takes. Off is much faster; H.264 and ProRes always keep it.
```

**Checked.** Ran here: both builds, the 17 host tests. `apertar-core --simulate` with no settings file: `GET /api/state` gives `preview_tdn: true`. Still needs the camera: `grep preview_tdn` in the rig's `camera_settings.conf`. If the line says `false`, nothing changes for the rig. If it is missing, switch "Preview temporal denoise" off once in the WebUI (Settings, System, Performance).

**Rule.** The initial value of a new setting is what a 1.6.0 camera gets on upgrade. Make it the 1.6.0 behaviour, and let the new behaviour be the saved choice.


---

## C10. camera: photo mode follows the preview temporal denoise switch

Apertar-Core `0d13a6f`. Corrects the lead's own change to C7. Made by hand.

**What was there.** In C7 the worker wrote the test as "H.264 or ProRes video" and noted that photo mode counts as raw, "because stills are developed from the raw frame". When I integrated the commit I overruled that and added photo mode to the modes that always keep the full tuning file:

```
const bool ispOutputSaved = settings.photoModeEnabled || isProcessedVideoFormat(settings.recordingFormat);
```

My reason was a review finding (Camera-headers-F2) that said JPEG, PNG and TIFF stills are saved from the ISP output.

**Why it is a problem.** The finding was wrong on that point, and I did not open the code before acting on it. Processed stills are developed by Core from the raw frame, in 1.6.0 and in the port:

```
src/camera/CameraController.cpp:6845   bool writeProcessedStill(FrameJob &job, ...)
src/camera/CameraController.cpp:6850       job.frame.data = job.rawBytes.data();
src/camera/CameraController.cpp:6852       if (!processRawFrameToRgbStill(job.frame, job.metadata, job.rendering, &image, error))
```

So in photo mode the ISP picture is only the monitor picture. My change made the switch do nothing in photo mode for no reason, and the commit message stated a mechanism that does not exist.

**How to spot it.** A claim of the form "X comes from Y" in a review, a comment or a commit message is a pointer, not a fact. Before changing code because of it, find the function that writes X and read where its input comes from. Here: `grep -n "writeProcessedStill\|processRawFrameToRgbStill" src/camera/CameraController.cpp`, one minute.

**Options.**

- Leave it: harmless for the pictures, but the switch and its texts would lie about photo mode.
- Rewrite the pushed commit: the branch history would look cleaner, but it was already pushed, and a rewritten branch is a trap for anyone who fetched it.
- A small corrective commit: the history shows the misstep and the fix. The clean commit series planned for the end of the campaign folds the two into one.

**Chosen, and why.** The corrective commit. It restores the worker's test exactly and corrects the three texts that repeated the wrong mechanism (README, the Types.hpp comment, the WebUI note).

**After.**

```
        // H.264 and ProRes record the ISP output, so they always get the tuning file as it is.
        const bool ispOutputRecorded = !settings.photoModeEnabled && isProcessedVideoFormat(settings.recordingFormat);
```

**Checked.** Ran here: both builds, the 17 host tests. Still needs the camera: with the switch off, enter photo mode and read `journalctl -u apertar-core | grep "tuning file"`: the line must end in `active=<...>_notdn.json`.

**Rule.** Check a finding against the code before you act on it, also when a reviewer and a skeptic both signed it. Two readers can share one wrong assumption.

---

## C11. camera: reconfigure when a format switch changes the Clear HDR storage depth

Apertar-Core `9bd7610`. Finding: HDR-D1. Reviewed by a second agent: accept.

**What was there.**

src/camera/CameraController.cpp:12723-12727@cinemate-port (same lines at the lane tip before ea120bc):
    bool CameraController::applySettingsLocked(CaptureSettings nextSettings, bool requiresReconfigure, bool commit)
    {
        requiresReconfigure |= nextSettings.photoModeEnabled != settings_.photoModeEnabled;
        requiresReconfigure |= activeIspColorProfile(nextSettings) != activeIspColorProfile(settings_);
        requiresReconfigure |= nextSettings.clearHdr != settings_.clearHdr;
setRecordingFormat (CC:11387-11389) only checked processed stream, size and rawBitDepth. The storage depth, which depends on the format (CC:1640-1643, 1686-1687), reached rawStreamInfo_ only at configure (CC:8615-8622). The copy worker read the format from the new settings_ and the depth from the stale rawInfo (CC:9491-9496).

**Why it is a problem.** If the stream is not reconfigured, the session only swaps controls and settings_, so the stale rawStreamInfo_.bitDepth is used for the take. cDNG -> MLV: the MLV says 12/200/4095 and the packer keeps the low 12 bits of linear 16-bit samples (black at 77 % of white, highs wrap). MLV -> cDNG: a 4096-entry LinearizationTable meets a 16-bit view, writeDngFile throws "Invalid RAW linearization table." and the take fails. In Apertar 1.6.0 the storage depth followed rawBitDepth only (CC:1301-1308@upstream-1.6.0), so setRecordingFormat's rawBitDepth test covered it. Upstream lists the settings that change the stream as `requiresReconfigure |=` lines at the top of applySettingsLocked (CC:8661-8662@upstream-1.6.0). Fork main 57c8fb0 made the depth depend on the format and did not add a line there. This was not a port regression.

**How to spot it.** grep for the function that fills a cached value at configure time (storageRawBitDepthForSettings -> rawStreamInfo_) and list its inputs. Then check that the reconfigure predicate (grep 'requiresReconfigure') changes when any of those inputs changes. Warning sign: a predicate that compares raw settings fields (rawBitDepth) while the value it protects is computed from more fields (clearHdr, recordingFormat, photo mode).

**Options.**

- One `requiresReconfigure |=` line in applySettingsLocked comparing storageRawBitDepthForSettings of next and current: covers every setter, 4 lines, guarded because the helper is libcamera-only
- Extend the predicate in setRecordingFormat: covers only that setter, so a future setter that changes format, photo mode or depth would miss it
- Move clearHdrStoresCodes12 / storageRawBitDepthForSettings out of the libcamera block into a header so the line needs no #if and a host test can call them: a code move that needs the original developer's decision and touches lines the other lane may edit

**Chosen, and why.** Option 1. It is the Apertar pattern: the stream-changing settings are listed as `requiresReconfigure |=` lines in one place. storageRawBitDepthForSettings is defined inside `#if APERTARCORE_HAS_LIBCAMERA` (CC:1443-2268), while applySettingsLocked builds in both configurations. So the new line has the same guard as the other libcamera-only blocks in the file (for example CC:12686-12698). The simulated camera has no session to reconfigure, so nothing is lost there. What we give up: cDNG <-> MLV in 12-bit Clear HDR now restarts the stream (about as long as a size change). There is also no host test. The encoder-level tools/clear_hdr_storage_test.cpp was left out on purpose. It would only show that MlvEncoder and CdngEncoder write what a stale view tells them, and it would pass the same with or without this fix. Testing the fix needs the helper move from option 3.

**After.**

```
    requiresReconfigure |= nextSettings.clearHdr != settings_.clearHdr;
#if APERTARCORE_HAS_LIBCAMERA
    // Clear HDR 12-bit stores 12-bit codes in cDNG and linear 16-bit in MLV; the stream takes the depth at configure.
    requiresReconfigure |= storageRawBitDepthForSettings(nextSettings) != storageRawBitDepthForSettings(settings_);
#endif
```

**Checked.** Ran here: /home/user/build/bin/check_core.sh /home/user/wt/lane-hdr lane-hdr both tests. Both builds pass and all 17 host tests pass. The warnings are in other files or on CC lines this change does not touch (7763, 7916, 1235, nolc build), so none are new. No WebUI or socket test was run: no command or state field changed, and the simulator skips the session. Needs the camera: Clear HDR 12 in cDNG, restart Core, then `set_record_format mlv` and record 2 s. The MLV RAWI must read 16/3201/65535, not 12/200/4095. Then `set_record_format cdng`, record, and check that `journalctl -u apertar-core | grep -i linearization` is empty.

**Rule.** When a derived value (here the storage depth) starts to depend on a new input, every "did it change, do we need to redo X" check must compare the derived value, not the old inputs.


---

## C12. camera: entering Clear HDR on the IMX585 starts at 3840x2160

Apertar-Core `93cab28`. Finding: HDR-D2. Reviewed by a second agent: fix-needed.

**What was there.**

The fork's colour Clear HDR start kept the SDR size, and the sanitiser took the nearest 12-bit Clear HDR row. A Full HD start therefore ran the binned 1920x1080 mode under a "4K Clear HDR" label (src/camera/CameraController.cpp setClearHdr@cinemate-port). Fork main instead pinned colour Clear HDR to 3840x2160 in the sanitiser, which blocked every other Clear HDR row. In the first version of this fix, the WebUI pill sent set_fps on every Clear HDR entry:
  const fpsAgain = clearHdr && !snapshot.clear_hdr && Number.isFinite(fps) && fps > 0;

**Why it is a problem.** In original Apertar, an explicit choice sets the state once in the controller setter, and the sanitiser only enforces limits, so it pins nothing. Explicit commands also keep their own scope. setFps outside a take always clears ladderOverride_ (CC:10711) and runs ladderRewriteLocked (CC:10712), even when the FPS does not change. So with the ladder enabled but overridden, a pill tap from SDR handed the mode back to the ladder.

**How to spot it.** grep for `ladderOverride_ = false` in CameraController.cpp and list which socket commands end an override. Then check every WebUI path that chains commands (concat of set_* payloads) against that list.

**Options.**

- Pin 3840x2160 in the sanitiser as fork main does: this blocks every other Clear HDR row and set_resolution inside Clear HDR, so it was rejected
- Set 3840x2160 in setClearHdr on the off-to-on edge: local, and leaves the sanitiser, ladder and mono rule untouched (chosen)
- WebUI: always resend the FPS after entering Clear HDR: this breaks the ladder override (reviewer finding)
- WebUI: resend the FPS only while the ladder is off, because the ladder owns the FPS when on (chosen)

**Chosen, and why.** I set the 4K start in setClearHdr, and the WebUI resends the FPS only when ladder_enabled is not true. The reviewer was right: CC:10711-10712 clear the override unconditionally outside a take. The cost: with the ladder on, a Full HD SDR 50 fps to Full HD HDR pill tap keeps the 4K Clear HDR FPS cap until the operator or the ladder changes the FPS. Separately, set_resolution of a different size inside Clear HDR also ends the override (CC:10679). This is existing Core behaviour for any real size change, and setResolution runs no ladder rewrite, so the chosen mode holds.

**After.**

```
    if (enabled && !settings_.clearHdr && sensorFamily == SensorFamily::Imx585)
        next.resolution = Resolution{ 3840, 2160 };
...
      const fpsAgain = clearHdr && !snapshot.clear_hdr && snapshot.ladder_enabled !== true && Number.isFinite(fps) && fps > 0;
```

**Checked.**

Here: check_core.sh both builds pass with 0 warnings, and all 17 host tests pass, including imx585_modes_test. In --simulate on port 8150, the WebUI loads with no page errors. Playwright (/home/user/build/sim/hdr-d2-pw/run.js) evaluated imx585BaseCommands:
- Full HD SDR 50 to the hd-hdr pill: with ladder_enabled false it gives set_clear_hdr, set_resolution 1920x1080, set_fps 50; with ladder_enabled true it gives set_clear_hdr and set_resolution only.
- 4K SDR 48 to the 4K HDR pill: set_fps 48 with the ladder off or the field absent, none with the ladder on.
- HDR to HDR and HDR off send no set_fps.
get_state works over /api/command.

Needs the camera:
- At Full HD, tap 4K Clear HDR, then run `printf '{"cmd":"get_state"}\n' | socat - UNIX-CONNECT:/tmp/apertar-core.sock`. It must show resolution 3840x2160, clear_hdr true, raw_bit_depth 12.
- At Full HD 50 fps with the ladder off, the WebUI Full HD HDR pill must give 1920x1080 with Clear HDR on at 50 fps.
- With the ladder overridden, an HDR pill tap must keep ladder_override true.

UI lane, not edited here: the two touch-UI comment fixes from section D2 of REPORT.md (QML comments that say the touch UI enters 16-bit / keeps the size).

**Rule.** Before a UI sends an extra command to restore a value, check what that command's Core setter resets as a side effect (overrides, ladder rewrite). Skip it where another owner, such as the Mode Ladder, controls that value.


**Note from the lead: why the fix sits in Core, and what it cost.** Two programs send `set_clear_hdr`, and they expect different things. The touch UI's entry is called "4K Clear HDR": it sends only `set_clear_hdr` and then locks the size controls, a contract written when Core forced 4K (fork main). The WebUI's family pills send `set_clear_hdr` and then `set_resolution`, a contract written when Core took the nearest row. I first wanted the smaller fix: let the touch UI send the size it promises. That fails on the Mode Ladder: an explicit `set_resolution` ends a Clear HDR override (`ladderOverride_ = false` in `setResolution`), so the ladder would take the mode straight back. So the size has to be set inside `setClearHdr`, where the override is handled. The price is in the WebUI: entering Clear HDR now passes through 4K, which caps the FPS, so the pills send the FPS again afterwards (and not when the ladder owns the FPS). That is logic in the page that I would rather not have. It is four lines, it is in a port-only function, and two reviews went over the ladder cases. If the pills are ever reworked, the cleaner cure is one Core command that takes Clear HDR and the size together.

---

## C13. camera: hold back binned 1920x1080 in 12-bit Clear HDR

Apertar-Core `a36c52f`. Finding: HDR-H1-interim. Reviewed by a second agent: accept.

**What was there.**

src/camera/Imx585Modes.hpp:78-79@cinemate-port listed the binned Full HD row first in the 12-bit Clear HDR class:
    inline constexpr Mode kH12Modes[] = {
        { 1920, 1080, true }, { 3840, 2160, false }, ...
tools/imx585_modes_test.cpp:20 asserted `size() == 29`. src/web/WebControlPage.cpp:8918 mirrored it as `h12: "1920x1080b 3840x2160 ..."`. Before the setClearHdr fix that came earlier in this lane, a Full HD start in the touch UI landed in this mode under a "4K Clear HDR" label.

**Why it is a problem.** The 12-bit Clear HDR samples are expanded with one curve: the full-resolution CCMP curve in cdng/ClearHdrCcmp.hpp, which libcamera's CcmpUnwrap mirrors. Neither side has a term for binning, and commit c1350b0 added the binned row "desk-only", with no curve check on a capture. If the sensor bins before the compander, mid-tones from about 4.6 % to 17.5 % of white come out about 16x too dark, with a step near 17.5 % (hdr12/REPORT.md section 1, V-H1.md). That cause is probable, not confirmed. Original Apertar 1.6.0 has no mode tables. The sizes it offers are sizes it records correctly (CAM-36: no silent downgrade of what is recorded; CAM-21: out-of-range requests are refused with a sentence).

**How to spot it.** grep -n "binned\|true }" src/camera/Imx585Modes.hpp, then check each Clear HDR row: does ClearHdrCcmp.hpp (and libcamera CcmpUnwrap) have a term for that readout? If a mode came in with a commit that says "desk-only" or "not all BLC", ask which capture checked its curve. When you edit a table, grep for its hand copies too (the "1920x1080b" strings in WebControlPage.cpp, the counts in tools/imx585_modes_test.cpp).

**Options.**

- Delete the row from kH12Modes and mirror that in the WebUI fallback list and the test: 3 small edits; the operator loses binned Full HD at 12-bit Clear HDR until a capture is checked
- Full fix: give ccmp::Params and libcamera CcmpUnwrap a binning factor: changes Core and libcamera together and needs a capture to verify, so it cannot be done or checked here
- Keep the row and add a warning in the UIs: the mode still records possibly wrong samples, which breaks CAM-36
- Pin colour Clear HDR to 4K in the sanitiser as fork main did: also blocks every 12-bit and 16-bit crop row, against the intent of caa0153

**Chosen, and why.** Option 1, as the report's 'H1 interim, Core only' recommends. The table is the single source of truth: the probe (offered()), find()/nearest(), the set_resolution check, list_sensor_modes and the ladder pool all read it. One row deleted there reaches every Core user. The only copy that needed a hand edit was the WebUI's fallback string, used until the pool arrives. Given up: binned 1920x1080 at 12-bit Clear HDR, until the P7 capture pair passes. 16-bit Clear HDR and SDR keep their binned row. The driver still advertises the mode, so putting it back is a Core-only change.

**After.**

```
// The driver also lists 1920x1080 binned here. Core holds it back until a capture shows that the 12-bit
// companding curve, the full-resolution one, holds for the binned readout too. To offer it again, put
// { 1920, 1080, true } back first, and "1920x1080b" in the WebUI's h12 list.
inline constexpr Mode kH12Modes[] = {
    { 3840, 2160, false }, { 2880, 2160, false }, { 2160, 2160, false },
...
    CHECK(im::all(im::Class::H12).size() == 28);   // the driver's binned 1920x1080 row is left out
    CHECK(!im::find(im::Class::H12, 1920, 1080, 0));
```

**Checked.**

Run here: /home/user/build/bin/check_core.sh /home/user/wt/lane-hdr lane-hdr both tests printed PASS for lc, nolc and the 17 host tests. The 3 nolc warnings are already there, in CameraController.cpp, which this commit does not change. The WebUI was driven with Playwright in --simulate on port 8147, with imx585 snapshots fed to the page functions. The h12 class has 28 rows. The hd-hdr pill is disabled at 12-bit SDR and 12-bit Clear HDR and enabled at 16-bit Clear HDR, where it gives 1920x1080. No page errors. The simulator has no IMX585, so list_sensor_modes returns an empty list there. Still needs the camera:
1. With 12-bit Clear HDR on, run ac '{"cmd":"list_sensor_modes"}'. It must show no 1920x1080 12-bit Clear HDR mode.
2. Run ac '{"cmd":"set_resolution","width":1920,"height":1080}'. It must be refused with "1920x1080 is not a mode of the IMX585 at 12-bit Clear HDR."
3. To justify putting the row back, use a test build that has the row. At 1920x1080, record 12-bit and 16-bit Clear HDR of the same grey ramp, shutter and ISO (REPORT P7). Decode each through its own DNG tags and compare patch medians. They must match across the ramp, as the 4K pair does.

**Rule.** A companded or binned sensor mode is offered only after one capture pair has checked its transfer curve against a linear mode. Until then, leave it out of the mode table rather than ship it unverified.


---

## C14. media: clip info tells a Clear HDR 12-bit clip from a Log clip

Apertar-Core `56e135c`. Finding: HDR-D3. Reviewed by a second agent: accept.

**What was there.**

src/playback/ClipProbe.hpp:165-176@cinemate-port (01f170c; same lines at lane tip 2f49381):
        // FORMAT row (design 4.3): 16-bit = Clear HDR; a LinearizationTable on 12-bit = companded
        const bool table = !f.first.linearization.empty();
        ...
        if (f.first.bits == 16) look = "Clear HDR 16-bit";
        else if (lossy3 && table) { ... }
        else if (lossy5 && table) { ... }
        else if (table) { look = "Clear HDR 12-bit companded"; f.companded = true; }
        else look = "SDR " + std::to_string(f.first.bits) + "-bit";

**Why it is a problem.** The rule was "any table on a non-16-bit file means Clear HDR 12-bit". But Log takes also write a table (the inverse of the Log curve), and they store fewer bits: cdngLogBits in include/apertar/core/Types.hpp goes 16 -> 12, 12 -> 10 and 10 -> 8. So an H16 Log take showed "Clear HDR 12-bit", and so did an SDR 12 Log take that holds 10 bits. A wrong label like that is one way the owner could have seen "12-bit Clear HDR looks strange" (hdr12/REPORT.md D3, V-H9 section 5). Original Apertar 1.6.0 has no playback code in Core (no src/playback/ in /home/user/wt/core-upstream), so this row is new ground and not a mismatch. The fix keeps the port's shape and makes the rule match what the encoder really writes: CameraController.cpp:4092 writes ccmp::expansionTable() for Clear HDR 12-bit, and :5129 writes the Log inverse table.

**How to spot it.** Look for labels that branch on "has X" (!vec.empty(), a flag present) when more than one writer can produce X. Run grep -n "linearizationTable =" src and check that every writer it finds maps to its own label.

**Options.**

- Compare the table's contents with ccmp::expansionTable() (12 bits, 4096 entries, std::equal): no new state, the header is already part of Core, and it costs 4096 compares once per probe of a changed folder. Chosen.
- Write a private DNG tag that marks Log or Clear HDR, and read it back: the label becomes exact and the source mode is kept, but the file format changes and files already on cards are not covered.
- Guess from the clip name or from the bit depth alone: cheap, but a custom clip name template breaks it, and H16 Log and H12 both store 12 bits.

**Chosen, and why.** Content compare. The file is the witness, which is the rule ClipProbe already follows. It needs no format change, and it is right for clips already recorded. What we lose: an H12 take with Log on now reads "Log 12-bit", and the file alone cannot tell which mode a Log take came from. That would need a tag and is out of scope. The lossy 3:1 / 5:1 rows and the "companded" JSON field ("has a table") stay as they were. Nothing in the WebUI reads that field.

**After.**

```
        const bool table = !f.first.linearization.empty();
        const auto &ccmpTable = ccmp::expansionTable();
        const bool ccmpTableOn = f.first.bits == 12 && f.first.linearization.size() == ccmpTable.size()
            && std::equal(ccmpTable.begin(), ccmpTable.end(), f.first.linearization.begin());
        ...
        else if (ccmpTableOn) { look = "Clear HDR 12-bit companded"; f.companded = true; }
        else if (table) { look = "Log " + std::to_string(f.first.bits) + "-bit"; f.companded = true; }
        else look = "SDR " + std::to_string(f.first.bits) + "-bit";
```

**Checked.**

Run here:
- The gate: /home/user/build/bin/check_core.sh /home/user/wt/lane-hdr lane-hdr both tests. Both builds pass, all 18 host tests pass.
- The new test, built against the old ClipProbe.hpp: the Log 12 and Log 10 clips read "Clear HDR 12-bit companded", so it fails. It passes with the fix.
- The simulator (apertar-core --simulate --media holding the four test clips): GET /api/media/clip?kind=folder&id=<clip> gives "Clear HDR 12-bit companded · uncompressed", "Log 12-bit · uncompressed", "Log 10-bit · uncompressed" and "SDR 12-bit · uncompressed".

Still needs the camera: record H12 with Log off, H16 with Log on, and SDR 12 with Log on. Open each in the WebUI Clip Viewer, or run curl -s "http://<pi>:8000/api/media/clip?kind=folder&id=<clip>" | grep -o '"format":"[^"]*"'. They should read "Clear HDR 12-bit companded", "Log 12-bit" and "Log 10-bit".

**Rule.** Tell a file's kind from what the file actually holds (the table's contents), not from whether some table is there.



---

## D2-1. imx283: per-crop VMAX floors are off by default

imx283-v4l2-driver `36d484b`. Findings: Driver-imx283-F2, X-knobs-17. Made by hand.

**What was there.**

```
imx283.c:277@cinemate-port   static bool crop_vmax = true;
imx283.c:2430@cinemate-port  if (crop_vmax && mode->crop_min_VMAX)
                                     return mode->crop_min_VMAX;
```

VMAX is the number of lines the sensor counts per frame, blanking included. A lower VMAX means a shorter frame and a higher frame rate. `crop_vmax=1` lets each cropped row use its own, lower floor. The parameter's own help text calls those floors "experimental, UNMEASURED".

**Why it is a problem.** Two defaults cancelled each other. The driver turned the experiment on. Core then capped the frame rate at the `crop_vmax=0` floor anyway, and `APERTAR.md` told every Apertar user to create `/etc/modprobe.d/imx283.conf` with `crop_vmax=0`. The installer (`setup.sh`, `dkms.postinst`) does not create that file. So a user who followed the README ran any other libcamera program on unmeasured sensor timings. The same driver already shows the pattern for an unvalidated feature: `experimental_modes` is off unless asked for (imx283.c:269).

**How to spot it.** A setup guide that tells every user to switch a default off is a default that is wrong. `grep -n "module_param" imx283.c`, then read each default against what the guide tells the user to set.

**Options.**

- Delete `crop_vmax`, the `crop_min_VMAX` field and the macro argument: cleanest, but throws away the experiment's numbers before anyone has measured them.
- Default off: one line of code. The numbers stay for the day someone measures them.
- Leave on and ship a modprobe.d file from the installer: more moving parts to keep the wrong default.

**Chosen, and why.** Default off. It is the smallest change, it matches `experimental_modes`, and it removes a setup step from `APERTAR.md`. Kernel style writes a flag that starts as false without an initialiser (`static bool crop_vmax;`), like the line above it.

**After.**

```
/* The per-crop VMAX floors are unmeasured, so they are off unless asked for. */
static bool crop_vmax;
```

**Checked.** Not built or loaded: this container has no kernel headers and no sensor. On the Pi: `cat /sys/module/imx283/parameters/crop_vmax` must print `N`, and Apertar must offer the frame rates it offered with `crop_vmax=0`.

**Rule.** An unmeasured feature is off by default. If the guide tells every user to turn something off, turn it off in the code.

---

## C15. rec: free the playback JPEG encoder when its thread ends

Apertar-Core `b13ccb5`. Finding: REC-5. Reviewed by a second agent: accept.

**What was there.**

src/playback/PlaybackFrames.cpp:92@cinemate-port, inside encodeRgbJpeg:
    thread_local tjhandle handle = tjInitCompress();
    if (!handle) return false;
    ...
    const int rc = tjCompress2(handle, rgb.data(), ...);
Nothing ever calls tjDestroy(handle).

**Why it is a problem.** A thread_local variable is destroyed when its thread exits. But a raw tjhandle is just a pointer, so destroying it does not free what it points to. WebServer starts one detached thread per connection (src/web/WebServer.cpp:279-290) and serves one request on it. So every frame that missed the cache created a handle plus its libjpeg state, and the thread then exited without freeing them. Core's memory grew with every scrub and play session. Original Apertar wraps the handle in a small RAII struct: TurboJpegCompressor calls tjInitCompress in its constructor and tjDestroy in its destructor, and the encoder declares `thread_local TurboJpegCompressor compressor;` (App:4108-4134@upstream-1.6.0, encodeYuv420ToJpeg). CAM-6 says small helpers are copied into each .cpp that needs them.

**How to spot it.** grep -rn "thread_local" src | grep -v "thread_local [A-Z][A-Za-z]*Compressor". Any thread_local raw handle or pointer from an Init/Create/open call with no destructor leaks once per thread. That is worst where threads are short-lived, like WebServer's one detached thread per connection.

**Options.**

- Copy App's TurboJpegCompressor struct into the PlaybackFrames.cpp anonymous namespace: 15 lines, one file, App untouched, follows CAM-6
- Move the struct into a new src/playback/TurboJpegCompressor.hpp and include it from App and playback: one source of truth, but a new file and an edit in App (merging copies unasked, CAM-6 smell)
- Call tjInitCompress and tjDestroy on every call with no thread_local: simplest, but it sets the handle up again for each frame, even on a long-lived thread

**Chosen, and why.** Option 1, the copy. It is the smallest local change, it is code App already has, and it leaves App alone. I gave up the single shared definition the item suggested. Two 15-line copies are what CAM-6 expects in this code base. The handle is still created once per connection thread. That cost was there before, and the cache hides most of it.

**After.**

```
struct TurboJpegCompressor {
    TurboJpegCompressor() : handle(tjInitCompress()) {}
    ~TurboJpegCompressor() { if (handle) tjDestroy(handle); }
    tjhandle handle = nullptr;
};
...
    thread_local TurboJpegCompressor compressor;
    if (!compressor.handle) return false;
    const int rc = tjCompress2(compressor.handle, rgb.data(), ...);
```

**Checked.** Run here: the gate (/home/user/build/bin/check_core.sh /home/user/wt/lane-core1 lane-core1 both tests) printed all PASS, with no warnings in PlaybackFrames.cpp. The libcamera build has TurboJPEG enabled. The sim media folder has no DNG clip, so I could not scrub in --simulate. Instead, a standalone program ran the same tjCompress2 call on 3000 short-lived threads: with the raw thread_local tjhandle, RSS went from 4 MB to 20 MB; with TurboJpegCompressor it went from 4 MB to 6 MB. Needs the Pi: scrub a 4K clip in the WebUI for 5 minutes and compare `ps -o rss -C apertar-core` before and after. The growth should stay within the JPEG caches (about 32 MB).

**Rule.** A thread_local holding a C library handle must be an RAII object whose destructor frees the handle, never a raw pointer.


---

## C16. rec: clip-name example reads a listing, never the medium under the lock

Apertar-Core `9ec7bbf`. Finding: REC-6. Reviewed by a second agent: accept.

**What was there.**

src/camera/CameraController.cpp:11827-11834@cinemate-port (called from settings() :12592 and emitSettingsEventLocked() :12866, both under mutex_):
void CameraController::fillClipNameExampleLocked(CaptureSettings &out) const
{
    try {
        out.clipNameExample = nextClipFolderName(mediaRootPath(mediaRoot_), out, clipNameSensorLocked(),
                                                 std::chrono::system_clock::now());
nextClipFolderName (:1191) -> clipname::nextClipNumber (ClipName.hpp:287) calls std::filesystem::exists(root / name) for clip 1..9999 until one is free.

**Why it is a problem.** Every state poll (once a second per WebUI client) and every setter reply ran one stat per existing clip with the camera lock held. With 400 takes that is about 400 stats per poll, also during a take. On a hung or pulled USB mount one stat can block, and then record_stop, checkRecordingFailure and every setter wait on mutex_. Original Apertar looks the clip folder up only at take start (CC:5548@upstream-1.6.0, DngRecordingQueue::reserveClipFolder), and settings() does no I/O (CC:8566-8573@upstream-1.6.0). Rule CAM-10: nothing slow under mutex_. CAM-18: the runtime field is still filled before settings leave Core.

**How to spot it.** grep -n "Locked(" for helpers called from settings() or emit*EventLocked, then follow them to std::filesystem::exists/status/directory_iterator, stat or open. A loop of up to 9999 probes, or any I/O reached from a getter that polls run every second, is the smell. Ask: what happens to this call if the USB disk stops answering?

**Options.**

- Cache the finished example string, refreshed on template change, take start/stop and mount change (the item's literal rework): cheap, but the string goes wrong right after a format, fps or date change ({format}_{date}_{clip} is the default), until the next take
- Keep the probe but run it outside mutex_ on each settings read: no lock hang, but still ~400 stats per poll per client
- Cache the root's folder names, filled by the media watcher thread (which already does blocking probes of the root), and compute the example from the set under the lock: no I/O under the lock, correct for current settings and clock, stale only up to one watcher cycle (1 s) after an external card change
- Drop clip_name_example from state and let the UIs call preview_clip_name: changes the socket contract and the touch UI bridge

**Chosen, and why.** Option 3, the folder-name set. It meets the item's goals (no stat per poll, nothing slow under mutex_, example stale for at most one poll after an external change, as the item's Risk line accepts) without the stale-name bug a cached string would have after a format or fps change. Given up: one readdir of the root per second on the media watcher thread while idle (not during takes, and never on a Removed/Error mount). Also a small extra member and public setter. setClipFolderNames ignores a listing that arrives while recording_ is set, because that listing was made before the take began and lacks the take's folder.

**After.**

```
// CameraController.cpp, fillClipNameExampleLocked: a set lookup, no I/O
out.clipNameExample = nextClipFolderName([this](const std::string &name) {
    return clipFolderNames_.count(name) > 0;
}, out, clipNameSensorLocked(), std::chrono::system_clock::now());
// ApertarCoreApp.cpp, runMediaWatcher (own thread, no camera lock while listing)
for (std::filesystem::directory_iterator it(options_.mediaRoot, ec), end; !ec && it != end; it.increment(ec))
    names.insert(it->path().filename().string());
camera_.setClipFolderNames(std::move(names));
```

**Checked.** Here: the gate (above, PASS). Then apertar-core --simulate --media /home/user/build/sim/media --web-port 8163 with 400 dummy cDNG_26-11-17_C0001..C0400 folders. get_state gave clip_name_example cDNG_26-11-17_C0401. Folders made or removed by hand showed in the next poll (C0402, then C0001). set_record_format mlv answered MLV_26-11-17_C0001 at once. set_clip_name_template / preview_clip_name answered correctly. Playwright: the WebUI "Next clip:" line showed the name, with no page errors. strace cannot attach to processes in this container, so the stat count per poll was not measured. Needs the Pi: with many clips on the card and the WebUI open, run strace -f -c -e trace=newfstatat -p $(pidof apertar-core) for 10 s; it must show no stat per clip folder. Then pull the card during polling and press record stop; it must answer within 2 s. After a real take stops, the example must move to the next number within about 1 s.

**Rule.** A getter or event builder that runs under the camera mutex reads only memory. Filesystem probes belong on the thread that already owns blocking media I/O, which passes the result in.


---

## C17. rec: part folders are made by the writers, the queue waits for stranded ones

Apertar-Core `a663cfc`. Finding: REC-7. Reviewed by a second agent: accept.

**What was there.**

src/camera/CameraController.cpp spawnWorker Exit guard @cinemate-port (plus the e8b065e destructor wait):
    {
        std::lock_guard<std::mutex> lock(queue->exitMutex_);
        queue->liveWorkers_.fetch_sub(1, std::memory_order_acq_rel);
    }
    queue->exitCv_.notify_all();
In the port, copy threads also called ensurePartFolder (mkdir on the medium) and were joined without a bound. ~DngRecordingQueue's second stop() returned at once and left detached writers running.

**Why it is a problem.** Original Apertar 1.6.0 joins every writer in stop() and makes its folders before the take, so it has no detached threads. The port's bounded dead-medium stop is port ground and must cover every thread that touches the medium. Once the queue is destroyed after waiting on a cv, a thread may only touch that cv while it holds the mutex the waiter rechecks under. Otherwise the waiter can see the count drop, return and free the cv before notify_all runs.

**How to spot it.** grep -n 'notify_all\|notify_one' and check whether any notify sits after a lock scope closes on an object a waiter may destroy. grep for filesystem calls (create_directories, mkdir, open) in threads that stop() joins without a timeout.

**Options.**

- Keep mkdir on the copy thread and bound the copy-thread join: a second timeout path and more detached threads
- Move ensurePartFolder to the writer, which stop()'s bounded wait already covers: chosen, a small local change
- Destructor: wait on exitCv_ for the dead-medium time; notify under exitMutex_ so the waiter cannot free the cv early: a one-line move
- Make the queue shared_ptr-owned by the writers: a new ownership layer, out of style

**Chosen, and why.** The writer makes the part folder, and the destructor gets a bounded wait with the notify done under the lock. This is the smallest safe change, and it does not alter how a removed medium is detected (REC-8). What is given up: if the writers outlive even the second bound, the queue is still destroyed under them. That is logged, and it is left to REC-8's design.

**After.**

```
~Exit()
{
    // Notify under the lock: ~DngRecordingQueue may free the cv
    // as soon as it sees 0.
    std::lock_guard<std::mutex> lock(queue->exitMutex_);
    queue->liveWorkers_.fetch_sub(1, std::memory_order_acq_rel);
    queue->exitCv_.notify_all();
}
```

**Checked.** Here: /home/user/build/bin/check_core.sh /home/user/wt/lane-core1 lane-core1 both tests, all PASS. The 3 nolc warnings are older ones in lines this change does not touch (7782 mediumGone, 7935 basePathOverride, 1242 allocatePhotoBasePath). Needs the Pi: set [storage] frames_per_folder=100, record a cDNG take and pull the card. stop must return within APERTAR_DEAD_MEDIUM_STOP_MS. Quit Core 10 s later with no crash: journalctl -u apertar-core -b | grep -i 'segfault\|detached'. A normal split take must still have every part_NNN folder filled.

**Rule.** Every thread that can block on the medium must sit under a bounded wait, and a thread that signals an object which may be destroyed must do so under the waiter's mutex.


---

## C18. audio: bound the writer queue and size the WAV from bytes written

Apertar-Core `bfd032e`. Finding: REC-16. Reviewed by a second agent: accept.

**What was there.**

src/audio/AudioRecordingSession.cpp (readerLoop) @cinemate-port: the reader counted bytes when it queued them, not when they were written, and the queue had no size limit.
    enqueueWrite(buffer.data(), static_cast<size_t>(bytesRead));
    if (writeFailed_.load(std::memory_order_acquire)) break;
    capturedBytes_ += static_cast<uint64_t>(bytesRead);
  and the gap padding did: enqueueWrite(nullptr, gapBytes); capturedBytes_ += gapBytes;
  enqueueWrite pushed every block with no cap; after a failed write, writerLoop dropped the blocks without counting them.

**Why it is a problem.** After a write failure, finalizeWav sized the WAV header from capturedBytes_, which included bytes that never reached the file. The header then claimed more data than the file held (or the file had a silent tail when resampling), and memory grew without limit while the card stalled. Original Apertar adds to capturedBytes_ only after a successful rawStream_.write (src/audio/AudioRecordingSession.cpp:472-474 @upstream-1.6.0). Its background DNG writer is bounded by configuredWriterByteCap() with APERTAR_LOSSYDNG_WRITER_BYTES (src/lossydng/LossyDngEncoder.cpp:97-110 @upstream-1.6.0, used at :167).

**How to spot it.** grep -n 'capturedBytes_ +=\|push_back' in any code that hands work to a writer thread. Ask whether the counter moves before the write succeeds, and whether the queue has a cap.

**Options.**

- Count bytes in the writer thread after a successful write and cap the queue the way the DNG writer is capped: small and local, follows upstream
- Keep counting in the reader and subtract dropped blocks on failure: more bookkeeping across two threads, easy to get wrong
- Go back to synchronous writes in the reader like upstream: undoes the port's writer thread and brings back reader stalls

**Chosen, and why.** The first option: count after the write, in the writer thread, and add a cap read from the environment like configuredWriterByteCap(). This gives up the port's never-drop queue: when the card stalls past the cap, the take ends with an error instead of using up memory.

**After.**

```
    if (queuedWriteBytes_ + size > configuredWriterByteCap()) {
        if (!writeFailed_.exchange(true, std::memory_order_acq_rel)) {
            failure_.set("Audio capture write stalled.");
            ...
        }
        return;
    }
...
        capturedBytes_ += static_cast<uint64_t>(block.size());
```

**Checked.** Run here: check_core.sh /home/user/wt/lane-core1 lane-core1 both tests. Both builds pass with 0 warnings and all 17 host tests pass. There is no ALSA here. Still needs the Pi: record with audio to a nearly full card, then run ffprobe -v warning <clip>.wav and check there is no size warning. Also set APERTAR_AUDIO_WRITER_BYTES=1048576 with a stalled card and check the take ends with "Audio capture write stalled.".

**Rule.** Count bytes where they are written, not where they are queued, and give every queue between threads a byte cap.


---

## C19. media: URL-encode the clip id and name in a clip's audio_url

Apertar-Core `7f188a5`. Finding: APP-26. Reviewed by a second agent: accept.

**What was there.**

src/ApertarCoreApp.cpp:7387@cinemate-port (line 7391 at lane tip before the fix), in clipInfoJson:
    << ",\"audio_url\":\"" << (hasAudio ? "/api/media/file?kind=folder&id=" + escapeJson(id) + "&name=" + escapeJson(f.name) + ".wav" : std::string()) << "\""

**Why it is a problem.** escapeJson only makes a string safe inside JSON quotes. It does not make it safe inside a URL query. A clip name with '&', '#', '%', '+' or a space breaks the query: for 'A&B_001' the server reads id=A and finds no name, so /api/media/file returns 400 and the clip plays with no sound. Clip names can hold such characters because the names are built from a template (014a2bf). Original Apertar builds media URLs one query value at a time with urlEncodeComponent (mediaDownloadUrl, src/ApertarCoreApp.cpp:6140-6142@upstream-1.6.0; presets at :5447). It applies escapeJson once to the finished URL where the URL goes into the JSON (download_url).

**How to spot it.** grep -n '?[a-z_]*=" + escapeJson\|&[a-z_]*=" + escapeJson' src/*.cpp src/*/*.cpp. Any query value built with escapeJson instead of urlEncodeComponent is this bug. Also ask: can this value contain '&', '#', '%', '+' or a space? Clip names, file names and preset names can.

**Options.**

- Encode each query value with urlEncodeComponent and escapeJson the whole URL: one line, same as mediaDownloadUrl, no new code
- Add a mediaAudioUrl() helper next to mediaDownloadUrl: tidier, but it is a new function with one caller
- Have the WebUI build the URL itself from id and name with encodeURIComponent: moves the logic to JS and changes the JSON contract the page reads

**Chosen, and why.** Option 1. It is the smallest change and it matches how upstream already builds download URLs. Nothing else changes: the field name, the empty string when there is no audio, and the page's use of clip.audio_url all stay as they were. I did not add a helper, because the line has only one caller.

**After.**

```
    << ",\"audio_url\":\"" << (hasAudio ? escapeJson("/api/media/file?kind=folder&id=" + urlEncodeComponent(id) + "&name=" + urlEncodeComponent(f.name + ".wav")) : std::string()) << "\""
```

**Checked.** Here: the gate (check_core.sh /home/user/wt/lane-core1 lane-core1 both tests) prints PASS. I ran a --simulate core on port 8167 with --media /home/user/build/sim/app26-media. It held a clip folder 'A&B_001' with three DNG frames and A&B_001.wav. GET /api/media/clip?kind=folder&id=A%26B_001 returned audio_url "/api/media/file?kind=folder&id=A%26B_001&name=A%26B_001.wav". curl fetched that URL with 200 audio/wav (192044 bytes). The old, unencoded form returned 400. A Playwright fetch from the WebUI page with a Range header got 206 audio/wav. Camera: nothing beyond the general smoke test. Optional Pi check: record a take with sound under a clip name that holds '&' or a space, open it in the WebUI player and confirm the sound plays.

**Rule.** Build a URL by URL-encoding each query value (urlEncodeComponent), then JSON-escape the whole URL once where it goes into the reply.


---

## C20. hw: write a key edit into every copy of a duplicated section

Apertar-Core `6a05fe5`. Finding: HW-17. Reviewed by a second agent: accept.

**What was there.**

src/hardware/HardwareConfigText.hpp:537-550@cinemate-port, the Set branch of hwconf::applyEdit:
    for (size_t i = 0; i < L.size(); ++i) {
        if (L[i].kind == Kind::Section && L[i].section == edit.section && !firstHeader) firstHeader = i;
        if (!firstHeader || L[i].section != edit.section) continue;
        if (L[i].kind == Kind::Section && i != *firstHeader) break;   // a second copy of the section: leave it
        ...
            if (replaced) drop.push_back(i);
            else replaced = i;

**Why it is a problem.** If a section is in the file twice, every reader takes the later line. The port changed only the first copy, so the later copy's old value stayed in effect. Trusted writes skip checkEdits' refusal of duplicated sections (IMU calibration and orientation, set_buffer_mode, set_frames_per_folder, set_clip_merge, set_storage_preroll). They replied ok and the setting was lost: after calibrate_gyro, for example, the old bias stayed. Original Apertar's writeHardwareConfigValue sets inTargetSection again at every header of that name and rewrites the key in each copy (src/hardware/Mpu6050RecordingSession.cpp:628-668@upstream-1.6.0). Conventions rule HW-8: programmatic writes edit one key in place.

**How to spot it.** grep -n "break;.*copy\|second copy" in any INI writer. Ask "which line does the reader use when the section or key appears twice, and which one does the writer change?" A smell: an edit that stops at the first match while the parser lets later lines win.

**Options.**

- Replace the key in every copy of the section, the way upstream writeHardwareConfigValue does (small change, keeps comments and line order)
- Merge the copies into one section while editing (regenerates part of the file, against HW-8, and surprises anyone who reads the file by hand)
- Refuse trusted writes on duplicated sections as set_controls does (the IMU and storage commands start failing on files that 1.6.0 accepted)

**Chosen, and why.** Option 1, the upstream behaviour. The loop no longer stops at the second header. A flag, keyInCopy, is reset at each header of the section. The first line of the key in each copy is rewritten, and later lines of the key inside the same copy are dropped as before. lastInSection now ends up in the last copy, so a new key is added there. Given up: the file still has two copies. Merging them stays the operator's job in Settings > Config, as the checkEdits message says.

**After.**

```
    bool keyInCopy = false;
    for (size_t i = 0; i < L.size(); ++i) {
        if (L[i].kind == Kind::Section && L[i].section == edit.section && !firstHeader) firstHeader = i;
        if (!firstHeader || L[i].section != edit.section) continue;
        if (L[i].kind == Kind::Section) keyInCopy = false;   // a new copy of the section
        if (L[i].kind != Kind::Blank) lastInSection = i;
        if (L[i].kind == Kind::Key && L[i].key == edit.key) {
            if (keyInCopy) drop.push_back(i); else replaced.push_back(i);
            keyInCopy = true;
```

**Checked.** Run here: the gate (/home/user/build/bin/check_core.sh /home/user/wt/lane-core1 lane-core1 both tests) passed. A scratch g++ program called hwconf::applyEdit on text with [mpu6050] twice (gyro_bias_x=1 and =2 in the first copy, =12 in the second) and set gyro_bias_x=5. Both copies came out as 5, the duplicate line was dropped and the inline comment kept on its own line. A new key (gyro_bias_y) went into the last copy. Live check: APERTAR_HARDWARE_CONFIG=<file with [storage] twice> apertar-core --simulate, then curl -X POST /api/command -d '{"cmd":"set_frames_per_folder","value":"500"}' wrote 500 in both copies and get_state reported frames_per_folder 500. (The file's mtime had to be set a minute back first. Otherwise the store answers being_written for a file changed in the last second.) Needs the camera: nothing.

**Rule.** A key write into an INI file must follow the reader's rule: if the reader takes the later line, write every copy.


---

## C21. hw: a write to a missing hardware file starts from the /boot copy

Apertar-Core `0c85297`. Finding: HW-18. Reviewed by the lead (no second worker this round).

**What was there.**

src/hardware/HardwareConfigStore.cpp:276@cinemate-port (saveLocked). After refreshLocked() the store had cleared text_ for a missing file (:160-163), so the edit started from nothing:
    const std::string current = text_;
    const std::string currentRevision = revision_;
    ...
    next = hwconf::applyEdits(current, *edits);
The IMU calls store.edit(store.currentRevision(), edits, "imu", flags) (Mpu6050RecordingSession.cpp:616-619), and the store's path is always the editable one.

**Why it is a problem.** Every reader (GpioInput, Pcf8574Input, the IMU and others) opens the first file that exists in the list env -> /home/pi -> /boot/firmware -> /boot (HW-2, HW-9). A /home/pi file with only [mpu6050] or [imu] in it wins over the full /boot file, so after the next start the buttons, displays and the other sections are gone. Original Apertar writes only the editable path (HW-9, App:4271-4276@upstream-1.6.0), and its IMU wrote the file the loader had read (Mpu6050RecordingSession.cpp:1297-1300@upstream-1.6.0), so nothing was lost. The port's own Config page already seeds a missing file from the /boot copy (buildHardwareConfigFileJson, App:6215-6227 at the tip).

**How to spot it.** Look for any write path that treats "file missing" as "text is empty" while the readers walk a candidate list. Run grep -n "text_.clear\|kAbsentRevision" src/hardware and ask: when this file does not exist, which file do the readers use instead, and does the write keep its contents?

**Options.**

- Seed current in saveLocked from the /boot copy when the editable file is missing: about 10 lines, one place, every writer (IMU, set_controls, WebUI replace) gets it
- Have the IMU write the file the loader found, as upstream did: this breaks HW-9 (never write /boot) and the single store path
- Refuse the write with an error that names both paths: safe, but calibrate_gyro then fails on a /boot-only rig until someone copies the file by hand
- Copy the /boot file to /home/pi at start: a new side effect at boot, and it writes a file nobody asked for

**Chosen, and why.** Option 1. It is the item's rework, the smallest change, and it repeats the rule buildHardwareConfigFileJson already uses (same two paths, same order). current stays at revision kAbsentRevision, so a caller that loaded the missing file (the IMU, or the WebUI, which serves revision h0000000000000000) still matches the base and does not get "stale". The diff and the new-error check now run against the /boot text, so they report only the real change. Given up: when APERTAR_HARDWARE_CONFIG points to a missing file and /home/pi exists, the readers would read /home/pi first, but the seed skips it and looks only at /boot. That matches the Config page, and that setup is a bench-only case.

**After.**

```
    // A missing file starts from a /boot copy when there is one: the readers take its sections, so a write must keep them.
    std::string current = text_;
    if (!stamp_.exists) {
        for (const char *candidate : { "/boot/firmware/apertar-hardware.conf", "/boot/apertar-hardware.conf" }) {
            if (std::filesystem::is_regular_file(candidate, error)) {
                current = readTextFile(candidate);
                break;
            }
        }
    }
```

**Checked.** Gate here: /home/user/build/bin/check_core.sh /home/user/wt/lane-core1 lane-core1 both tests (all PASS). Run-time check here: the script /home/user/build/sim/hw18-check.sh, run as unshare -m bash /home/user/build/sim/hw18-check.sh. It runs in a private mount namespace (a Linux feature that gives one process tree its own view of mounts) with a tmpfs over /boot, so the real /boot and other lanes do not see it. It writes /boot/firmware/apertar-hardware.conf with [gpio], [imu] and [display], sets APERTAR_HARDWARE_CONFIG to a missing file, starts --simulate on port 8157 and sends set_imu_sync_offset 12. The new file held all three sections with sync_offset_ms=12. Needs the Pi: nothing. An optional look on a rig with only /boot/firmware/apertar-hardware.conf: run calibrate_gyro, then check that /home/pi/apertar-hardware.conf holds every section.

**Rule.** A writer that creates the editable file must start from the file the readers would otherwise read, never from empty text.


---

## C22. core, web: the Controls page reads the hardware file through GET /api/config

Apertar-Core `fe269e7`. Finding: command-plane commit 1. Reviewed by a second agent: accept.

**What was there.**

src/ApertarCoreApp.cpp@cinemate-port: get_controls ran in a second dispatcher ahead of the command lock. It parsed the hardware file eight times and wrote controlsErrors_/controlsWarnings_ from a read. WebControlPage.cpp loadControls:
  const [controls, catalog] = await Promise.all([
    controlsCall({ cmd: "get_controls" }),
    controlsState.catalog ? Promise.resolve(null) : controlsCall({ cmd: "list_actions" }),
  ]);
  controlsState.revision = String(controls.controls.revision || "");

**Why it is a problem.** A second door to the hardware file: it went past the command lock, parsed the file many times and changed state during a read. Original Apertar serves a read that must not wait for the lock as an HTTP GET on the web server's thread, and GET /api/config already returns this file (buildHardwareConfigFileJson, ApertarCoreApp.cpp:5290-5321 and 7168-7173@upstream-1.6.0).

**How to spot it.** grep -n 'cmd == "get_' src/ApertarCoreApp.cpp for commands handled before the lock; in the page JS, look for an await before an independent request that used to sit in a Promise.all.

**Options.**

- Extend GET /api/config with the page's fields and delete get_controls: one read path, small diff (chosen)
- Keep get_controls but move it under the lock: still two doors to one file
- Add a new /api/controls route: a new endpoint the original does not have

**Chosen, and why.** I extended the upstream GET /api/config and deleted get_controls, as the design page says. After review, the page keeps its old Promise.all shape, so a first load is still one round trip. The cost: smoke_core.sh's get_controls call now gets Unknown command, which is expected.

**After.**

```
const [payload, catalog] = await Promise.all([
  fetch("/api/config", { cache: "no-store" }).then((response) => response.json()),
  controlsState.catalog ? Promise.resolve(null) : controlsCall({ cmd: "list_actions" }),
]);
if (!payload.ok)
  throw new Error(payload.error || "Could not load the controls.");
controlsState.revision = String(payload.revision || "");
```

**Checked.** Gate passed. The one warning is unchanged and was already there (convertPlanarYuv420ToRgb unused, ApertarCoreApp.cpp:4742; not on a line this commit touches). Ran --simulate on port 8147 and drove the page with Playwright (/home/user/build/sim/hdr-pw.js): on the first load GET /api/config and POST list_actions go out side by side, a reload sends only GET /api/config, the revision and model are set, 7 peripherals load, no page errors. grep -rn get_controls src finds nothing. controls_page_test.js was not copied or changed. Needs the camera: open Settings > Controls while a take runs, then check that curl -s localhost:8000/api/state shows recording_dropped_frames 0.

**Rule.** A read the UI needs without the command lock goes through an HTTP GET route like upstream's /api/config, not through a socket command that skips the lock; parallel requests stay parallel.


---

## C23. core, web: saved hardware-file versions come from GET /api/config/history

Apertar-Core `3660aab`. Finding: command-plane commit 2. Reviewed by the lead (no second worker this round).

**What was there.**

src/ApertarCoreApp.cpp:12463@cinemate-port (lane tip 1c5c76a), inside handleReadOnlyHardwareCommand, the dispatcher that runs before the command lock:
    if (command.name == "controls_history") {
        if (const auto name = command.string("name"); name && !name->empty()) {
            const auto text = store.historyText(*name);
            if (!text)
                return errorReply(command.id, "No saved version called " + *name + ".");
            ...
The page called it at three places (WCP:18634, :18661, :18973) as controlsCall({ cmd: "controls_history", name }) and checked reply.ok each time.

**Why it is a problem.** It was a second door to a file the WebUI already reads through GET /api/config, answered by a second dispatcher in front of handleCommand (CMD-2, CMD-3). The original code serves a library read as an HTTP GET route on the web server's own connection thread, with no commandMutex_. It picks one item with a query parameter: GET /api/presets at App:7360@upstream-1.6.0, queryParameterValue at App:7198-7199@upstream-1.6.0. That is WEB-4 (file-library reads are /api routes) and WEB-5 (one if-branch per route, okReply/errorReply with id -1, an HTTP status on refusal).

**How to spot it.** Look for a command whose block only reads a store or a file and never touches camera_ or UI.conf. Check: grep -n 'command.name ==' src/ApertarCoreApp.cpp and read the blocks that are handled outside handleCommand's lock. Then ask whether the page already fetches a route for the same file.

**Options.**

- Move the block into GET /api/config/history with ?name= (the plan): about -18/+26 in App, +13 in WCP, follows the presets route
- Keep controls_history as an ordinary command under the lock: smallest diff, but the file keeps two doors and a history read waits behind a take start
- Fold the history list into GET /api/config: one fetch less, but every config read gets heavier and one version still needs its own call

**Chosen, and why.** The route, as the plan says. The block moved nearly line for line. The only changes are -1 as the id, response.body, and a 404 status on an unknown name. In the page, one async helper replaces three inline calls. Each caller wraps it in try/catch and shows error.message, the way the original library fetches show Core's sentence (WEB-14, WEB-16). Given up: socket clients such as core.py lose the command. Over ssh the replacement is curl -s localhost:8000/api/config/history (owner row a in the design page).

**After.**

```
if (request.method == "GET" && request.path == "/api/config/history") {
    ...
    if (const auto name = queryParameterValue(request.query, "name"); name && !name->empty()) {
        const auto text = store.historyText(*name);
        if (!text) {
            response.status = 404;
            response.body = errorReply(-1, "No saved version called " + *name + ".");
            return response;
        }
```

**Checked.**

Run here:
- The gate (check_core.sh lane-hdr both tests): PASS. The single warning is the old convertPlanarYuv420ToRgb unused-function warning at App:4742, not in these lines.
- --simulate with its own APERTAR_HARDWARE_CONFIG and HOME, under curl:
  - the list works;
  - a save adds an entry;
  - ?name= returns the text;
  - an unknown name gives 404 and the sentence;
  - controls_history now answers "Unknown command";
  - help no longer lists it.
- Playwright against that --simulate page:
  - the Config history select lists the saved versions;
  - picking one puts its text in the editor, unsaved;
  - a bad name toasts the sentence;
  - Controls Undo restores the file, through GET history?name= and then set_controls;
  - no page errors.
- smoke_core.sh compared with the commit-1 output (smoke-after.txt): only the help list (132 to 131) and the controls_history reply (now an error) changed, both expected. Note: smoke_core.sh needs the lead's edit: drop controls_history and add /api/config/history to its route list.

controls_page_test.js: it fails at the same check ("Controls shows the GPIO, the NeoRotary and the PCF8574") on commit 1 as on this commit. That is a fixture or page drift from before this commit. So its Undo check does not run, and the Playwright run above covers it. The test also hard-codes the macOS Chrome path; I used a temporary copy with the Linux path for the run.

The copy at /home/user/build/sim/hdr/controls_page_test.js now has a GET /api/config/history mock placed before the /api/config handler. It logs { route: "config_history", name }. The controls_history command mock is removed, and the Undo check looks for route === "config_history". The lead applies this.

Camera: nothing beyond the page check. On the Pi, open Settings > Config > history and press Undo in Controls.

**Rule.** A read of a file library is a GET route with a query parameter, not a socket command.


---

## C24. core: an I2C scan gives up after one second

Apertar-Core `bdef3d1`. Finding: command-plane commit 3. Reviewed by a second agent: accept.

**What was there.**

src/ApertarCoreApp.cpp:12538@cinemate-port (lane-hdr tip 7625476): the loop probes every address from 0x03 to 0x77 with no limit on the total time:
    for (int address = 0x03; address <= 0x77; ++address) {
        ...
        const hardware::I2cProbe probe = hardware::probeI2cAddress(bus, address);
        if (!probe.busExists)
            return errorReply(...);
        if (!probe.found)
            continue;

**Why it is a problem.** On a stuck bus (SDA held low), each of up to 117 addresses costs one adapter timeout. Command-plane commit 5 moves scan_i2c under commandMutex_, so a slow scan would hold up every other command. Which errno a stuck address returns depends on the adapter (bcm2835, RP1 designware, i2c-gpio) and has not been measured, so a list of errnos to stop on cannot be trusted. Original Apertar bounds a wait with a steady_clock deadline: waitForTimedatectlNetworkSync, src/ApertarCoreApp.cpp:2979-2980@upstream-1.6.0 (`const auto deadline = std::chrono::steady_clock::now() + timeout; while (now() < deadline)`).

**How to spot it.** Look for a for-loop that calls open/ioctl/read, or a probe function, once per item with no deadline. Ask: "If every call took its worst-case timeout, how long would this hold the lock?" To find candidates: grep -n "for (int address\|probeI2cAddress\|::read(" src.

**Options.**

- Time bound with a steady_clock deadline in the loop: +3 lines, works on every Pi without knowing the adapter's errno; a very slow but healthy bus (i2c-gpio) could be refused
- Stop on certain errnos (ETIMEDOUT, EREMOTEIO...): not measured per adapter, so it could miss the stuck case or refuse a good bus
- Run the scan in a worker thread whose status the client polls, like the media speed test: about +40 lines and a new status command; only worth it if a healthy scan is slow

**Chosen, and why.** The time bound, as the plan says. It reuses upstream's bounded-wait shape and needs no knowledge of the adapter. What we give up: a healthy scan that runs past 1 s is refused. The owner row in the design page says to measure on a Pi 4 and switch to the worker option if a healthy scan goes over about 0.5 s. The check runs only after a real probe. Addresses Core already holds are skipped without a probe, so they cost no time.

**After.**

```
        const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(1);
        for (int address = 0x03; address <= 0x77; ++address) {
            ...
                if (!probe.busExists)
                    return errorReply(...);
                if (std::chrono::steady_clock::now() >= deadline)
                    return errorReply(command.id, "I2C bus " + std::to_string(bus) + " does not answer: check the wiring.");
                if (!probe.found)
```

**Checked.**

Run here:
- The gate, check_core.sh /home/user/wt/lane-hdr lane-hdr both tests: all PASS. Its one warning is the existing unused convertPlanarYuv420ToRgb at App:4742, not in my lines.
- --simulate on port 8143: `scan_i2c bus=1` still answers "Bus 1 does not exist on this Pi.", and `scan_i2c` with no bus still gets its sentence. This machine has no /dev/i2c-*, so the deadline itself could not be exercised.

Needs the camera:
- On Pi 4, Pi 5/CM5 and CM4: `time python3 ~/apertar-kb/working/tools/core.py scan_i2c bus=1` must list the same addresses as `i2cdetect -y -r 1` and take well under 1 s.
- Optional bench check: jumper SDA (GPIO 2) to GND through a 1 kOhm resistor, never directly. The scan should return the sentence within about 1 s plus one adapter timeout.

**Rule.** Any loop that does blocking I/O for every item (a probe or read per address or file) gets a steady_clock deadline, so the time it can take is bounded no matter how the hardware fails.


---

## C25. core: list_actions answers the action list only

Apertar-Core `d40a1d6`. Finding: command-plane commit 4. Reviewed by a second agent: accept.

**What was there.**

src/ApertarCoreApp.cpp:12550@cinemate-port (lane tip before this commit), inside handleReadOnlyHardwareCommand:
    if (command.name == "list_actions") {
        const SharedUiSettingsSnapshot uiSettings = readSharedUiSettings();
        const CaptureSettings cameraSettings = camera_.settings();
        ...
        std::string body = hardware::actions::catalogJson();   // "{...}": the reply wants the members
        body = body.substr(1, body.size() - 2);
        body += ",\"values\":{\"iso\":" + jsonNumberArray(pcfIsoOptions(...)) ...
        body += ",\"values_for\":\"" + ...;  body += ",\"gestures\":{...}";

**Why it is a problem.** The reply sent three members nobody reads. The WebUI keeps only catalog.actions (WebControlPage.cpp:16757, 16829, 16883, 18062, 18511). row.gestures in the page comes from the controls model, not from this reply. To fill values, every call read UI.conf and copied the camera settings. The builder also wrapped its output in braces, and the caller then cut them off again with substr. In original Apertar a builder returns the members and okReply(id, fragment) adds the braces (ApertarCoreApp.cpp:108-128@upstream-1.6.0; flat okReply/errorReply replies, conventions CMD rules). Source finding: App-4-F20 (catalogJson members), HW-controls-model-F8.

**How to spot it.** grep -n 'substr(1, .*size() - 2)' src/ApertarCoreApp.cpp finds braces cut off a builder's output. For each member of a reply, grep the WebUI and the touch UI for its name; a member with no reader is a candidate to delete. A read command that calls readSharedUiSettings() or camera_.settings() for something the page never shows is the same smell.

**Options.**

- Delete the unread members and have catalogJson return members without braces: -21/+3, one helper changes its contract, and its only in-tree caller is list_actions
- Keep catalogJson with braces and strip only the extra members: smaller diff in the .hpp, but the substr brace strip stays
- Keep values for a future picker: costs a UI.conf read and a settings copy per call for nothing, and the reply is still not flat

**Chosen, and why.** Option 1, as the design page says. The builder now follows okReply's fragment contract, so the caller is one line. Given up: the values lists. No client reads them, and any future picker can ask for the value-step lists, which have their own commands. analog_targets and trigger_events stay, though nothing reads them today either (HW-controls-model-F6 belongs to the hardware-inputs theme).

**After.**

```
// The members of the list_actions reply, without the braces.
inline std::string catalogJson()
{
    std::ostringstream out;
    out << "\"actions\":[";
    ...
    out << "],\"max_per_mapping\":" << maxButtonActions;

    if (command.name == "list_actions")
        return okReply(command.id, hardware::actions::catalogJson());
```

**Checked.**

Run here: the gate (check_core.sh /home/user/wt/lane-hdr lane-hdr both tests, all PASS, 1 warning as before). In --simulate, curl POST /api/command {"cmd":"list_actions"} returns ok, actions (53), analog_targets, trigger_events and max_per_mapping 6. smoke_core.sh (/home/user/build/sim/hdr/smoke-c4.txt) diffed against smoke-c2.txt: the only change is values, values_for and gestures leaving the list_actions reply. Headless Chromium (Playwright) on Settings > Controls (/home/user/build/sim/hdr/pickers.js): the catalog loads with the 5 members, the action selects fill (25 options in the first one), no page errors. controls_page_test.js could not run here because it starts Chrome from a macOS path (line 101). The camera needs no check: the change touches no hardware path.

Check-tool change for the lead to apply: in the copy /home/user/build/sim/hdr/controls_page_test.js, line 32 (the gen.cpp "actions" branch) changes from `std::cout << "{\"ok\":true," << hardware::actions::catalogJson().substr(1);` to `std::cout << "{\"ok\":true," << hardware::actions::catalogJson() << "}";`, because catalogJson() no longer has braces. smoke_core.sh needs no edit; its list_actions shape changes as described above, which is expected.

**Rule.** A JSON builder that feeds okReply returns the members only. Never build braces and cut them off again, and never send a member no client reads.


---

## C26. core, web: controls_last_input, scan_i2c and list_actions take the command lock like every command

Apertar-Core `4b5ad25`. Finding: command-plane commit 5. Reviewed by the lead (no second worker this round).

**What was there.**

src/ApertarCoreApp.cpp:12486-12560@cinemate-port (lane tip before this commit). There was a second dispatcher in front of the lock:
  // The hardware commands that only read: they run without the command lock.
  std::optional<std::string> ApertarCoreApp::handleReadOnlyHardwareCommand(const ControlCommand &command)
  { if (command.name == "controls_last_input") {...} if (command.name == "scan_i2c") {...} if (command.name == "list_actions") ... return std::nullopt; }
  std::string ApertarCoreApp::handleCommand(const ControlCommand &command) {
      if (const auto reply = handleReadOnlyHardwareCommand(command))
          return *reply;
In WebControlPage.cpp (Listen) it was: controlsListenTimer = window.setInterval(async () => { ... await controlsCall({ cmd: "controls_last_input" }) ... }, 300);

**Why it is a problem.** In upstream, handleCommand takes commandMutex_ on its first line and every command is one block in one flat if chain ending in "Unknown command" (App:9091-9093, App:10820@upstream-1.6.0; BRIEF "one command entry point"). When a read must not wait for the lock, upstream makes it an HTTP GET route on the web thread (WS:276-287, App:7168-7173@upstream-1.6.0), not a second door into the command chain. The early door also had a real bug: a take could start in the middle of an I2C scan, because the scan checked recordingGateActive() only once. And setInterval does not wait for an async callback, so while a long command held the lock, Listen piled up a new request every 300 ms. The missing-argument sentence follows STY-10 (C1-I07): "<command> requires <field>.".

**How to spot it.** grep -n "std::optional<std::string> .*Command(" src/ApertarCoreApp.hpp, and look for any call above the std::lock_guard in handleCommand. In page JS, grep -n "setInterval(async" src/web/WebControlPage.cpp: an async setInterval does not wait for its reply, so requests pile up when Core is slow.

**Options.**

- Move the three blocks under the lock and turn Listen into a setTimeout chain (the plan): a pure move plus about 10 lines; Listen and scan now wait behind a long command.
- Make the three reads GET routes, as was done for get_controls: no lock, but three more routes for live state and command data, and more page churn.
- Leave the pre-lock helper and only document it: no work, but the second dispatcher and the scan-versus-take race stay.

**Chosen, and why.** Option 1, as the design page says. The blocks moved byte for byte (git diff --minimal shows a pure move), apart from the bus sentence, which became "scan_i2c requires bus.". The comment above test_input was already there and already says why it stays before the lock, so I kept it and did not add the planned line. In the WebUI, each tick awaits its reply and then schedules the next tick 300 ms later. A module variable controlsListenStarted lets a stopped or restarted Listen end the old chain once its reply comes back. A .catch keeps the chain alive after a network error, the way setInterval kept firing before. Given up: while the safety-stop drain or record_start holds the lock, the Listen highlight and the scan now wait for it. The 1 s scan bound from commit 3 caps how long a scan can hold the lock.

**After.**

```
    if (command.name == "scan_i2c") {
        if (recordingGateActive())
            return errorReply(command.id, "Not during a take: scan the I2C bus when the camera is idle.");
        const auto busValue = command.number("bus");
        if (!busValue || *busValue < 0 || *busValue > 255)
            return errorReply(command.id, "scan_i2c requires bus.");
  // WebUI: const listen = async () => { ...; const reply = await controlsCall(...).catch(() => ({ ok: false }));
  //   if (!controlsState.listening || controlsListenStarted !== started) return; controlsListenTimer = window.setTimeout(listen, 300); ... };
```

**Checked.** Run here: /home/user/build/bin/check_core.sh /home/user/wt/lane-hdr lane-hdr both tests gave PASS on both builds and 18 host tests. The one warning, convertPlanarYuv420ToRgb unused at App:4742, was already there in code this commit does not touch. I ran --simulate with APERTAR_HARDWARE_CONFIG set to a copy of the controls fixture (/home/user/build/sim/hdr/hw.conf) and sent controls_last_input, scan_i2c (with and without bus), list_actions and help over curl POST /api/command. I drove Settings > Controls in Playwright with /home/user/build/sim/hdr/listen.js. Listen lit row 0 from a routed controls_last_input reply. With a 1.5 s reply delay, at most one request was in flight. Stop ended the polls. A quick stop/start leaves the old chain's one request plus the new one in flight, and the old chain then ends. There were no page errors. I did not run controls_page_test.js: it needs a fixture beside it and still mocks get_controls, which earlier commits removed. Its copy at /home/user/build/sim/hdr/controls_page_test.js is unchanged, and its Listen check (:264-266) stays valid. Note that test_input does not call noteInputSeen, so in --simulate Listen can only be tried with a routed reply. Needs the camera: start a take, press Listen and turn a knob; the row lights within about 0.3 s and recording_dropped_frames stays 0. Press Listen, then start and stop a take; at the stop REC updates within 1 s and DevTools > Network shows at most one pending controls_last_input. Then run python3 ~/apertar-kb/working/tools/core.py scan_i2c bus=1 during a take; it is refused.

**Rule.** One door, one lock: every command is a block of handleCommand's chain under commandMutex_. A read that must not wait becomes a GET route, not a second dispatcher before the lock.


---

## C27. hw: a whole-file save writes the file and reports what the checker found

Apertar-Core `43d8a19`. Finding: hardware-inputs commit 1. Reviewed by a second agent: accept.

**What was there.**

src/hardware/HardwareConfigStore.cpp:336-342@cinemate-port (saveLocked). The checker could veto every save, whole-file text saves included:
    result.newErrors = hwconf::newErrors(hwconf::validate(current, facts), result.issues);
    if (!result.newErrors.empty() && !flags.force) {
        result.code = "errors";
        result.error = "Not saved: " + ... + result.newErrors.front().message;
        return result;
    }
POST /api/config never sets force. The WebUI Check said ". Save is refused until the errors are fixed." (WebControlPage.cpp:18885).

**Why it is a problem.** The port's checker, hwconf::validate, is a second copy of the readers' rules, and it disagrees with them. It refused files every reader accepts. Example: d17=capture twice in [gpio_buttons] is a duplicate_key "error", but the reader just takes the later line. Original Apertar checks a whole-file save only for empty, 256 KiB and NUL bytes, then writes it with .bak and .tmp+rename (saveHardwareConfigFile, src/ApertarCoreApp.cpp:5323-5386@upstream-1.6.0). The readers are the authority: they keep their defaults for anything they cannot use and ignore unknown keys (HW-12). The WebUI is for a trusted LAN (WEB-6), so the operator's whole file wins.

**How to spot it.** Look for a validator result that ends in a `return` with ok=false on a path where upstream has no such check: grep -n 'validate(' src/hardware/HardwareConfigStore.cpp, then compare with saveHardwareConfigFile at App:5323-5386@upstream-1.6.0. Ask: does any reader really refuse this file? If the reader only logs or keeps a default, the save must not be refused.

**Options.**

- Compute newErrors only when edits is set, so the existing refusal block fires for key edits only: +1 line, no re-indent, and new_errors keeps meaning 'what blocked the save' (chosen)
- Wrap the whole refusal block in if (edits) { ... }: same behaviour, but 6 lines re-indented for review
- Keep computing newErrors for every save and test 'edits && ...' in the condition: text-save refusals for other reasons would then carry a non-empty new_errors, and the page shows that list first
- Make key edits advisory too: owner question 5 says keep the refusal, because the page writes keys the operator did not type

**Chosen, and why.** I made newErrors a key-edit-only result: `if (edits) result.newErrors = ...;`. The refusal below it is unchanged. Text saves leave newErrors empty, so the refusal cannot fire for them and no error reply carries a misleading new_errors list. What we give up: a stale text save that the port merges key by key (it still has a null edits pointer) is not refused on new errors either. That merge path is deleted by commit 5 of this page and already stops at needs_review / merge_review. The plan's Check example was wrong: a key edit that sets d18=capture next to d17=capture adds no error. The test used set.gpio_buttons.d18=no_such_action instead, which raises an unknown_action error.

**After.**

```
    // A whole-file save is written whatever the checker finds, as in 1.6.0: the readers skip what they cannot use
    // and the reply names the issues. A key edit that adds an error is refused: the page writes keys nobody typed.
    if (edits)
        result.newErrors = hwconf::newErrors(hwconf::validate(current, facts), result.issues);
    if (!result.newErrors.empty() && !flags.force) {
HardwareConfigStore.hpp:  bool force = false;         // key edits only: save although the edit adds errors
WebControlPage.cpp:  ". Save writes the file anyway; the readers skip what they cannot use."
```

**Checked.**

Gate: /home/user/build/bin/check_core.sh /home/user/wt/lane-core3 lane-core3 both tests: PASS, PASS, PASS, and no warnings in the touched files. I then ran /home/user/build/lane-core3-lc/apertar-core --simulate on port 8180, with APERTAR_HARDWARE_CONFIG, XDG_CONFIG_HOME and HOME pointed at a scratch folder. Results:
(1) curl -X POST --data-binary @dup.conf /api/config, where dup.conf has d17=capture twice: ok:true, written:true, errors:1, one duplicate_key issue, and the file holds the text.
(2) set_controls with set.gpio_buttons.d18=no_such_action: refused with "Not saved: 1 new error. Unknown action ...", and the file is unchanged. The same call with force=true and dry_run=true returns ok.
(3) Playwright/Chromium: Check on the dup text shows "Checked: 1 error, 0 warnings. Save writes the file anyway; the readers skip what they cannot use."; Save writes the file and shows "Saved. Core found 1 thing to look at".
Pi: nothing to check, because no hardware path changed.

**Rule.** A checker that copies the readers' rules may advise on a whole-file save, never veto it: the readers decide what a file means.


---

## C28. hw: Undo and restore put back a kept version with its script paths

Apertar-Core `1a417c8`. Plan: `design/hardware-inputs.md` commit 2, **rewritten by the lead**. Finding: HW-config-text-store-F2. Recorded decision: controls Q2 (DA-4).

**What was there.** The port's hardware-file store compares the `[run_script]` paths of the text it is asked to save with the paths in the file, and refuses the save when they differ:

```
src/hardware/HardwareConfigStore.cpp:330@cinemate-port
    if (scriptPaths(nextDoc) != scriptPaths(currentDoc)) {
        result.code = "script_paths";
        result.error = "Script paths are changed over ssh, not here.";
```

The same test runs for Undo (`set_controls text=<history version> by=webui_undo`), for a History version and for `restore=true`.

**Why it is a problem.** Two problems, and they pull in opposite directions.

1. The refusal also hits Undo. Change a path over ssh, then press Undo in the WebUI: the version Undo wants to put back has the old path, so it is refused. A saved version could never be brought back across a path change.
2. The plan said: delete the test, as in 1.6.0 (the 1.6.0 Config page writes the whole file without any check). A worker made that commit (`7e3a0c0`). But the test is not the port's accident: it is Patrik's decision Q2 of 2026-10-29, "`[run_script]` paths: ssh only; the browser cannot write them", recorded in `working/controls/decisions.md:10`. The review's plan was written without reading that page. I found it by chance while checking a different item, stopped the lane and threw the worker's commit away.

**How to spot it.** A check that looks over-strict may be a decision. Before deleting a rule, grep the knowledge base for its message text and for the feature's decision page: `grep -rn "ssh" ~/apertar-kb/working/controls/`. Here the refusal text "changed over ssh" leads straight to Q2.

**Options.**

- Delete the test (the plan): 1.6.0 behaviour, but it reverses Patrik's decision.
- Keep the test and exempt Undo and restore by the client's word (`by=webui_undo`): small, but any client can send that word, so the rule would be gone in practice.
- Keep the test and let a save through when its paths are the paths of a version **Core itself kept** (the history folder, the last text it wrote): those paths were on the camera before, set over ssh once.

**Chosen, and why.** The third. It compares the paths themselves, so it cannot be fooled by what the client says it is. In C++ terms: `keptScriptPaths()` loops over the files in `hardware-history/` with `std::filesystem::directory_iterator`, parses each with the same `hwconf::parse` the store already uses, and compares the two `std::map<std::string, std::string>` path maps with `==` (a map compares equal only when every key and value match).

**After.**

```
    const auto nextPaths = scriptPaths(hwconf::parse(next));
    if (nextPaths != scriptPaths(currentDoc) && !keptScriptPaths(notes_, nextPaths)) {
        result.code = "script_paths";
```

**Checked.** Ran here, `--simulate` with a hardware file holding `path1=a.sh`: a browser save with a new path is refused; a save of another key is written; after the file is changed outside Core to `b.sh`, Undo to the earlier version is written and the file holds `a.sh` again; an "Undo" that carries a path no kept version has is refused. Both builds and the host tests pass.

**Rule.** Before removing a rule the port added, look for the decision behind it in the knowledge base. A rule Patrik decided stays; the review only changes how it reaches a stock camera (next entry).


---

## C29. hw: the ssh-only rule for script paths is a switch, off as in 1.6.0

Apertar-Core `f4de756`. Plan: the decisions audit of `design/hardware-inputs.md`. Made by the lead.

**What was there.** After C28 the script-path rule ran on every camera.

**Why it is a problem.** The campaign has one rule for features the port added: a stock camera (original driver, 720x720 screen, a 1.6.0 hardware file) behaves as Apertar 1.6.0 until the operator turns the feature on. On 1.6.0, the WebUI's Config page can change script paths. With C28 alone, a stock camera loses that after the merge. Patrik's decision is about his camera and his Controls design; the original developer has not made it for every camera.

**How to spot it.** For each rule the port adds, ask: "what does a camera that has never heard of this feature do after the update?" If the answer differs from 1.6.0, the rule needs a switch with the 1.6.0 value as its default.

**Options.**

- A key in the hardware file, for example `[run_script] browser_paths=false`: but the browser can write the hardware file, so it could switch the protection off with the same save it wants to make. A lock whose key hangs on the door.
- A camera setting in `camera_settings.conf`: Core would need a new setting, a command to change it, and that command would be reachable from the network again.
- An environment variable of the Core service. Only someone with a shell on the camera (ssh) can change it, which is exactly the boundary Q2 draws. Upstream already reads switches this way at the point of use (`std::getenv("APERTAR_LOSSYDNG_ASYNCWRITE")` in `LossyDngEncoder.cpp`).

**Chosen, and why.** The environment variable `APERTAR_SCRIPT_PATHS=ssh`. Unset means 1.6.0. Its value names what it does, so a drop-in file reads as a sentence. The cost: the protection is off on a stock camera, as it was in 1.6.0. The handoff recommends to the original developer that it become the default, as a separate decision for him.

**After.**

```
    // APERTAR_SCRIPT_PATHS=ssh: a new [run_script] path is set over ssh only (1.6.0 lets the browser write it).
    const char *scriptPathsEnv = std::getenv("APERTAR_SCRIPT_PATHS");
    const auto nextPaths = scriptPaths(hwconf::parse(next));
    if (scriptPathsEnv && std::string(scriptPathsEnv) == "ssh" && nextPaths != scriptPaths(currentDoc) &&
        !keptScriptPaths(notes_, nextPaths)) {
```

`std::getenv` returns `nullptr` when the variable is not set, so the `scriptPathsEnv &&` test comes first: comparing a null pointer as a string would crash.

**Checked.** Ran here, each case with a fresh state folder: unset, a browser save with a new path is written (1.6.0); with `APERTAR_SCRIPT_PATHS=ssh` it is refused with "Script paths are changed over ssh, not here." and a save of another key is written. (A first run shared one state folder between the two cases, and the second case wrongly passed: the first had saved the new path, so it counted as a kept version. The rule worked; the test did not. Fresh folder per case.) Needs the camera: add `Environment=APERTAR_SCRIPT_PATHS=ssh` to a drop-in of `apertar-core.service` on the rig, `sudo systemctl daemon-reload`, restart Core, and check the Config page refuses a changed path.

**Rule.** A security switch lives where the attacker cannot reach it. A setting the browser can write cannot protect against the browser.

---

## C30. hw: every whole-file save gets the empty, size and binary checks

Apertar-Core `8bfc242`. Finding: hardware-inputs commit 3. Reviewed by a second agent: accept.

**What was there.**

The port ran the upstream sanity checks only on POST /api/config, at src/ApertarCoreApp.cpp:8628@cinemate-port. The set_controls branch (src/ApertarCoreApp.cpp:12780-12803@cinemate-port) passed its text straight to the store:
    if (!text && edits.empty())
        return errorReply(command.id, "set_controls needs text= ...");
    hardware::StoreFlags flags;
    ...
    ? hardware::configStore().replace(*base, *text, by, flags, hardwareConfigFacts())
That covers text= (WebUI Undo, history restore) and the text that restore=true resolves.

**Why it is a problem.** There were two doors for writing the whole file, and only one of them was guarded. An empty text, a text with a NUL byte or a huge text could reach the hardware file through Undo, a socket client or restore=true. The store's own base and no-change tests do not catch these. Original Apertar has one whole-file save, saveHardwareConfigFile (src/ApertarCoreApp.cpp:5325-5341@upstream-1.6.0). It refuses empty text ("Config file cannot be empty."), text over 256 KiB ("Config file is too large.") and NUL bytes ("Config file contains invalid binary data.") before it writes anything. Finding HW-config-text-store-F5.

**How to spot it.** grep -n 'configStore().replace(' src/ApertarCoreApp.cpp, then check that every call is preceded by checkHardwareConfigText. More generally: when a guard sits on one HTTP route, ask which socket command or restore path reaches the same writer without it.

**Options.**

- Call checkHardwareConfigText in the set_controls branch after restore=true resolves the text: +3 lines, checks stay in App where 1.6.0 has them (chosen)
- Move the three checks into HardwareConfigStore::replace: every caller is covered, but upstream-shaped App code moves into the port's store and POST /api/config would change
- Make the WebUI send Undo and restore through POST /api/config: changes the page and the restore flow; that is webui-state's item WCP-09-F12, not this one

**Chosen, and why.** Option 1. It is the smallest change. It reuses the existing helper, and its error sentences are identical to 1.6.0. The check sits after the restore=true block, so the restored text is checked too. It also sits before the store's base test, so an empty text is refused even with a stale base. Given up: a new whole-file caller of the store outside App would have to call the helper itself. Today there is none: the IMU and storage writers make key edits, not whole-file saves.

**After.**

```
        // A whole file, restored text included, gets the same checks as POST /api/config.
        if (std::string message; text && !checkHardwareConfigText(*text, &message))
            return errorReply(command.id, message);
(C++17 if-with-initializer: the message string lives only inside the if, the same shape as the parseEdits check just above it.)
```

**Checked.**

Run here: check_core.sh /home/user/wt/lane-core3 lane-core3 both tests (both builds and 18 host tests PASS). Then a --simulate run on port 8173 with APERTAR_HARDWARE_CONFIG=/home/user/build/sim/core3/hw.conf:
- set_controls text="" with the current base: "Config file cannot be empty."
- text "  \n" with a stale base: "Config file cannot be empty."
- a text with \u0000: "Config file contains invalid binary data."
- 256 KiB + 1 bytes: "Config file is too large."
- md5sum of the file was the same before and after these four.
- A normal text= save still wrote (ok:true, written:true).
- POST /api/config with an empty body still replied "Config file cannot be empty."
Needs the camera: nothing. No hardware path changes.

**Rule.** Every door that writes a whole file runs the same sanity checks, in the place where the original code runs them.


---

## C31. core, web: hardware-file refusals are one sentence

Apertar-Core `926a62b`. Finding: command-plane commit 6. Reviewed by the lead (no second worker this round).

**What was there.**

src/ApertarCoreApp.cpp:12801@cinemate-port (same shape at :12841, :12881, :12915):
        if (!result.ok) {
            return errorReplyBody(command.id, result.error,
                "\"code\":\"" + escapeJson(result.code) + "\",\"revision\":\"" + escapeJson(result.revision) + "\""
                ",\"issues\":" + controlsIssuesJson(result.issues) + ...
src/web/WebControlPage.cpp:18662@cinemate-port:
          const kept = result.code === "stale" || result.code === "conflict"
            ? " Your choices stay on the page. Press Reload to see the newer file." : "";

**Why it is a problem.** A refusal carried a second error vocabulary (code) and lists, and the page translated the code into its own words. Original Apertar has two reply builders only, okReply and errorReply (src/ApertarCoreApp.cpp:108-128@upstream-1.6.0), and every surface shows the refusal sentence as written (CMD-9, CMD-28, WEB-14). The Check button also sent base "h", which is no revision, so a Check before the file loaded was always refused as stale (WCP-10-F7).

**How to spot it.** grep -n 'errorReplyBody\|"code\\"' src/ApertarCoreApp.cpp, and in the page grep -n 'result.code ===\|new_errors' src/web/WebControlPage.cpp. A page that appends its own text to Core's error is translating a code; ask why Core's sentence does not say it.

**Options.**

- errorReply(id, result.error) in the five commands, Core's sentence on the page, conflict sentence completed: about -35/+18, one reply shape (chosen)
- Keep the lists in refusals as a documented extension: no page change, but two error shapes stay
- Also skip the store's new-errors refusal on a dry run (the plan): after C27 a text Check is never refused on new errors, so this would only make a key-edit dry run say ok while the real save is refused

**Chosen, and why.** Option 1, without the plan's store change for dry runs. The code contradicted the plan there: since C27 newErrors is computed only for key edits (if (edits) ...), so Check (a text dry run) already answers ok:true with its issues; adding && !flags.dryRun would break the store's rule that a dry run's ok means 'would save'. Given up: a refused key edit names only the count and the first new error; Check lists all. Kept on purpose: StoreResult::conflicts and hwconf::conflicts (they decide the refusal), textToEdits, needs_review/merged/confirm_merge (Q17's unbuilt review) and "Script paths are changed over ssh, not here." (Q2). The Undo refusal's read of result.issues also went, because no refusal carries issues now.

**After.**

```
        if (!result.ok)
            return errorReply(command.id, result.error);
  store: "The file changed in the same place since you loaded it. Reload, then change it again."
  page:  showControlsMessage(result.error || "Could not save the controls.", [], false);
         controlsCall({ cmd: "set_controls", base: state.configRevision, ..., dry_run: "true" })
         if (checkButton) checkButton.disabled = !state.configRevision;
```

**Checked.** Here: the gate (above). --simulate with HOME and APERTAR_HARDWARE_CONFIG in /home/user/build/sim/cp2/c6a: a key edit adding an error -> "Not saved: 1 new error. Unknown action ..."; a second edit from the old base -> the conflict sentence with "Reload, then change it again."; a stale base on set_controls, set_buffer_mode, set_clip_merge, set_frames_per_folder, set_storage_preroll -> the stale sentence only; a stale values-only text save -> ok, merged:true, needs_review:true. c6b with APERTAR_SCRIPT_PATHS=ssh: save and dry run -> "Script paths are changed over ssh, not here.". Chromium (/home/user/build/sim/cp2/c6-page.js): Check disabled with no revision, enabled after load, lists "Line 3: Unknown action ..."; stale and error-adding Controls saves and a stale Hardware save show Core's sentence and keep the edits; no page errors. smoke_core.sh -> smoke-1.txt; shape_subset vs smoke-upstream.txt: every base field present with the same type. Camera: nothing, no hardware path changes.

**Rule.** A refusal is one sentence through errorReply; the page shows it as written. Lists of what is wrong belong in ok replies (a dry run), not in refusals.


---

## C32. core, web: a config text save names its revision only to be refused when stale

Apertar-Core `46d28cd`. Finding: command-plane commit 7. Reviewed by the lead (no second worker this round).

**What was there.**

src/ApertarCoreApp.cpp:8611@cinemate-port (POST /api/config):
        const auto revisionHeader = request.headers.find("x-apertar-revision");
        if (revisionHeader == request.headers.end() && request.headers.count("origin")) {
            response.status = 409;
            response.body = errorReplyBody(-1, "Apertar was updated: reload this page. Your text stays in the box.",
                                           "\"code\":\"old_page\"");
  ... response.body = errorReplyBody(-1, message, "\"code\":...,\"conflicts\":" + controlsConflictsJson(result.conflicts));
WebControlPage.cpp: const kept = payload.code === "stale" || payload.code === "conflict" || payload.code === "merge_review" ? " Your text stays in the box. ..." : "";

**Why it is a problem.** The route behaved differently for a browser (Origin header) and a script, and spoke a second error vocabulary (code). Upstream's POST /api/config saves the text, last writer wins, and refuses only with errorReply(-1, sentence) and an HTTP status (src/ApertarCoreApp.cpp:7175-7195@upstream-1.6.0; WEB-5, CMD-9). Core and page ship together (CMD-30), so a tab from before an update needs no machine code. A header beside a raw body is upstream's own shape: x-preset-filename (src/ApertarCoreApp.cpp:7396-7400@upstream-1.6.0), so the revision header stays.

**How to spot it.** grep -n 'headers.count("origin")\|"code\\"' src/ApertarCoreApp.cpp. A route that asks who is calling (browser or script) to decide what a request means is a smell: the same request should mean the same thing from every client.

**Options.**

- Delete the Origin test; a missing header means the current revision; errorReply with the status kept (chosen): -35/+7, 1.6.0 behaviour without the header
- Keep old_page on Origin presence: protects one tab left open across an update, at the cost of a client-dependent rule and a code
- Require the header from every client: scripts and the KB restore step (curl without header) break

**Chosen, and why.** Option 1, as the plan says. Given up: a tab left open across an update can save over a newer file once (owner row a, 'old_page'). Kept: the revision header, the store's merge review (a stale values-only save still answers 409 'Reload; your text stays in the box.'), and the script-path rule, which does not depend on the header. Not in the plan: controlsConflictsJson had this route as its last caller after commit 6; it is in the anonymous namespace, so leaving it would add a -Wunused-function warning, and it is removed. The store still computes the conflicts list (StoreResult::conflicts) that decides the refusal. A refused save now always fills the issue box with the sentence (before, only when the reply had a payload; a network error now also shows there).

**After.**

```
        // The page names the revision it loaded, to be refused when the file is newer. Without it the text is
        // saved over the current file, as in 1.6.0.
        const auto revisionHeader = request.headers.find("x-apertar-revision");
        const std::string base = revisionHeader != request.headers.end() ? revisionHeader->second : store.currentRevision();
        ...
            response.status = changed ? 409 : 400;
            response.body = errorReply(-1, message);
  page:  if (!payload.ok) throw new Error(payload.error || "Could not save config.");
         showConfigIssues(error.message || "Could not save config.", []);
```

**Checked.** Here: the gate (above). --simulate in /home/user/build/sim/cp2/c7a with its own hardware file: curl -X POST --data-binary @a.txt /api/config without the header -> 200, written; with -H 'Origin: http://127.0.0.1:8175' and no header -> 200, written; with a stale X-Apertar-Revision -> 409 {"ok":false,"error":"The file changed ... Reload, then change it again."}; empty body -> 400 "Config file cannot be empty.". Chromium, two tabs (/home/user/build/sim/cp2/c7-page.js): tab two's save is refused with Core's sentence, its text stays in the box, the file has tab one's line only; no page errors. smoke-2.txt vs smoke-upstream.txt: every base field present with the same type. Camera: nothing.

**Rule.** A request means the same from every client: do not read Origin to decide what a save means. An optional header may narrow a save (refuse when stale); without it the 1.6.0 behaviour holds.


---

## C33. core, web: playback routes refuse through errorReply

Apertar-Core `d092b04`. Finding: command-plane commit 8. Reviewed by the lead (no second worker this round).

**What was there.**

src/ApertarCoreApp.cpp@cinemate-port, the frame route (same at the sound, download and download-selected routes):
            response.status = 409;
            response.body = "{\"ok\":false,\"error\":\"Playback held: " + hold + ".\",\"hold\":\"" + hold + "\"}";
            response.status = 404;
            response.body = "{\"ok\":false,\"error\":\"This clip was removed.\",\"gone\":true}";
                response.body = "{\"ok\":false,\"busy\":true}";
WebControlPage.cpp: pbvApplyHold(clip.hold || state.pb.snapshotHold || "recording");

**Why it is a problem.** Hand-built JSON bypasses errorReply and carries a second vocabulary (hold tokens, gone, busy); the sentences were tokens ("Playback held: media_test.") or missing. Original Apertar answers a route refusal with errorReply(-1, sentence) and a status (WEB-5, CMD-9) and its busy sentences say what to do: "Stop recording before deleting media." (src/ApertarCoreApp.cpp:7514-7520@upstream-1.6.0), "Wait for the media speed test to finish first." (:9110). The clip route's 409 already had no hold member at the tip, so the viewer fell back to the last 1 s poll: a clip opened in standby right after a poll showed the Recording card instead of Wake (Patrik's DA-65, playback held in standby).

**How to spot it.** grep -n 'response.body = "{' src/ApertarCoreApp.cpp finds JSON built by hand. In the page, a member read from an error body (body.gone, clip.hold) is a second protocol beside the status code.

**Options.**

- One local lambda holdResponse(hold) -> 409 + errorReply sentence; 410 for gone, 503 + sentence for busy; the page reads the hold from GET /api/state on a held clip open (chosen): -45/+46
- Keep a hold member in the refusal: no page fetch, but a second vocabulary in error replies stays
- Let the page map hold from its last poll only (the plan as first written): one fewer request, but a stale poll shows the wrong card (the audit's conflict with DA-65)

**Chosen, and why.** Option 1, with the audit's change. A C++ lambda defined at the top of handleWebRequest is a small local function object; CMD-25 names that shape for a repeated block. The empty hold after an interrupted frame read falls to the recording sentence, as before (why = "recording"). All recording holds (take, sound recorder, timelapse) use "Stop recording or the timelapse before playing or downloading media.", because the hold name does not tell them apart. The state lookup awaits, so the page checks the viewer is still the same clip before showing the card. Given up: the download sentence "Recording. Downloads wait until the take ends." (one family sentence now), and one extra GET /api/state when a clip open is held.

**After.**

```
    const auto holdResponse = [](const std::string &hold) {
        WebServer::Response response;
        response.status = 409;
        ...
        const char *sentence = hold == "writing" ? "Wait for the current capture to finish writing to media."
            : ... : "Stop recording or the timelapse before playing or downloading media.";
        response.body = errorReply(-1, sentence);
    if (const std::string hold = playbackHoldReason(); !hold.empty())
        return holdResponse(hold);
  page: if (response.status === 410) return { outcome: "gone" };  /  hold = String(snapshot.playback_hold || "") || hold;
```

**Checked.** Here: the gate (above). --simulate with a copied cDNG clip folder (/home/user/build/sim/cp2/c8a): during record_start the frame, file, download and download-selected routes answer 409 with the recording sentence; after enter_standby 409 "Wake the camera first."; a frame of a missing clip 410 "This clip was removed."; an idle frame 200 image/jpeg. Chromium (/home/user/build/sim/cp2/c8-page.js): standby, last poll set to no hold, open the clip -> requests /api/media/clip then /api/state, card "Standby / Wake the camera to play clips."; c8-gone.js: the frame outcome is ok, then gone after the folder is deleted; no page errors. smoke-3.txt vs smoke-upstream.txt: every base field present with the same type. Camera: play a clip, press record; playback stops before the first frame is written, and curl -s localhost:8000/api/state shows recording_dropped_frames 0. Not exercised here: the writing, media_test and media sentences and the 503 busy reply (simulate has no slow card).

**Rule.** A route refusal is a status plus errorReply's sentence. Where the page needs to know more (which hold), it asks a lock-free state route, not a member hidden in the error body.


---

## C34. core: Boot Config and set_controls switches read true or false, 1 or 0

Apertar-Core `111ccf7`. Finding: command-plane commit 10. Reviewed by the lead (no second worker this round).

**What was there.**

src/ApertarCoreApp.cpp@cinemate-port (boolFieldValue, bootConfigSet):
    std::transform(v.begin(), v.end(), v.begin(), ... std::tolower ...);
    if (v == "true" || v == "1" || v == "on" || v == "yes")
        return true;
    const bool dryRun = boolFieldValue(command.string("dry_run").value_or("false")).value_or(false);
  set_controls:
            if (const auto value = command.string(name); value && !parseBooleanToken(*value, flag))

**Why it is a problem.** A switch whose wrong value writes a file must refuse the wrong value. .value_or(false) on an std::optional turned 'not understood' into 'false', and for dry_run false means 'write config.txt'. Original Apertar has two boolean forms: lenient (true/1, else off) for a plain switch, strict (true/1, false/0, else refused) where a wrong value must not pass: set_standby_usb_power_off, src/ApertarCoreApp.cpp:9130-9133@upstream-1.6.0 (conventions section 4, CMD-8). parseBooleanToken was written to read timedatectl output (yes/no) and was reused for commands.

**How to spot it.** grep -n 'value_or(false)' src/ApertarCoreApp.cpp near a parser that returns std::optional: a nullopt (parse failure) silently becomes a value. Ask of each boolean flag: what happens if the client sends a typo?

**Options.**

- Strict boolFieldValue and refusal of a bad dry_run/confirm_display; the set_controls flags on the same helper (chosen): about -12/+19
- Keep the lenient words, refuse only unknown words: still accepts on/yes where upstream does not, two dialects of boolean
- Lenient upstream form (true/1 else false): a typo in dry_run would then write, the problem itself

**Chosen, and why.** Option 1, as the plan with its extra. The new refusal in bootConfigSet uses the same errorReplyBody 'invalid' shape as the refusal right above it, because command-plane commit 9 converts all Boot Config refusals at once; a lone errorReply there would mix two shapes in one function. Given up: scripts that sent yes/on/True; none found in the KB tools (grep). The page sends JSON booleans, which the command parser stores as the strings true/false, so the card is unaffected.

**After.**

```
// A switch that decides whether a file is written: true or 1, false or 0, nothing else.
std::optional<bool> boolFieldValue(const std::string &value)
{
    if (value == "true" || value == "1")
        return true;
    ...
    if (!dryRunValue || !confirmDisplayValue)
        return {400, errorReplyBody(command.id, std::string(dryRunValue ? "confirm_display" : "dry_run") + " must be true or false.", ...)};
```

**Checked.** Here: the gate (above; boot_config_test is one of the 18). --simulate (/home/user/build/sim/cp2/c10a): set_controls dry_run=yes, on, True -> "dry_run must be true or false."; restore=yes and force=no refused; md5sum of the hardware file unchanged by those; dry_run "true", JSON true and 1 -> dry run, 0 -> a real save. set_boot_config dry_run=yes and confirm_display=on -> refused 400; POST /api/boot-config {"dry_run":"yes"} -> 400; {"dry_run":true} passes the flag check and stops at 'Could not read /boot/firmware/config.txt.' (no config.txt here). smoke-4.txt: every base field present with the same type. Camera: on the Pi, the Boot Config card's review and Save still work (python3 ~/apertar-kb/working/tools/core.py set_boot_config dry_run=true answers the review; dry_run=yes is refused).

**Rule.** A flag whose wrong value writes a file is parsed strictly and refused when not understood; never turn a parse failure into a value with value_or.


---

## C35. camera: the new camera switches are written 0 and 1 in camera_settings.conf

Apertar-Core `ee141f9`. Finding: command-plane commit 15. Reviewed by the lead (no second worker this round).

**What was there.**

src/camera/CameraController.cpp:963,974-979@cinemate-port (writeCaptureSettings):
    output << prefix << "clear_hdr=" << (s.clearHdr ? "true" : "false") << '\n';
    output << prefix << "fps_phase_lock=" << (s.fpsPhaseLock ? "true" : "false") << '\n';
    output << prefix << "preview_tdn=" << (s.previewTdn ? "true" : "false") << '\n';
    output << prefix << "media_trim=" << (s.mediaTrimEnabled ? "true" : "false") << '\n';
    ... fps_speed_ramp, fps_speed_ramp_keep_exposure, fps_speed_ramp_stretch_audio the same

**Why it is a problem.** One file, two spellings of a boolean. 1.6.0 writes its switches by streaming the bool, which gives 0 or 1: output << prefix << "iso_auto=" << s.isoAuto (src/camera/CameraController.cpp:749@upstream-1.6.0), read back with std::stoul(value) != 0 (:659-660). The port's lines are the only true/false in the file (X-knobs-19, CC-1-F4).

**How to spot it.** grep -n '? "true" : "false") << .\\n.' src/camera/CameraController.cpp: in a settings writer (not JSON) this spelling differs from the file's other switches.

**Options.**

- Stream the bool (0/1) and keep the lenient readers (chosen): 7 lines, old files keep loading
- Also change the readers to std::stoul(value) != 0: would read a port file's 'true' as an error and fall back to the default, losing the operator's setting
- Leave true/false: no change, the file keeps two spellings

**Chosen, and why.** Option 1. In C++, streaming a bool into an std::ostream without std::boolalpha writes 0 or 1, which is exactly what upstream relies on. The readers stay as they are, so a file the port wrote (true/false) loads unchanged and is rewritten in 0/1 at the next debounced persist, the way upstream rewrites the whole file on every change. Downgrade: fork main reads clear_hdr as true or 1 (core-main CC:710-711), and 1.6.0 ignores the port keys, so going back is safe. fps_speed_ramp_after=return|stay stays: it is an enum word. Given up: nothing.

**After.**

```
    output << prefix << "clear_hdr=" << s.clearHdr << '\n';
    output << prefix << "fps_phase_lock=" << s.fpsPhaseLock << '\n';
    output << prefix << "preview_tdn=" << s.previewTdn << '\n';
    output << prefix << "media_trim=" << s.mediaTrimEnabled << '\n';
    output << prefix << "fps_speed_ramp=" << s.fpsSpeedRamp << '\n';
```

**Checked.** Here: the gate (above; the 3 nolc warnings are the old ones in CameraController.cpp at 1242, 7782, 7935, not in these lines). --simulate with HOME=/home/user/build/sim/cp2/c15a and a camera_settings.conf holding preview_tdn=true, media_trim=false, fps_phase_lock=true: get_state shows preview_tdn and fps_phase_lock true; after set_iso value=400 the file holds clear_hdr=0, fps_phase_lock=1, preview_tdn=1, media_trim=0, fps_speed_ramp=0, fps_speed_ramp_keep_exposure=0, fps_speed_ramp_stretch_audio=1; a restart reads the same values. Camera: nothing; on the rig, grep preview_tdn ~/.config/apertar-core/camera_settings.conf after the first settings change shows 0 or 1 and the WebUI shows the same switch state as before.

**Rule.** In a settings file, write a new switch the way the file's existing switches are written; keep the reader accepting the old spelling so files written before still load.


---

## C36. core: set_value_steps echoes the lists flat

Apertar-Core `86a33a1`. Finding: command-plane commit 16. Reviewed by the lead (no second worker this round).

**What was there.**

src/ApertarCoreApp.cpp:14178@cinemate-port:
        if (!updateSharedUiGeneralSettings(updates))
            return errorReply(command.id, "Could not save the value list.");
        return okReply(command.id, "\"ui\":{" + valueStepsJson(readSharedUiSettings(), camera_.sensorName()) + "}");

**Why it is a problem.** A command reply that nests its values in an object breaks the flat reply shape (CMD-8, CMD-9) and borrows the "ui" group, which in 1.6.0 exists only in /api/state (CMD-11). Upstream's UI.conf commands echo what they stored flat: okReply(command.id, "\"sleep_mode\":...") (src/ApertarCoreApp.cpp:9802-9813@upstream-1.6.0; CMD-6). Finding App-5-F5 (the reply part).

**How to spot it.** grep -n 'okReply(command.id, "\\"[a-z_]*\\":{' src/ApertarCoreApp.cpp finds replies that nest an object. Before changing a reply, grep every client for the command name: grep -rn set_value_steps src ../ui-work/src ../ui-work/qml.

**Options.**

- Drop the wrapper, same members (chosen): 1 line; safe because no client reads the reply
- Keep the wrapper: no change, but the reply stays nested and looks like /api/state
- Return only what changed (one list): smaller reply, but a different member set per call

**Chosen, and why.** Option 1, as the plan says, after the check the instructions asked for. Readers: WebControlPage.cpp:8494 sendValueSteps only awaits sendCommand; sendCommand's applyCommandSnapshotPatch reads result.state and result.imu generically, never result.ui, and has no set_value_steps case; the card redraws from the next /api/state. The touch UI (/home/user/wt/ui-work) has no sender: its three hits are comments (SettingsBridge.hpp:106, SettingsBridge.cpp:1843, CameraPage.qml:518), and it reads the lists from UI.conf. No KB tool sends the command. Given up: nothing.

**After.**

```
        if (!updateSharedUiGeneralSettings(updates))
            return errorReply(command.id, "Could not save the value list.");
        return okReply(command.id, valueStepsJson(readSharedUiSettings(), camera_.sensorName()));
```

**Checked.** Here: the gate (above). --simulate (/home/user/build/sim/cp2/c16a): curl -X POST /api/command -d '{"cmd":"set_value_steps","name":"iso","free":"true"}' -> {"ok":true,"iso_steps":[...],"shutter_angle_steps":[...],...} flat; /api/state ui.iso_free true. Chromium (/home/user/build/sim/cp2/c16-page.js): sendValueSteps({name:'iso', free:'false'}) -> state.snapshot.ui.iso_free false, no error toast, no page errors. smoke-6.txt vs smoke-upstream.txt: every base field present with the same type. Camera: nothing.

**Rule.** A command reply is flat; before changing its shape, grep every client of the command (WebUI, touch UI, KB tools) and name what each reads.


---

## C37. core: --check-dual exits 0 only with a sensor on cam0 and on cam1

Apertar-Core `62460c6`. Finding: dual 1. Reviewed by the lead (no second worker this round).

**What was there.**

src/main.cpp:113-126@clip-split (merged into lane/dual 7444157): the secondary decides only for itself, after systemd has started it.
    if (!options.simulateCamera && !options.camera.empty() && options.camera != "cam0") {
        const auto node = apertar::cameraport::resolve({}, options.camera);
        if (!apertar::cameraport::secondaryHasSensor({}, options.camera,
                node.valid && apertar::cameraport::configNamesPort({}, node.port), 20000, 500, &why)) {
            std::cerr << why << "\n";
            return 0;
        }
    }

**Why it is a problem.** The check looked at cam1's port only. With cam0's sensor unplugged the primary takes cam1's sensor, the secondary's check still passes, it waits for the primary and starts a CameraManager, which writes HBLANK on the sensor the primary is running (design 3.4), before it exits on EBUSY. And systemd only learns there was nothing to do after the process ran. Original Apertar adds a launch option as a hand-written if (arg == "--x") in main with a usage line and a README row (CMD-23, src/main.cpp:52-82@upstream-1.6.0).

**How to spot it.** Ask of every second-instance feature: what does the instance do on a rig that has no second device, and who decides that, the instance after it started or the init system before? grep -n 'return 0' src/main.cpp for exits that hide 'nothing to do' inside a started service.

**Options.**

- A shell script with ls /sys/class/video4linux in ExecCondition: no build, but a second copy of the of_node scan in bash that drifts from CameraPort.hpp.
- A Core option that reuses CameraPort.hpp (chosen): about 40 lines in the header, 15 in main, one host test.
- ConditionPathExists= on a sysfs path: zero code, but subdev numbers are not stable and it cannot wait for a late probe.

**Chosen, and why.** The Core option: one scan for the session's camera pick, the subdev lookup, the relay and the unit. It checks both ports, so the cam0-unplugged case is skipped too. Given up: nothing for a stock camera; the option is a no-op unless run.

**After.**

```
    if (checkDual) {
        std::string why;
        const bool dual = apertar::cameraport::dualSensorsPresent({}, options.camera, 20000, 500, &why);
        std::cerr << why << "\n";
        return dual ? 0 : 1;
    }
```

**Checked.** Gate PASS. tools/camera_port_test.cpp (new; CameraPort.hpp:8 named it but it was missing): two sensors, cam0 only, cam1 only, none, no config.txt line (no wait), a late cam1 within the bound, a lens driver, no device tree, by port and by I2C node. Host binary: exit 1 in 5 ms. Pi: /home/pi/ApertarCore-build/apertar-core --camera cam1 --check-dual; echo $? with two sensors (0), cam1 unplugged (1, after 20 s when config.txt names cam1), cam0 unplugged (1).

**Rule.** A service that may have nothing to do is told so by its unit before it starts (ExecCondition), with the same code the program uses, not by an exit 0 after it started.


---

## C38. core: a second Core does not start without its own hardware file

Apertar-Core `5dc6b6b`. Finding: dual 2. Reviewed by the lead (no second worker this round).

**What was there.**

src/hardware/GpioInput.cpp:64-72@lane/dual 7444157 (the same list in 11 more readers, CameraController.cpp:3048 and :3094 among them):
    if (const char *envPath = std::getenv("APERTAR_HARDWARE_CONFIG"); envPath && *envPath)
        candidates.emplace_back(envPath);
    candidates.push_back(defaultHardwareConfigPath());   // /home/pi/apertar-hardware.conf
    candidates.emplace_back("/boot/firmware/apertar-hardware.conf");

**Why it is a problem.** A missing cam1 file made the secondary read the primary's wiring file: buffer=ram gave it a second RAM queue on a 4 GB Pi (design 2, RAM row), and [camera] keys meant for cam0. The fallback list is original Apertar's (HW-9, src/hardware/GpioInput.cpp:60@upstream-1.6.0) and right for one Core; a second Core is new ground. The role gate (App:8517-8566 at the tip) already skips the inputs, tally and trigger on a secondary.

**How to spot it.** For a second instance of a program, list every file it falls back to when its own is missing: grep -rn 'getenv("APERTAR_' src and look for a hard-coded /home/pi path after each.

**Options.**

- Drop /home/pi from all 12 candidate lists in secondary mode: 12 edits in accepted duplicated code (rule 6 of the conventions), easy to miss one.
- Build the cam1 template into Core and write it on demand (PLT-8): a second copy of config/apertar-hardware-cam1.conf to keep in sync, and a write into /home/pi.
- Refuse to start without the file, in main, before any reader runs (chosen): 13 lines, one place, and the install step copies the file.

**Chosen, and why.** Refuse in main: the readers never run, so no list needs to change, and a missing install step shows as a failed unit with a clear line instead of a camera running on the wrong settings. Exit 2 is main's existing code for a launch error; the unit (dual 3) sets RestartPreventExitStatus=2 so it does not loop. Given up: a secondary that works with no file at all.

**After.**

```
    if (apertar::cameraport::isSecondary(options.camera)) {
        const char *hardwareConfig = std::getenv("APERTAR_HARDWARE_CONFIG");
        std::error_code error;
        if (!hardwareConfig || !*hardwareConfig || !std::filesystem::is_regular_file(hardwareConfig, error)) {
            std::cerr << "ApertarCore camera " << options.camera << ": no hardware file of its own (" ...
            return 2;
        }
    }
```

**Checked.** Gate PASS. Simulate under /home/user/build/sim/dual/hw-*: missing file and unset variable both exit 2 with the line; with the cam1 template present it starts and its controls line names the file; a primary without the variable starts as before. Pi: move /home/pi/apertar-hardware-cam1.conf away, sudo systemctl start apertar-core-cam1, journalctl -u apertar-core-cam1 -b shows the line, systemctl show apertar-core-cam1 -p NRestarts reads 0.

**Rule.** A second instance of a program never falls back to the first instance's files; a missing file of its own is a launch error.


---

## C39. scripts: the cam1 unit starts with the primary, only with two sensors

Apertar-Core `76c3506`. Finding: dual 3. Reviewed by the lead (no second worker this round).

**What was there.**

config/apertar-core-cam1.service@lane/dual 7444157 (from clip-split bd6dd64):
    ExecStart=/home/pi/start-apertar-core-ds.sh
    Restart=on-failure
    RestartSec=5
    Environment=APERTAR_CORE_BIN=/home/pi/ApertarCore-ds-build/apertar-core
    [Install]
    WantedBy=apertar-core.service
(enabled with sudo systemctl enable --runtime apertar-core-cam1, HANDOFF.md SHARED-PI ADAPTATIONS)

**Why it is a problem.** The ds paths were the shared-Pi test setup, not a shipping unit: a fresh install has no ds files, so the unit fails at exec and Restart=on-failure retries every 5 s; a --runtime enable is gone at reboot. Original Apertar ships system files flat for the image or a hand install (PLT-6, Core/CMakeLists.txt:190-196@upstream-1.6.0) and the primary runs /home/pi/start-apertar-core.sh (architecture/build.md:94).

**How to spot it.** grep -n 'ExecStart\|Environment=.*BIN\|-ds' config/*.service: a unit that names a test binary or script, or a README that says enable --runtime, is still a bench setup.

**Options.**

- ExecCondition through the start script (forward "$@"): one binary path, but an old installed script would start a full primary-role Core as the condition.
- ExecCondition on the binary itself (chosen): the binary path is written twice (unit and script default), but an old binary only answers 'unknown option' (exit 2, skipped).
- ConditionPathExists on sysfs paths: no code, but subdev numbers move and a late probe is missed.

**Chosen, and why.** The binary in ExecCondition, the start script in ExecStart: a stale binary or script cannot turn the condition into a running camera. RestartPreventExitStatus=2 turns dual 2's launch error into one visible failure. Given up: the binary path is named in two places (unit and start-script default), noted in the unit's comment.

**After.**

```
    [Unit]
    Description=Apertar Core for the second sensor (cam1)
    After=apertar-core.service
    [Service]
    ExecCondition=/home/pi/ApertarCore-build/apertar-core --camera cam1 --check-dual
    ExecStart=/home/pi/start-apertar-core.sh
    RestartPreventExitStatus=2
    [Install]
    WantedBy=apertar-core.service
```

**Checked.** Gate PASS. systemd-analyze verify (systemd 255): only 'Command /home/pi/ApertarCore-build/apertar-core is not executable' and the same for /home/pi/start-apertar-core.sh (missing on this host); with both replaced by /bin/true it prints nothing. Start script with APERTAR_CAMERA=cam1 APERTAR_WEB_PORT=8001: '--socket ... --media /media/RAW --camera cam1 --web-port 8001'; without: today's line. Pi: the README install block once; reboot with two sensors: systemctl status apertar-core apertar-core-cam1 both active, the cam1 journal shows 'dual check: a sensor on cam0 and on cam1'; reboot with cam1's sensor unplugged: systemctl status apertar-core-cam1 shows 'ExecCondition ... status=1' / condition failed, systemctl show apertar-core-cam1 -p NRestarts is 0; reboot with cam0's unplugged: the primary takes cam1's sensor, cam1's unit skipped the same way.

**Rule.** A shipped unit names only the paths a normal install has, and an enable that must survive a reboot is a plain enable, not --runtime.


---

## C40. ipc: cam1 counts as configured only with a sensor on cam0 and on cam1

Apertar-Core `f09db0b`. Finding: dual 4. Reviewed by the lead (no second worker this round).

**What was there.**

src/ipc/ControlClient.cpp:333-334, 371@lane/dual 7444157 and src/ipc/Cam1State.hpp:27:
    const bool namesCam1 = options_.configNames && options_.configNames("cam1");
    const bool namesBoth = namesCam1 && options_.configNames("cam0");
    ...
    inputs.configNamesBoth = namesBoth;
    ...
    return in.switchOn && (in.configNamesBoth || in.socketAccepted || in.socketIsOurs);

**Why it is a problem.** config.txt says what the firmware should load, not what answered: with a sensor unplugged the line stays, and the relay published a cam1 that can never link. Every consumer (WebUI dualActive, the touch UI's cam1Present, ApertarControlBridge.cpp:1484, record_cameras, time left) keys on that object, so the camera looked dual with one sensor. Original Apertar has no second camera; its rule for optional hardware is that absence leaves the camera as it was (conventions principle 8, CMD-24).

**How to spot it.** Find every 'is it configured' test and ask what it reads: a file the operator edits (config.txt), or the device that answered (sysfs, a socket). grep -n 'configNames\|configured(' src/ipc.

**Options.**

- Keep configured, make each UI treat not_found and offline-with-one-sensor as single: touches the WebUI, the HDMI QML and Core's take paths separately.
- Configured reads sysfs, the same test as the unit's ExecCondition (chosen): five lines in Core, the UIs follow.
- Drop the not_found word entirely: a protocol change for nothing; it stays for a sensor lost after a link.

**Chosen, and why.** One test, dualSensorsPresent, answers both 'does cam1's Core run' (the unit) and 'is cam1 configured' (the relay), so they cannot disagree. Given up: the 'CAM1 NOT FOUND' state for a configured-but-unplugged sensor before any link; it now reads as one camera (the WebUI card keeps a note, dual 5).

**After.**

```
    options.dualSensors = [] { return cameraport::dualSensorsPresent({}, "cam1", 0, 0, nullptr); };
    ...
    const bool dualSensors = options_.dualSensors && options_.dualSensors();
    inputs.dualSensors = dualSensors;
    ...
    return in.switchOn && (in.dualSensors || in.socketAccepted || in.socketIsOurs);
```

**Checked.** Gate PASS (warning count per file as the baseline: RecordingClock.hpp and TakeSlots.hpp, pre-existing). Simulate: switch on, config naming both, no sensors: no cam1 in /api/state; a simulated secondary on /tmp/apertar-core-cam1.sock links and cam1 appears 'ready'. Smoke shapes vs 1.6.0: every base field present with the same type. Pi: switch on, cam1 sensor unplugged, curl -s localhost:8000/api/state | grep -c '"cam1"' is 0; with both sensors cam1 reads ready; journal has no 'cam1 linked' with one sensor.

**Rule.** Decide that a device is there from what answered (sysfs, a socket), not from the config line that asked for it.


---

## C41. web: the page shows two cameras only while Core reports cam1

Apertar-Core `9fd6435`. Finding: dual 5. Reviewed by the lead (no second worker this round).

**What was there.**

src/web/WebControlPage.cpp:15018-15026@lane/dual 7444157:
    function dualActive(snapshot) {
      if (!snapshot) return false;
      if (dualCam1(snapshot)) return true;
      if (!(snapshot.ui && snapshot.ui.dual_sensor_enabled === true)) return false;
      const ports = dualSensorPorts();
      return !ports || (ports.cam0 !== "none" && ports.cam1 !== "none");
    }

**Why it is a problem.** The page decided 'two cameras' from config.txt when Core said nothing, so it could disagree with Core and show a second pane for a sensor that is not there. Core is the one owner of camera state; the WebUI renders what /api/state says (WEB rules; one store, one owner, CMD-12).

**How to spot it.** A UI test with a fallback for 'the server did not say': grep the page for checks that read config files or settings next to a state field, and ask whether the field's absence already means something.

**Options.**

- Keep the fallback and add sensor presence to the page: a new state field, more API.
- Follow Core's cam1 object only (chosen): one line; at most one second of single layout right after the switch goes on, until the relay's next tick.
- Leave it: dual layouts with one sensor, the bug the owner reported.

**Chosen, and why.** Follow Core: the page and Core ship in one binary, so the pre-object fallback has no Core left to cover. Given up: the dual layout in the second between switching on and Core's first tick.

**After.**

```
    function dualActive(snapshot) {
      return !!dualCam1(snapshot);
    }
    ...
      const oneAnswered = !cam1 && switchedOn && configured;
        : oneAnswered ? "Boot Config names two sensors, but only one answered: one camera."
```

**Checked.** Gate PASS; node --check on the served script. Playwright (chromium, --simulate, /home/user/build/sim/dual/web-*): switch on + config naming both + no cam1: dual-wide false, cam1Badge hidden, the new note after loadBootConfig, 0 page errors; with a simulated cam1 Core linked on /tmp/apertar-core-cam1.sock: dual-wide true, badge shown. Pi: switch on, cam1's sensor unplugged, open :8000: one picture, no CAM1 badge, the card's note.

**Rule.** When the server owns a state, the page draws from the server's field, not from its own reading of the config that should produce it.


---

## C42. hw: the hardware-state note takes a safe writer name

Apertar-Core `7b24c82`. Finding: hardware-inputs commit 15. Reviewed by the lead (no second worker this round).

**What was there.**

src/hardware/HardwareConfigStore.cpp:406-414@cinemate-port
void HardwareConfigStore::writeStateLocked(const std::string &by)
{
    state_.writtenAt = timestamp("%Y-%m-%d %H:%M:%S", std::time(nullptr));
    state_.writtenBy = by;
    settingsFile::atomicWrite(notes_ / "hardware-state.conf",
                              "written_revision=" + state_.writtenRevision + "\n" + ...
                              "written_by=" + state_.writtenBy + "\n");

**Why it is a problem.** by comes straight from the command field (set_controls, set_buffer_mode and the other storage switches: command.string("by").value_or("api")). The note is a key=value file read line by line in the store's constructor, where a later line wins. by="x\nwritten_revision=h0" therefore planted a second written_revision line, and after the next start the store would treat a file it did not write as its own (settledLocked skips the being-written check for that revision). The history names in the same file already used safeName. Original Apertar never writes a raw client string into a key=value file: a UI.conf value is normalised first and refused if it differs (CMD-6, App:9802-9813@upstream-1.6.0).

**How to spot it.** For every file Core writes as key=value lines, grep where each value comes from: grep -n 'atomicWrite' src/hardware/*.cpp, then follow each value back to command.string(...). A client string concatenated between "key=" and "\n" without a filter is the smell. Also: one helper used for one sink (history names) but not its sibling sink (the note).

**Options.**

- Pass by through the existing safeName: one line, same filter as the history names (chosen)
- Refuse a by= with control characters in App: a new error sentence and a new refusal for a field that is only a label
- Escape newlines and read them back in the constructor: a new escaping format for a three-line note

**Chosen, and why.** safeName, because the same value already goes through it for the history file name, so the note and the history now say the same writer name. Given up: a by= with capitals or punctuation is shown lowercased with underscores in written_by (GET /api/config); no in-tree client sends such a name (webui, webui_undo, imu, api, core). The safeName comment now says why the note uses it.

**After.**

```
// The writer's name in a history entry and in the state note: [a-z0-9_] only, so a caller cannot put a path or a line in it.
std::string safeName(const std::string &by)
...
    state_.writtenBy = safeName(by);
```

**Checked.** Gate (check_core.sh /home/user/wt/lane-core3 lane-core3 both tests): PASS, PASS, PASS (18). The KB test working/tools/controls_store_test.cpp built against the tree and run with APERTAR_SCRIPT_PATHS=ssh: 52 of 52, including written_by=webui. --simulate on port 8181 with APERTAR_HARDWARE_CONFIG, XDG_CONFIG_HOME and HOME in /home/user/build/sim/hw2/c15: set_controls set.gpio_buttons.enabled=false with by="x\nwritten_revision=h0" wrote the file; hardware-state.conf holds one written_revision= line and written_by=x_written_revision_h0. Pi: nothing, no hardware path changes.

**Rule.** Every client string that goes into a line-based file goes through a filter first; use the one the same value already gets elsewhere.


---

## C43. hw: the store does not wait 100 ms under its lock

Apertar-Core `a583fa0`. Finding: hardware-inputs commit 16. Reviewed by the lead (no second worker this round).

**What was there.**

src/hardware/HardwareConfigStore.cpp:198-209@cinemate-port
    const int64_t age = now - stamp_.mtimeNs;
    if (age >= 0 && age < 1000000000)
        return false;
    const Stamp first = statFile();
    std::this_thread::sleep_for(std::chrono::milliseconds(100));
    return first == statFile();

**Why it is a problem.** settledLocked runs inside saveLocked under mutex_ (the std::lock_guard at the top of saveLocked). A sleep there makes the IMU, the storage switches and both pages queue for 100 ms on every save of a file Core did not write last. It adds little: a saving editor leaves the mtime under 1 s old, which the age check refuses; nano and vim, and the owner's longtakes.py (os.replace, longtakes.py:626-662), write in one go. Only a writer that pauses over a second between two writes gets past both. Original Apertar has no such check on its whole-file save (saveHardwareConfigFile, App:5323-5386@upstream-1.6.0), and its rule is no lock held across slow work it can avoid (CMD-19: std::lock_guard in the smallest scope).

**How to spot it.** grep -n 'sleep_for' and check whether a lock_guard is alive in the same scope; ask who else waits on that mutex. A sleep that makes a 'probably stable' guess under a lock is the smell.

**Options.**

- Delete the second stat and the sleep, keep the age check (chosen, -7/+3)
- Drop the mutex around the sleep and retake it: a second check-then-act window and a harder lock order to read
- Keep it: 100 ms per outside-edited save, IMU calibration writes queue behind it

**Chosen, and why.** Delete, as the plan and the audit say. The age check is what catches longtakes.py's os.replace write, so it stays. Given up: a hand writer that writes, waits more than 1 s and writes again into the same file can be edited between its two writes; the file lock (QtIniLock) and the stale-base check remain. <thread> had no other user and went with the sleep.

**After.**

```
// A file Core did not write must not be edited while an editor may still be saving it (nano rewrites in place):
// one changed in the last second is left alone. Never sleep here: every writer waits on mutex_.
bool HardwareConfigStore::settledLocked() const
{
    if (!stamp_.exists || revision_ == state_.writtenRevision)
        return true;
    ...
    return !(age >= 0 && age < 1000000000);
}
```

**Checked.** Gate: PASS, PASS, PASS (18). KB controls_store_test.cpp built against the tree (APERTAR_SCRIPT_PATHS=ssh): 52 of 52, including section 6 'a fresh hand edit is not merged into' and 'settled'. --simulate on port 8182, files in /home/user/build/sim/hw2/c16: the file replaced with Python os.replace (as longtakes.py does), then a set_controls key edit at once -> code being_written; 1.5 s later the same edit -> written, the outside line kept, curl time 12 ms. Pi: nothing.

**Rule.** Never sleep while holding a lock other writers need; refuse and let the caller retry.


---

## C44. hw: a button held at start is inverted only with invert_on_start

Apertar-Core `e60218a`. Finding: hardware-inputs commit 10 (variant). Reviewed by the lead (no second worker this round).

**What was there.**

src/hardware/GpioInput.cpp:620-631@cinemate-port
            if (!button.haveSample) {
                // Like Cinemate: a button that already reads pressed at start is wired the other way round ...
                button.inverted = level;
                if (level)
                    std::cerr << "GPIO input: GPIO " << button.gpio << " reads pressed at start; taken as inverted (a 1-0-1 button).\n";
            ...
            const bool pressed = level != button.inverted;
(src/hardware/Pcf8574Input.cpp:424-435@cinemate-port: the same with invertedMask)

**Why it is a problem.** A stock camera with a button held, or stuck, when Core starts got that button inverted for the session: it fired on release and a real press did nothing until a restart. Apertar 1.6.0 seeds observed and stable state from the first sample (GpioInput.cpp:693-697, Pcf8574Input.cpp:500-504@upstream-1.6.0), so a held button fires nothing, its release fires nothing, the next press fires; polarity is the operator's active_low (GpioInput.cpp:433-434@upstream-1.6.0, HW-12). The inversion itself is not an accident: Patrik decided it for his 1-0-1 buttons (DA-34 'like Cinemate (gpio_input.py check_initial_state)', DA-39 PCF pins too), so the campaign rule makes it a setting at the 1.6.0 value (C29 is the same move for script paths).

**How to spot it.** For each rule an input applies at start, ask what a stock camera does after the update with a button held at boot. grep -n 'haveSample' src/hardware/*Input.cpp and compare each first-sample block with upstream's: a first sample that changes how later samples are read (inverted, a mask) instead of only seeding state is the smell.

**Options.**

- Delete the inversion (the plan's commit 10): 1.6.0 behaviour, but reverses DA-34 and DA-39
- Per-pin dN_active_low / pinN_active_low (plan commit 12): new ground, ~40 lines, and not what Patrik asked for (he wants the Cinemate auto rule)
- Keep the inversion behind a section key invert_on_start, default false, like upstream's reset_on_start and emit_on_start (chosen, ~+40 lines with comments, README and template)
- An environment switch as in C29: wrong place, this is wiring (HW-10, the hardware file holds wiring) and nothing to protect from the browser

**Chosen, and why.** The section key, as the lead's item text and the audit say. A bool key read with the section's own parseConfigBool in a flat key == chain is the upstream shape (HW-11, R11 step 6; NeoRotary4Input.cpp:419 and GroveAnalogInput.cpp:309@upstream-1.6.0). False adds the NeoRotary rule to the two other inputs: a heldAtStart flag (GPIO, per RuntimeButton) or mask (PCF8574) is set from the first sample and cleared once the debounced state reads released; while set, the button is not fed to ButtonGesture. True runs the old code and line; a scratch run showed it behaves exactly as the parent commit. Given up: true still inverts GPIO encoder pushes too (they are RuntimeButtons, as before); the key is read only in the buttons branch, never in [gpio_encoders]. The 'ignored until released' journal line prints at each reopen, like the inversion line did. No Controls card row: text-only, as poll_ms and chip (DA-40).

**After.**

```
                if (config_.invertOnStart) {
                    button.inverted = level;  ... "taken as inverted (a 1-0-1 button)."
                } else if (level) {
                    std::cerr << ... "ignored until released. If it is a normally closed button, set invert_on_start=true in [gpio_buttons].\n";
                }
                button.heldAtStart = level != button.inverted;
                button.observedPressed = button.stablePressed = ...heldAtStart;
            ...
            button.heldAtStart = button.heldAtStart && button.stablePressed;
            if (button.heldAtStart)
                continue;
```

**Checked.** Gate: PASS, PASS, PASS (18). A scratch program (not committed, PLT-12) linked GpioInput.cpp and Pcf8574Input.cpp with an LD_PRELOAD shim that fakes /dev/fakegpio (GPIO v2 chardev, no edge events, so poll mode) and /dev/i2c-1, levels read from a file: held at start 1 s, released 1 s, pressed 1 s, released 1 s, d17/pin0=record_toggle. Key absent: one 'ignored until released' line; only the second press fires record_toggle. invert_on_start=true: 'taken as inverted', record_toggle on each release; the parent commit's sources give the same output with no key. --simulate port 8183: set_controls set.gpio_buttons.invert_on_start=true and set.pcf8574.invert_on_start=true are written; set.gpio_encoders.invert_on_start is refused ('not a key of [gpio_encoders]'); GET /api/config with no file shows both commented lines. KB controls_test.cpp (run with the tree argument): 120 of 121, the same single failure as before this commit (GPIO settings row, chip). Needs the camera: [gpio_buttons] enabled=true d17=record_toggle, hold d17, sudo systemctl restart apertar-core, release after 'GPIO input enabled': nothing records, the journal has the 'ignored until released' line; press: recording starts. Add invert_on_start=true with a normally closed button: journalctl -u apertar-core | grep 'taken as inverted' names it; one press records once. Same with a PCF8574 pin. On the owner's rig before deploying: journalctl -u apertar-core | grep 'taken as inverted'; any line means he adds invert_on_start=true to that section.

**Rule.** A start-time guess that changes how a button reads is a feature: off by default, named by a section key, and logged when it would have applied.


---

## C45. hw: the press that wakes the camera from Standby does nothing else

Apertar-Core `74f6bca`. Finding: hardware-inputs commit 11. Reviewed by the lead (no second worker this round).

**What was there.**

src/ApertarCoreApp.cpp:10304-10325@cinemate-port (handleHardwareInputAction, void)
    if (camera_.state() == CameraState::Standby) {
        if (!buttonPress)
            return;
        ControlCommand wake;
        wake.name = "wake";
        dispatchHardwareInputCommand(std::move(wake));
        return;
    }
src/hardware/GpioInput.cpp:565-570@cinemate-port: void emitAction(...) { ... actionCallback_(action); }

**Why it is a problem.** The input classes count gestures (Single, Double, Triple, Hold) in ButtonGesture from the press on. App woke the camera on that press, but emitAction was void, so the input could not know and kept counting: d17_hold=standby slept the camera again 3 s after waking it, d17_double=photo took a photo. HW-5: 'In Standby a press only wakes and is consumed'. Upstream's shape for exactly this: the power button's callback returns bool and on true calls gesture.consume() (StandbyPowerButtonInput.hpp:8, StandbyPowerButtonInput.cpp:66-71, PowerButtonGesture.hpp:31-32@upstream-1.6.0); upstream GPIO buttons fire on press only, so a wake press had no follow-up (GpioInput.cpp:703-708@upstream-1.6.0).

**How to spot it.** Where a callback decides something the caller must act on (here: 'this press was used up'), a void callback is the smell. Grep the gesture or debounce state an input keeps (grep -n 'gesture' src/hardware/*Input.cpp) and ask: when App ignores or swallows an event, does the input learn of it?

**Options.**

- Bool callback + ButtonGesture::consume(), as upstream's power button (chosen, about +32/-12 over 9 files)
- App remembers 'woke at time T' and ignores actions for N ms: a timer guess, and a Hold 3 s later passes it
- Inputs read camera state themselves: breaks HW-6 (no app knowledge in src/hardware)

**Chosen, and why.** The upstream power-button shape. std::function<bool(const std::string &)> (a callable that returns bool) is the new PressCallback; rotation and Listen callbacks keep ActionCallback (void). The rotation fallback ActionCallback(actionCallback_) wraps the bool callback in a void one, since the ?: operator needs both sides of one type. consume() zeroes the click count and, while the button is down, marks it as a long press whose Hold already fired. Given up: the second press of a double click after a wake is a new press and fires its Press action (as in 1.6.0); switches still wake the camera and ignore the answer (owner question 7).

**After.**

```
    void consume()
    {
        clicks_ = 0;
        if (down_) { longPress_ = true; holdFired_ = true; }
    }
...
                case hardware::ButtonGesture::Event::Press: woke = emitAction(button.action); break;
                ...
                if (woke)
                    button.gesture.consume();   // A wake press does nothing else.
(App) dispatchHardwareInputCommand(std::move(wake));
        return true;
```

**Checked.** Gate: PASS, PASS, PASS (18). Scratch ButtonGesture program (not committed, PLT-12): press, consume, release at 200 ms -> Single 0; press, consume, held 3.1 s -> Hold 0, nextWakeMs -1; next press -> Press 1; without consume -> Single 1. Scratch driver with an LD_PRELOAD fake of /dev/fakegpio and /dev/i2c-1, callback 'asleep until the first press': parent commit: hold 3.5 s -> wake, standby; double click -> wake, record_toggle, photo (GPIO and PCF8574). This commit: hold -> wake only; double click -> wake, record_toggle. --simulate port 8184: enter_standby, test_input gpio_buttons d17 -> ok reply as before, state ready (woke only); again -> recording. smoke_core.sh + shape_subset.py against smoke-upstream.txt: every base field present with the same type. NeoRotary reviewed by reading (same lines). Needs the camera: d17=record_toggle, d17_hold=standby, d17_double=photo; enter Standby, hold d17 3 s: journalctl -u apertar-core -f shows one wake, no enter_standby; enter Standby, double-click d17: wakes, no new photo (a take from the second press is expected, stop it). Same on a NeoRotary push and a PCF8574 pin.

**Rule.** When an input's event is used up by the app, the callback says so and the input forgets the press.


---

## C46. core: the default hardware file template leaves the write-buffer and Clear HDR keys as comments

Apertar-Core `2b8518d`. Finding: hardware-inputs commit 6. Reviewed by the lead (no second worker this round).

**What was there.**

src/ApertarCoreApp.cpp:5054-5057, 5078-5079@cinemate-port (defaultHardwareConfigTemplate)
[storage]
buffer=frames
buffer_ram_fraction=0.6
buffer_ram_floor_mb=512
buffer_ram_max_fraction=0.5
[camera]
clear_hdr_iso_max_12bit=720
clear_hdr_iso_max_16bit=1585

**Why it is a problem.** A live key in a template is a setting written into every camera that gets the template as its file. These six are port keys: a stock 1.6.0 camera has no such setting, and a key written into its file stays there even if a later Core changes its default. Upstream templates hold upstream sections and keys only and ship accessories disabled (HW-7, HW-20; App:4291-4404@upstream-1.6.0). The port's own [media] lines in the same template already show the right form: a commented default.

**How to spot it.** Diff the template's live keys against upstream's template: every key that is not in App:4291-4404@upstream-1.6.0 or the 1.6.0 touch UI writer is a port setting. Ask for each: does the reader default to the same value? If yes, the line only pins it.

**Options.**

- Comment the six lines with their values (chosen, -6/+6)
- Delete them: the operator loses the hint that the keys exist
- Keep them live: a first-file write pins port settings on stock cameras

**Chosen, and why.** Comments: nothing changes for any camera (CameraController.cpp:2945-2946 max12=720 max16=1585; BufferBudget.hpp:33-35 fraction 0.6, floor 512 MB, max fraction 0.5; buffer unset means frames), the operator still sees the keys, and the owner's longtakes.py edit_storage_keys replaces a commented copy of a key (longtakes.py:647 matches ^[#;]?\s*key=), so his campaign tool works on the new template. Given up: nothing; storage-settings and camera-modes may still move or delete the keys (they need only keep them commented).

**After.**

```
# buffer=frames
# buffer_ram_fraction=0.6
# buffer_ram_floor_mb=512
# buffer_ram_max_fraction=0.5
...
# clear_hdr_iso_max_12bit=720
# clear_hdr_iso_max_16bit=1585
```

**Checked.** Gate: PASS, PASS, PASS (18). --simulate with no hardware file (/home/user/build/sim/hw2/state-run.sh, port 8186), run with the binary before and after this commit: GET /api/config text has no live buffer= or clear_hdr_iso_max line and holds the six commented lines; the 24 storage/buffer/Clear HDR fields of /api/state are equal in both runs. KB controls_test.cpp section 13 (template): no errors, parses back byte for byte (overall 120 of 121, the same pre-existing GPIO-row failure). Pi: nothing.

**Rule.** A template's live keys become settings on every camera that gets it: a key the original does not have stays a comment.


---

## C47. core: the default hardware file template holds the 1.6.0 touch UI's input and network sections

Apertar-Core `1ec624c`. Finding: hardware-inputs commit 7. Reviewed by the lead (no second worker this round).

**What was there.**

src/ApertarCoreApp.cpp defaultHardwareConfigTemplate@cinemate-port (no [network]):
[pcf8574]
enabled=false
bus=1
address=0x20
...
[gpio]
enabled=false
[gpio_encoders]
enabled=false

**Why it is a problem.** In 1.6.0 Core only showed its template; the touch UI wrote the real first file at start when it was missing (UI src/DisplayConfigBridge.cpp:41-326, call :587@upstream-1.6.0), with [network], input tuning, NeoRotary and Grove mappings, [gpio_buttons] chip=auto. The port deleted that writer (UI c9d841f), so the lead decided Core writes the first file (owner question 3, DA-3). For a stock camera to get what 1.6.0 gave it, Core's template must hold those sections and values. HW-7: three hand-kept templates; the shown one now carries the UI writer's content.

**How to spot it.** Extract both templates as text and compare key=value per section (a 30-line Python script: the UI's QTextStream << lines unescaped, Core's R"CONFIG( string). Every key the old writer wrote and the new one does not is a fresh-camera difference to explain.

**Options.**

- Copy the 1.6.0 file's sections and values, with the plan's three exceptions (chosen, +58/-3)
- Copy the file literally, d5/d6 and the [gpio_encoders] shared keys live: 1.6.0's text, but its poll_ms=3/debounce_ms=40 override the buttons' lines (later line wins, GpioInput.cpp:342-355) and the Controls page edits lines that then have no effect; GPIO 5/6 claimed by both examples
- Restore the UI writer (owner option 3b): about +590 UI lines and the moved-file hazard c9d841f removed

**Chosen, and why.** The plan's text. The examples are commented, not dropped, so the operator still sees the 1.6.0 mappings. Given up, and the lead should know: a fresh camera whose operator enables [gpio_buttons] gets debounce 60 ms and poll 12 ms, where the 1.6.0 file's [gpio_encoders] lines made it 40 ms and 3 ms, and d5/d6 are not mapped until uncommented. With the sections off (as shipped) nothing differs. A scratch run showed the checker would report 0 issues on the literal variant too, so the choice rests on the reader's later-line rule, not on the checker. Core's own comments were kept where both templates explain the same thing; three 1.6.0 comment lines were added (Grove digital BCM numbers, Grove encoder wiring, Grove ADC address).

**After.**

```
[network]
hotspot_delay_seconds=60
...
[gpio_buttons]
enabled=false
# chip=auto is the Pi's 40-pin header; another chip by path, for example /dev/gpiochip13.
chip=auto
active_low=true
pull=up
poll_ms=12
debounce_ms=60
[gpio_encoders]
# chip, active_low, pull, poll_ms and debounce_ms are shared with [gpio_buttons]: set them there.
```

**Checked.** Gate: PASS, PASS, PASS (18). Scratch program over the template text taken from the source: hwconf::validate 0 issues with empty facts, 0 with buses 0 1 4 10 13 14 known; hwconf::join(parse(t)) == t. Key-by-key comparison against the 1.6.0 UI writer: remaining differences are pin0..7=none, the commented GPIO examples and shared encoder keys, the IMU sections (next commit) and [display] (touch-ui). --simulate port 8186 with no file: GET /api/config text has every section, errors 0, warnings 0; the model's GPIO chip row is value auto. KB controls_test.cpp section 13: all checks ok (with facts buses 0 1 10 13 14 only the expected 'bus 4 does not exist' warning). Pi: none until the file is written (item 8).

**Rule.** When one writer replaces another, compare their output key by key and write down every difference you keep.


---

## C48. core: the default hardware file template holds the IMU sections

Apertar-Core `7ae9677`. Finding: hardware-inputs commit 8. Reviewed by the lead (no second worker this round).

**What was there.**

src/ApertarCoreApp.cpp defaultHardwareConfigTemplate@cinemate-port
[imu]
enabled=false
driver=mpu6050
sync_mode=free_run
sync_offset_ms=0
(no [mpu6050], [bmi160], [bmi270], [icm42688p])

**Why it is a problem.** A fresh 1.6.0 camera's file came from the touch UI and had the IMU on, with every device section (UI src/DisplayConfigBridge.cpp:199-298@upstream-1.6.0). Upstream Core's own template had [imu] enabled=false (HW-20 notes the IMU default differs per template), but Core only showed it. Now Core's template is what gets written, so it must hold what the camera got. Owner question 4 was answered by the lead from DA-7/DA-8: on, as 1.6.0's file.

**How to spot it.** Same key-by-key comparison as the previous commit; a section the old writer had and the new one lacks shows as 'section missing'.

**Options.**

- IMU on, the 1.6.0 file's text (chosen, +98/-1)
- IMU off as upstream Core's template and HW-20: differs from what a 1.6.0 camera got

**Chosen, and why.** On, text cut from the 1.6.0 writer's output by a script, so no value was retyped. Effect with no IMU fitted, as in 1.6.0: each WebUI state build tries a read on bus 1 at 0x68 and shows 'Waiting for MPU-6050'; a .gcsv is written only when Record Gyro Data is on. Given up: nothing new; with no file the IMU reader already defaults to enabled, bus 1, 0x68 (seen in --simulate before and after).

**After.**

```
[imu]
# Current options: driver=mpu6050, bmi160, bmi270, icm42688p.
# Free-running IMUs use sync_offset_ms to bake in a measured Gyroflow sync correction.
enabled=true
...
[mpu6050]
enabled=true
bus=1
address=0x68
sample_rate_hz=500
...
```

**Checked.** Gate: PASS, PASS, PASS (18). Scratch hwconf::validate over the template: 0 issues (empty facts; buses 0 1 4 10 13 14); parses back byte for byte. Key-by-key comparison with the 1.6.0 UI writer: only the commented GPIO examples, the shared encoder keys, pin0..7=none and [display] differ. --simulate port 8186 with no file: GET /api/config errors 0, warnings 0; /api/state imu.enabled true, bus 1, address 104 (the same with no file before this commit; the written file is checked in the next commit). Pi: none until the file is written.

**Rule.** Copy a template from the old writer's output by a script, not by hand.


---

## C49. core: Core writes the default hardware file when no copy exists

Apertar-Core `5622a68`. Finding: hardware-inputs commit 9. Reviewed by the lead (no second worker this round).

**What was there.** Nobody wrote a first file in the port: UI commit c9d841f deleted ensureDefaultHardwareConfigFile (UI src/DisplayConfigBridge.cpp:41-326, call :587@upstream-1.6.0) and the copy in Ina219Bridge.cpp:69-342. Core only showed its template (src/ApertarCoreApp.cpp buildHardwareConfigFileJson@cinemate-port: text = defaultHardwareConfigTemplate() when no file and no /boot copy).

**Why it is a problem.** A fresh port camera had no hardware file: every reader ran on compiled defaults, the touch UI logged 'INA219 config: using defaults in /home/pi/apertar-hardware.conf' (UI src/Ina219Bridge.cpp:263-267), and the Config page said 'Not saved yet'. A stock 1.6.0 camera had the UI's file after its first start. Decision DA-3: Core owns ~/apertar-hardware.conf; the lead's answer to owner question 3: Core writes the first file. Upstream precedent for Core writing its own file at start, in --simulate too: camera_settings.conf (CameraController.cpp:7640-7646@upstream-1.6.0). HW-9: write only the editable path.

**How to spot it.** When a writer is deleted, ask what a fresh install now starts with: run Core with an empty HOME and APERTAR_HARDWARE_CONFIG in a scratch folder and look for the file. For any new start-up write, list the cases where it must not write (file moved away on purpose, /boot copy, unwritable folder, second instance) and run each.

**Options.**

- Core writes through the store at start, gated on no file at any candidate path and no record of one (chosen, +24/-1 and a README line)
- Restore the UI writers (owner option 3b): ~590 UI lines back and the moved-file hazard c9d841f removed
- Write whenever the editable path is missing: replaces a file the operator moved away and hides a /boot copy from the readers

**Chosen, and why.** The gated write in App start(), before the first refreshBufferRequest and before any reader. The 'no record' test reads the store's notes (hardware-last-written.conf, hardware-history/adopted-*.conf) through HardwareConfigStore::defaultNotesDirectory(), so XDG_CONFIG_HOME picks the notes of this instance (DA-84). A path is any of hardwareConfigCandidatePaths(), so a /boot copy counts, and a second instance whose own file is missing still falls back to the primary's file as the dual-sensor design expects (it is not given the template). replace() with the absent revision writes via the store (lock, .tmp + rename, history, last-written, state note by=core). adopted = !wroteDefault && store.adopt(), so the pinned 'before Controls' version stays a file the operator had. Given up: when the folder cannot be written the log line carries the store's lock sentence ('Another program is writing the file; try again.'), which names the wrong cause; the start goes on. Also: with the file written, the template's live NeoRotary and Grove mappings show as Controls rows (smoke model rows 0 -> 4), as the plan's risk note says.

**After.**

```
    bool wroteDefault = false;
    {
        ...
        bool known = std::filesystem::exists(notes / "hardware-last-written.conf", error);
        for (const auto &path : hardwareConfigCandidatePaths())
            known = known || std::filesystem::is_regular_file(path, error);
        ... adopted-*.conf ...
        if (!known) {
            const hardware::StoreResult result =
                store.replace(std::string(hwconf::kAbsentRevision), defaultHardwareConfigTemplate(), "core");
```

**Checked.** Gate: PASS, PASS, PASS (18). --simulate on port 8188 with /home/user/build/sim/hw2/c9-run.sh, APERTAR_HARDWARE_CONFIG, XDG_CONFIG_HOME and HOME in a fresh folder per case. A, nothing anywhere: 'ApertarCore controls: wrote the default ~/hw.conf'; the file equals the template, mode 644; hardware-last-written.conf equals it; no hardware-history (no adopted-*.conf); state note written_by=core; GET /api/config exists:true, 0 errors, 0 warnings, replaced false; /api/state imu enabled, bus 1, address 104. B, file moved away, same notes, restart: no write; 'the file was replaced. The file is missing or empty. The version last saved at 09:57 can be restored'. C, only hardware-history/adopted-h....conf: no write. D, existing file: byte-identical, adopted as before. E, the file's folder cannot be created (its parent is a regular file): one 'could not write the default' line, Core starts and answers. F, only /boot/firmware/apertar-hardware.conf (unshare -m, tmpfs on /boot): no write. /home/pi stayed empty throughout. smoke_core.sh + shape_subset.py: every base field present with the same type. Needs the camera: back up (mv ~/apertar-hardware.conf ~/hw.keep; mv ~/.config/apertar-core ~/core.keep), sudo systemctl stop apertar-ui; sudo systemctl restart apertar-core; sleep 5; ls -l ~/apertar-hardware.conf ~/.config/apertar-core/hardware-last-written.conf; journalctl -u apertar-core -b | grep 'wrote the default'; sudo systemctl start apertar-ui; journalctl -u apertar-ui -b | grep 'INA219 config' should show 'INA219 config: /home/pi/apertar-hardware.conf (enabled=true, bus=4, address=0x40)'. Put both back and restart both units.

**Rule.** A start-up write that creates an operator file runs only when no copy exists anywhere and no record says one existed.

