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

