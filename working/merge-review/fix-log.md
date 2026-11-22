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


---

## C50. camera: the IMX585 tables also list the original driver's 1.85:1 sizes

Apertar-Core `b485059`. Finding: camera-modes commit 1. Reviewed by a second agent: not reviewed.

**What was there.**

src/camera/Imx585Modes.hpp:3@cinemate-port says "The IMX585 modes the cinemate-port driver advertises". The tables held only 3840x2072 / 1920x1036, and imx585_modes_test.cpp asserted CHECK(!im::anyClassHas(3840, 2076)); // the retired 1.6.0 size. The probe, CameraController.cpp:7152-7158@cinemate-port:
    const auto model = camera->properties().get(libcamera::properties::Model);
    std::string modelName = model ? std::string(*model) : std::string();
    std::transform(modelName.begin(), modelName.end(), modelName.begin(), ...tolower...);
    const bool tableProbe = modelName.find("imx585") != std::string::npos;
For an IMX585 the probe configures only table rows. A size the driver advertises but the table lacks is never tried and never logged.

**Why it is a problem.** The original Apertar driver (imx585.c:586-591, :817, :1007@e5b74d3) has 1.85:1 at 3840x2076 and binned 1920x1038. Because the probe tries only table rows, a stock camera never lists those modes, so one Core cannot serve both drivers. Upstream 1.6.0 lists those sizes itself (isImx585LowResolutionAlias and the crop predicates, CameraController.cpp:360-396@upstream-1.6.0). R6: the driver must offer the mode, and Core lists the size. CAM-11: sensors are told apart by SensorFamily from detectSensorFamily(camera->id()) (CameraController.cpp:5375@upstream-1.6.0), not by a second string match in the same file. CAM-23: a fallback or a dropped driver mode at start gets a log line. CAM-4: the pure tables stay header-only with a host test.

**How to spot it.** grep -n 'properties::Model' src/camera/CameraController.cpp: any use other than picking the default tuning is a second way to identify the sensor. To check that Core and the driver agree, compare the 'height =' values in git show origin/apertar:imx585.c and in the cinemate-port imx585.c against the rows in src/camera/Imx585Modes.hpp. Ask: does a driver mode that Core does not know leave a line in the journal?

**Options.**

- Add the two original sizes to the tables (S12, S10, and H12 for the future driver) and let the probe sort them out: about 5 extra configures at start (cost: probe time), no other code change
- Probe every size the driver advertises (formats.sizes()) instead of table rows: more general, but it loses the table's binning and its H16 optical-black rule (cost: bigger rework of a deliberate design, caa0153)
- Generate the tables from imx585.c with a host tool: catches drift automatically (cost: new tooling, no upstream precedent)

**Chosen, and why.** Option 1, as the page asks. I added the rows at the end of each table with a short trailing comment, so I did not have to re-flow the existing rows and the diff stays small. One side effect: on the original driver the 2076/1038 modes come last in the probe order. CC-3-F11 and Driver-imx585-F8 came along: tableProbe now uses detectSensorFamily, and there is one journal line per advertised size that no row of the class covers. I gave up a nearest() tie test (2072 vs 2076), because it would pin down an order nobody relies on. I left the old header line 3 for commit 13, as the page assigns, but the new paragraph under it states that the tables hold both drivers' sizes.

**After.**

```
    { 1024, 408, true }, { 1024, 400, true },
    { 3840, 2076, false }, { 1920, 1038, true },     // 1.85:1 of the original Apertar driver
};
...
const bool tableProbe = detectSensorFamily(camera->id()) == SensorFamily::Imx585;
...
for (const auto &advertised : formats.sizes(pixelFormat)) {
    bool covered = false;
    for (const auto &row : apertar::imx585::all(cls))
        covered = covered || apertar::imx585::transportFor(cls, row) == apertar::imx585::Size{ advertised.width, advertised.height };
```

**Checked.** Run here: /home/user/build/bin/check_core.sh /home/user/wt/lane-core4 lane-core4 both tests. Both builds pass; CameraController.cpp recompiled in the lc build with 0 warnings, and the 3 nolc warnings are older and outside my lines. imx585_modes_test prints ok. I did not start --simulate, because the probe runs only with libcamera and a camera, and no socket command or state field changed. Needs the camera: journalctl -u apertar-core -b | grep -E 'sensor mode:|sensor probe:'. With the cinemate-port driver (cd548ef) you should see the same 'sensor mode:' lines as before, with no 2076/1038 among them, and 'sensor probe: N modes in M ms' a few configures slower. You should also see one line, 'ApertarCore sensor probe: <12-bit format> 1920x1080 clear_hdr is a driver mode with no IMX585 table row', for the binned row Core holds back in H12. With the original driver (e5b74d3, installed with its setup.sh, then reboot) you should see 'sensor mode:' lines for 3840x2076 and 1920x1038 in 12-bit and 10-bit (sdr), and no 'no IMX585 table row' lines; its 16-bit 3840x2200 is covered by the H16 4K row. Binned 1038 rows may still be refused later, at configure time, by the readout check; commit 4 fixes that.

**Rule.** When Core keeps a copy of a driver's mode table, make it hold the union of the drivers it must run with, and let the run-time probe decide. Never assume the table matches the installed driver.


---

## C51. camera: a 1.85:1 size follows the height the driver has

Apertar-Core `aef5217`. Finding: camera-modes commit 2. Reviewed by a second agent: not reviewed.

**What was there.**

src/camera/CameraController.cpp:446@cinemate-port (lane tip f1c14d4):
Resolution migratedImx585CropResolution(Resolution resolution)
{
    if (resolutionMatches(resolution, 3840, 2076))
        return Resolution{ 3840, 2072 };
    if (resolutionMatches(resolution, 1920, 1038))
        return Resolution{ 1920, 1036 };
    return resolution;
}
It was called in clampCaptureSettings (every load and persist), in setResolution, in applyCapturePreset, and through migrateImx585LadderRungs in the constructor and in setModeLadder.

**Why it is a problem.** The rewrite fits only one driver. The original Apertar imx585 driver (e5b74d3) has 3840x2076 / 1920x1038, so on a stock camera Core asked for sizes the driver does not have. It also changed every saved file the moment the file was loaded. Original Apertar maps a client's size to the sensor's own size in the per-sensor normaliser, when the size is used, and never rewrites the saved value on load (isImx585LowResolutionAlias CC:360-364 and normalizedResolutionForSensor CC:2372-2421@upstream-1.6.0). 1.6.0's validator accepts 2076/1038 for every sensor (CC:366-396@upstream-1.6.0).

**How to spot it.** grep -n 'migrat\|Resolution{ 3840, 20' src/camera/*.cpp. Look for a helper applied in clampCaptureSettings or in a loader that changes a stored size for every sensor. Ask: "would the other driver or the other sensor still get the value it saved?"

**Options.**

- Keep the rewrite and flip the direction for the original driver: still rewrites files on load, and still has one hard-coded answer
- Map at use from what the startup probe found (pure function in Imx585Modes.hpp, called from the IMX585 normaliser step): one small host-tested function and a lookup of the probed sizes on every sanitise
- Advertise both heights and accept either without mapping: the port driver then refuses 2076 at configure, so saved sizes break

**Chosen, and why.** Option 2, as the design page says. driverCropSize(cls, requested, probed) returns the height of the pair whose transport size is in the probe's list for that class. With nothing probed, it returns the request if the class has it, otherwise the partner (so H16 3840x2076 becomes 2072). The CC helper probedImx585Sizes reads the probed list under probedSensorModesMutex. That mutex is already taken under mutex_ by probedMaximumFps, so the lock order does not change. Given up: a saved file is not corrected until the next save writes the effective value, the same as every other sanitised field. Two points where the code differed from the plan: (1) applyCapturePreset keeps its presetResolution variable, now set to requested.resolution, to keep the diff small. (2) The rung step in start() runs after the session/simulate if-else, so in --simulate it also runs, does nothing because no probe ran, and leaves the rungs as they are.

**After.**

```
inline Size driverCropSize(Class cls, Size requested, const std::vector<Size> &probed)
    ... partner = the other height of the pair, else return requested;
    for (const Size candidate : { requested, partner }) {
        const auto transport = transportFor(cls, candidate.width, candidate.height, 0);
        for (const Size &size : probed) if (transport && *transport == size) return candidate;
    }
    if (find(cls, requested...) || !find(cls, partner...)) return requested;
    return partner;
// CC: const Resolution wanted = driverCropResolution(cls, imx585AliasResolution(requested));
```

**Checked.** Run here: /home/user/build/bin/check_core.sh /home/user/wt/lane-core4 lane-core4 both tests gave PASS on both builds and 18 host tests. imx585_modes_test has new driverCropSize cases: port set gives 2072/1036, original set gives 2076/1038, empty list gives the request, H16 2076 gives 2072, H12 1920x1036/1038 come back as sent, and non-1.85:1 sizes come back unchanged. The 3 nolc warnings are in CameraController.cpp lines this commit does not touch (unused mediumGone, basePathOverride, allocatePhotoBasePath). In --simulate (sensor Unknown): set_resolution 3840x2076 gives get_state 3840x2076, and camera_settings.conf keeps resolution_height=2076 after a restart. 3840x2072 and 1920x1038 round-trip. Headless Chromium: the page loads with no script errors, and imx585NormalizedResolution keeps 3840x2076 and 1920x1038. Needs the Pi, port driver (cd548ef): start with resolution_height=2076 in camera_settings.conf, then `journalctl -u apertar-core -b | grep 'camera configured'` should show 3840x2072. A ladder with a 3840x2076 rung should show the rung as 3840x2072 and valid in `get_mode_ladder`, both before and after a restart. Needs the Pi, original driver (e5b74d3, after commit 4 so binned/explicit modes pass the readout check): `set_resolution 3840x2076`, then the `camera configured:` line should show raw 3840x2076. The journal `sensor mode:` lines list the 2076/1038 rows that driverCropSize then picks.

**Rule.** Map a size the sensor names differently when it is used (in the per-sensor normaliser), from what the driver really has. Never rewrite the saved value on load.


---

## C52. web: a 1.85:1 pill sends the size it shows

Apertar-Core `b3f4044`. Finding: camera-modes commit 3. Reviewed by a second agent: not reviewed.

**What was there.**

src/web/WebControlPage.cpp:9389,9405@cinemate-port (lane tip ef17857): two labels went to one size:
      if (label === "1920x1036" || label === "1920x1038")
        return { cmd: "set_resolution", width: 1920, height: 1036 };
      if (label === "3840x2072" || label === "3840x2076")
        return { cmd: "set_resolution", width: 3840, height: 2072 };
WCP:8916-8918, the fallback strings s12/s10/h12, listed only the port driver's "3840x2072" and "1920x1036b".

**Why it is a problem.** The page rewrote a 1.85:1 size to the cinemate-port driver's height. On the original imx585 driver (3840x2076 / 1920x1038, imx585.c:591,817@e5b74d3), a 1.85:1 pill therefore asked for a size that driver does not have. Original Apertar sends each pill's own label (resolutionCommandPayload, src/web/WebControlPage.cpp:5467-5468, 5483-5484@upstream-1.6.0). Any mapping to the sensor's own size happens in Core's per-sensor normaliser, at use (normalizedResolutionForSensor, CameraController.cpp:2372-2421@upstream-1.6.0). After commit 2, Core does that mapping with driverCropSize, so the duplicate mapping in the page was wrong on the stock driver and not needed on the port driver.

**How to spot it.** grep -n 'label === "[0-9]*x[0-9]*" ||' src/web/WebControlPage.cpp: a branch that matches two labels but returns one size is a mapping hidden in the page. Ask: does Core already normalise this size? If it does, the page should send the label as it is.

**Options.**

- Each label returns its own size, and the fallback lists take the original sizes (the plan, 1.6.0 shape): -5/+9 lines. On the port driver, no 1.85:1 pill is lit until the probed ladder pool arrives (one round trip). A click in that window still lands on 2072, because Core maps it.
- Drop the 1.85:1 branches and let the generic WxH regex at the end of resolutionCommandPayload handle them: fewer lines, but the function stops matching 1.6.0 line for line.
- Keep the page mapping and make it probe-aware: a second copy of Core's driverCropSize in JS, which is the duplication commit 2 removed.

**Chosen, and why.** Option 1, as the design page says. Each label gets its own if-branch in the 1.6.0 style. I kept the 2072 and 1036 branches, so the port driver's own labels still send their own sizes. Only the 3840 row of the h12 fallback changed; the h16 string is untouched. Given up: before the pool arrives, the port driver's fallback list shows 2076 while Core reports 2072, so no 1.85:1 pill is lit for one round trip. That trade-off is already in the design's Risks. The JS fps fallback table (WCP:7459-7462) still names 2072/1036, but it returns 60 for any size anyway, and it is not part of this item.

**After.**

```
      if (label === "1920x1036")
        return { cmd: "set_resolution", width: 1920, height: 1036 };
      if (label === "1920x1038")
        return { cmd: "set_resolution", width: 1920, height: 1038 };
      ...
      if (label === "3840x2072")
        return { cmd: "set_resolution", width: 3840, height: 2072 };
      if (label === "3840x2076")
        return { cmd: "set_resolution", width: 3840, height: 2076 };
```

**Checked.** Run here: the gate (both builds, 0 warnings, 18 host tests). Also apertar-core --simulate on port 8147 with headless Chromium (Playwright), driving the page's own functions. resolutionCommandPayload gives height 1038 / 1036 / 2076 / 2072 for the four labels. Sending the 1920x1038 and 3840x2076 payloads, get_state then reads 1920x1038 and 3840x2076 (the sim sensor is Unknown, so Core keeps them). With a fake IMX585 snapshot and no ladder pool, imx585ResolutionForBaseAndRatio returns these 1.85:1 sizes: Full HD binned 1920x1038 and 4K 3840x2076 in SDR 12 and 10, 3840x2076 in Clear HDR 12, 3840x2072 in Clear HDR 16. There were no page errors. The real IMX585 pill path does not run in --simulate (imx585Selected), so the click itself needs the camera. Port driver: click 1.85:1 under Full HD binned and under 4K. Then curl -s -X POST http://<pi>:8000/api/command -d '{"cmd":"get_state"}' should read 1920x1036 and 3840x2072, and journalctl -u apertar-core -b | grep 'camera configured' should show raw 1920x1036 / 3840x2072. Original driver (installed with setup.sh at e5b74d3, after commit 4 of the plan): the same clicks give 1920x1038 and 3840x2076 in get_state and on the 'camera configured' line.

**Rule.** A client sends the size it shows; only Core maps a size to what the sensor or driver has, once, at use.


---

## C53. camera: the IMX585 readout check accepts the original driver and checks the auto config like the IMX477

Apertar-Core `579ede9`. Finding: camera-modes commit 4. Reviewed by a second agent: accept.

**What was there.** src/camera/CameraController.cpp:8500@cinemate-port: the colour IMX585 exact-mode block ran on `if (sensorFamily_ == SensorFamily::Imx585 && !monochromeSensor_)` with no check for explicit or auto. Its crop check was `if (adjusted.empty() && imx585Row && cropMaximum)`, which compared the crop with active size x binning. The original driver's binned crop of 1920x1080 at 0,0 failed that comparison.

**Why it is a problem.** The original driver (imx585.c:803-808 and :2379-2381@e5b74d3) reports a binned mode's crop as the output size. libcamera sets ScalerCropMaximum from analogCrop on every configure (pipeline_base.cpp:568), so binned modes are refused. This is confirmed in code, not run on a Pi. 1.6.0 checks auto configs with the IMX477/577 size rule (CameraController.cpp:6166-6168@upstream-1.6.0), and its IMX585 auto fallback (5993-5996@upstream-1.6.0) had no readout check (6162-6164 lists only IMX477/577/294).

**How to spot it.** grep -n 'ScalerCropMaximum' src/camera/CameraController.cpp, and for each hit ask: does it hold for a driver whose binned crop is in output pixels? Also check whether an exact-mode block tests useExplicitSensorConfig.

**Options.**

- Skip the crop comparison when crop == raw size (local, one condition; chosen)
- Teach the block per-driver crop semantics via the probe (needs commit 5+ data, bigger)
- Drop the crop check entirely (loses the port driver's adjusted-mode detection)

**Chosen, and why.** The exact-mode block now runs only for an explicit sensorConfig. It skips the crop comparison when the reported crop equals the raw size. A colour IMX585 on the auto path gets the IMX477/577 size rule, which does nothing until commit 5 widens allowAutoSensorConfigFallback. We gave up exact crop checking for drivers that report crop == output.

**After.**

```
+                     sensorFamily_ == SensorFamily::Imx294 ||
+                     (sensorFamily_ == SensorFamily::Imx585 && !monochromeSensor_ && !useExplicitSensorConfig))) {
+                if (sensorFamily_ == SensorFamily::Imx585 && !monochromeSensor_ && useExplicitSensorConfig) {
+                    // A driver that reports its crop as the output size gives no window to compare.
+                    if (adjusted.empty() && imx585Row && cropMaximum && cropMaximum->size() != rawSize) {
```

**Checked.** Run here: check_core.sh both builds and 18 host tests. Still needs the Pi. Original driver (e5b74d3): before this commit, the output of journalctl -u apertar-core -b | grep -E 'camera configured|adjusted by the driver' shows 'adjusted by the driver (scaler crop maximum (0, 0)/1920x1080)'; after it, 1920x1080 configures. Port driver (cd548ef): the 'camera configured:' lines for 1920x1080, 3840x2160 and 3840x2072 are unchanged. The auto rule is checked in commit 5: on the port driver a 3840x2076 auto request is refused with 'adjusted to too-small stream 3840x2072'.

**Rule.** A readout check must not assume what a driver reports as its crop window. When the driver reports crop == output there is no window to compare, so fall back to the size rule.


---

## C54. camera: colour IMX585 3840-wide crops fall back to the automatic sensor configuration again

Apertar-Core `3eef877`. Finding: camera-modes commit 5. Reviewed by a second agent: not reviewed.

**What was there.**

src/camera/CameraController.cpp:8309@cinemate-port (lane-core4 tip 2e0d545). The automatic fallback was allowed only for mono, IMX294 and IMX577:
        const bool allowAutoSensorConfigFallback = monochromeSensor_ || sensorFamily_ == SensorFamily::Imx294 ||
                                                   sensorFamily_ == SensorFamily::Imx577;
In the loop below, `if (!useExplicitSensorConfig && !allowAutoSensorConfigFallback) continue;` skips the auto try. For a colour IMX585, an explicit failure was therefore final.

**Why it is a problem.** The original driver (e5b74d3) and the port driver (cd548ef) offer different 3840-wide crops. Take a crop that the installed driver has no explicit mode for, for example a saved 3840x2076 on the port driver with APERTAR_SENSOR_PROBE=0. That crop got no configuration at all. 1.6.0 tries explicit first, then falls back to auto for the IMX585 3840 raw12 crops and crops in software (CameraController.cpp:5993-5996@upstream-1.6.0, loop :6012-6017). Its invalidReadout rule (:6162-6183) decides what an auto config may hand back. The conventions page calls this "the driver may lack an explicit mode" precedent.

**How to spot it.** grep -n allowAutoSensorConfigFallback src/camera/CameraController.cpp in both trees and compare the sensor clauses. Ask: if this sensor's explicit sensorConfig is refused, does any configuration remain? Check that every sensor allowed into auto has a matching invalidReadout or size-rule branch.

**Options.**

- Add upstream's clause using the existing isImx585LegacyCropResolution plus width == 3840: three lines, no new size list (chosen)
- Restore upstream's own isImx585Raw12CropResolution list: a second list of the same sizes that drifts from the tables
- Allow auto for every IMX585 size: binned 1920 crops and Clear HDR rows would get auto configs that 1.6.0 never allowed, which is a behaviour change with no precedent

**Chosen, and why.** Option 1, as the design page says. The port's helper already lists the 3840 crops, including 2072 for the port driver, and the width test keeps the 1920 entries out. What was given up: a byte-for-byte copy of 1.6.0's list. 3840x2072 can now fall back to auto too, which 1.6.0 could not do because it did not know that size. Commit 4's size rule guards that path.

**After.**

```
        const bool allowAutoSensorConfigFallback = monochromeSensor_ || sensorFamily_ == SensorFamily::Imx294 ||
                                                   sensorFamily_ == SensorFamily::Imx577 ||
                                                   (sensorFamily_ == SensorFamily::Imx585 &&
                                                    sanitized.resolution.width == 3840 &&
                                                    isImx585LegacyCropResolution(sanitized.resolution));
```

**Checked.** Run here: check_core.sh /home/user/wt/lane-core4 lane-core4 both tests. Both builds and 18 host tests pass. The 3 warnings in the build without libcamera are on lines this commit did not touch: 1248, 7777 and 7930. No host test reaches the configure loop, which is inside #if APERTARCORE_HAS_LIBCAMERA. Still needs the camera, checked with journalctl -u apertar-core -b | grep -E 'camera configured|adjusted to too-small|rejected by'. Port driver cd548ef, with APERTAR_SENSOR_PROBE=0 in the unit environment: set_resolution 3840x1744 still configures explicitly. Then hand-edit resolution_height=2076: the journal shows the explicit try rejected, then either an auto configure with raw 3840x2160 or 'adjusted to too-small stream 3840x2072'. It must never show a configured raw 3840x2072. Original driver e5b74d3: set_resolution 3840x1744 configures.

**Rule.** If the driver may lack an explicit mode, let the configure loop fall back to auto for that size, and check what auto hands back with a size rule. Do not leave the size without any configuration.


---

## U4. ui: clip-name, buffer, log and pre-roll invokables return bool

Apertar-UI `62b239c`. Finding: touch-ui commit 1. Reviewed by a second agent: accept.

**What was there.**

src/ApertarControlBridge.cpp:632-727@cinemate-port (the lane tip before the fix, ac1fc28):
void ApertarControlBridge::applyBufferMode(const QString &value)
{
    ...
    if (!sendCoreCommand(QStringLiteral("set_buffer_mode"), {...})) return;
    if (m_bufferSetting != value) { m_bufferSetting = value; emit bufferSettingChanged(); }
}
applyClipNameTemplate had the same shape: `QJsonObject reply; if (sendCoreCommand(..., &reply)) applyClipNameState(reply);`. applyCdngLog set m_cdngLogOn after the send. applyStoragePreroll and applyStoragePrerollAuto threw away the result of sendCoreCommand.

**Why it is a problem.** In original Apertar, command invokables return bool: false after setLastError, otherwise the result of sendCoreCommand (UIC-9). Examples are applyCaptureMode and applyPhotoLongExposureEnabled at ui-upstream src/ApertarControlBridge.cpp:731-741@upstream-1.6.0. A void invokable hides failure from QML. The extra assignments did the same work twice. sendCoreCommand passes every reply line to applyCoreMessage, and any line with "ok" goes on to applyCoreState (ACB:1411-1412). applyCoreState then runs applyBufferState, applyCdngLogState and applyClipNameState (ACB:1732-1734). Core's replies carry the needed keys (core-work src/ApertarCoreApp.cpp): set_buffer_mode adds bufferSettingMembers() with buffer_setting (:12868), set_cdng_log returns settingsBody with cdng_log (:13101, key at :356), and set_clip_name_template returns settingsBody with clip_name_template and example (:13269-13271, key at :373). So the second write either repeated what Core had already said or covered it with the value the UI had asked for.

**How to spot it.** grep -n 'Q_INVOKABLE void' src/*.hpp: only notifyUserActivity and refresh should be void. In an invokable body, an `if (m_x != value) { m_x = value; emit ... }` right after sendCoreCommand is a smell: check whether the reply already carries that key.

**Options.**

- Thin bool invokables that leave the state to the reply through applyCoreState. Small, and the same as 1.6.0. Cost: the screen updates only from Core's answer, which is what 1.6.0 does.
- Return bool but keep the post-send assignments. Smaller diff, but the state is still written twice, from two sources.
- Change QML to act on the results now. Out of scope: commits 2-4 replace those tiles.

**Chosen, and why.** Option 1, as the plan says. Core's reply is the only source of the state, and the bridge only reports whether the command succeeded. Given up: the optimistic local update. Nothing is lost, because the reply is handled inside the same sendCoreCommand call, before it returns.

**After.**

```
bool ApertarControlBridge::applyBufferMode(const QString &value)
{
    if (value != QStringLiteral("frames") && value != QStringLiteral("ram")) {
        setLastError(QStringLiteral("Invalid write buffer mode."));
        return false;
    }
    // The reply carries buffer_setting, which applyCoreState applies.
    return sendCoreCommand(QStringLiteral("set_buffer_mode"), { { QStringLiteral("value"), value } });
```

**Checked.** Run here: /home/user/build/bin/check_ui.sh /home/user/wt/lane-ui1 lane-ui1 printed PASS with 0 warnings (Qt UI build, QML compiled ahead of time). Nothing could be run on a screen here. Needs the camera: in Settings > Record, switch Write Buffer between Frames and RAM, and Log between On and Off; the tiles follow as before. Then run apertar-cmd '{"cmd":"get_state","id":1}' | grep -o '"buffer_setting":"[a-z]*"' and check it shows the choice. Edit the clip-name pattern and check that "Next clip" follows.

**Rule.** A bridge command invokable returns bool and does not write state that Core's reply already carries. applyCoreState applies that reply.


---

## U5. qml: Log is a dropdown next to Compression, sent as Core's off or auto

Apertar-UI `9500ebc`. Finding: touch-ui commit 2. Reviewed by a second agent: accept.

**What was there.**

qml/SettingsPage.qml:3463-3495@cinemate-port (lane tip 98d7a1c): Log was a Column below Write Buffer, holding a "Log" header Text, an ActionTile and the status Text.
    ActionTile {
        label: apertarControlBridge.cdngLogOn ? "On" : "Off"
        tone: apertarControlBridge.cdngLogOn ? "accent" : "default"
        onClicked: apertarControlBridge.applyCdngLog(!apertarControlBridge.cdngLogOn)
    }
In src/ApertarControlBridge.cpp:708 the bridge took `bool on` and turned it into the wire word itself: `on ? "auto" : "off"`.

**Why it is a problem.** This was a choice of values drawn as a button. ActionTile is a verb with a fixed tone, and no upstream QML file sets `tone:` conditionally (QML-23, QML-26). Upstream draws a choice as an InlineDropdownField with {value,label} options. The example is Compression, in the same grid: qml/SettingsPage.qml:3244-3261@upstream-1.6.0. Upstream sends an enum as Core's own word and lets Core refuse unknown values (applyCdngCompression value=, ApertarControlBridge.cpp:516-535@upstream-1.6.0; UIC-12 keeps booleans for true/false switches only). Log is an enum in Core (CdngLog Off/Auto), so the bool was a UI-side translation of an enum.

**How to spot it.** Run `grep -n 'tone: .*?' qml/*.qml`. A conditional tone means a button is being used as a selector. Also look for a bridge invokable that takes `bool` and sends `? "word" : "word"`: that is an enum disguised as a bool. When adding a field to formatFieldsGrid, also update activeFieldCount.

**Options.**

- Dropdown in formatFieldsGrid next to Compression, bridge takes the QString word: matches upstream Compression exactly; one extra term in activeFieldCount
- Dropdown kept in its own Column below Write Buffer: smaller diff, but leaves Log away from the other cDNG format fields and keeps a lone header
- TogglePill row with the bool kept: fits a switch, but Core's value is an enum (off/auto) and the design settled it as an enum (command-plane.md:293)

**Chosen, and why.** Option 1. This is the item as written: the field sits next to Compression and is shaped like it. The grid's activeFieldCount has to count the new field, because the grid sets its height by hand from that count. A Qt Grid gives no implicit height here: `height: activeRowCount * resolutionField.height`. One thing gives way. The status text now sits under the whole grid, not under a "Log" header. Its strings are unchanged.

**After.**

```
    InlineDropdownField {
        visible: root.cdngRecordFormat && !!apertarControlBridge && apertarControlBridge.cdngLogAvailable
        label: "Log"
        value: apertarControlBridge && apertarControlBridge.cdngLogOn ? "auto" : "off"
        displayValue: value === "auto" ? "On" : "Off"
        options: [{ value: "off", label: "Off" }, { value: "auto", label: "On" }]
        onValueSelected: function(v) { apertarControlBridge.applyCdngLog(v) }
    }
bool applyCdngLog(const QString &value) { return sendCoreCommand("set_cdng_log", {{"value", value}}); }
```

**Checked.** Run here: /home/user/build/bin/check_ui.sh /home/user/wt/lane-ui1 lane-ui1 printed PASS with 0 warnings. That builds the UI with QML compiled ahead of time. No other callers of applyCdngLog exist (grep over qml/ and src/). Nothing was seen on a screen. Still needs the camera: set cDNG + Clear HDR, open Settings > Record and pick Log On. Then `printf '%s\n' '{"cmd":"get_state","id":1}' | socat - UNIX-CONNECT:/tmp/apertar-core.sock | grep -o '"cdng_log":"[a-z]*"'` should show auto, and the field should show On. Check that the format grid has no gap or overlap with Crop shown and with Crop hidden, and that the status text reads right under the grid.

**Rule.** A choice between values is an InlineDropdownField that sends Core's own word; an ActionTile is a verb with a fixed tone.


---

## U6. qml: Write Buffer is a dropdown

Apertar-UI `4d8bb42`. Finding: touch-ui commit 3. Reviewed by a second agent: accept.

**What was there.**

qml/SettingsPage.qml:3456-3480@cinemate-port (lane-ui1 tip 3b2c98b): the choice was a header Text plus a Row of two ActionTiles whose tone was set from the current value:
    ActionTile {
        label: "Frames"
        tone: apertarControlBridge.bufferSetting === "frames" ? "accent" : "default"
        actionEnabled: !apertarControlBridge.recording
        onClicked: apertarControlBridge.applyBufferMode("frames")
    }
    ActionTile { label: "RAM"; tone: ... === "ram" ? "accent" : "default"; ... }

**Why it is a problem.** An ActionTile in Apertar is a verb button with a fixed tone (SettingsPage.qml:3640, :5416@upstream-1.6.0). No upstream QML file sets tone: from a condition (QML-26). A pick between values is an InlineDropdownField with {value,label} options, for example Compression (SettingsPage.qml:3244-3261@upstream-1.6.0, QML-23). Tiles used as fake radio buttons are a second widget idiom that the original developer would have to learn and keep up.

**How to spot it.** grep -n 'tone: .*?' qml/*.qml finds tiles whose colour depends on state. Two or more ActionTiles in a Row that call the same apply* with different literal values are the same smell.

**Options.**

- Replace the header and the tile Row with a full-width InlineDropdownField inside the existing Column: smallest change, keeps the visible: condition and the status line (chosen)
- Move the field into the format grid next to Compression/Log, as commit 2 did for Log: needs another activeFieldCount term and moves the status text; more churn for no gain
- Keep the tiles but give them a fixed tone: still two buttons for one value, not the upstream idiom

**Chosen, and why.** Option 1. The field is placed where the tiles were, full width, like the full-width "Color Profile" field just below it. The Column still hides the whole block until Core has sent buffer_setting. Given up: lining it up with the two-column grid above. That would need a change to the grid's row count, which this item does not ask for.

**After.**

```
InlineDropdownField {
    width: parent.width
    label: "Write Buffer"
    value: apertarControlBridge ? apertarControlBridge.bufferSetting : "frames"
    displayValue: value === "ram" ? "RAM" : "Frames"
    options: [ { value: "frames", label: "Frames" }, { value: "ram", label: "RAM" } ]
    fieldEnabled: apertarControlBridge && !apertarControlBridge.recording
    onValueSelected: function(v) { apertarControlBridge.applyBufferMode(v) }
}
```

**Checked.** Here: /home/user/build/bin/check_ui.sh /home/user/wt/lane-ui1 lane-ui1 printed PASS with 0 warnings. That run builds the UI and compiles the QML ahead of time, which catches unknown properties but not behaviour. Nothing was run on a screen. On the camera: select cDNG or MLV, go to Settings > Record, pick Write Buffer RAM, then start and stop a take. After that, `grep '^buffer=' ~/apertar-hardware.conf` should show ram. Core writes [storage] buffer= (core-work App:12856); storage-settings may rename that file. Also check that the field shows RAM, that the status line follows, and that the field is greyed during a take.

**Rule.** A choice between values is an InlineDropdownField with {value,label} options. An ActionTile is a verb and keeps a fixed tone.


---

## U7. ui: only the ISO and WB auto keys reset the get_state poll

Apertar-UI `8a1ec6e`. Finding: touch-ui commit 5. Reviewed by a second agent: accept.

**What was there.**

src/ApertarControlBridge.cpp:1597-1609@cinemate-port (applyCoreState, added in f1edf96). This block runs for every state applyCoreState receives:
        if (isoInUse != m_isoInUse || ... || m_ladderActive != previousLadderActive) {
            ...
            emit cameraSetValuesChanged();
        }
        updateRefreshTimer();
    }
The iso_auto and wb_auto branches only assigned the value, as one-line ifs.

**Why it is a problem.** updateRefreshTimer() calls m_retryTimer.setInterval(). In Qt 6, setInterval on a running QTimer restarts the countdown. Every event routed into applyCoreState therefore pushed the next get_state poll back. A 1 s timelapse sends one timelapse_progress event per shot (core CC:12378). That is fast enough that the 1000 ms ISO/WB-auto poll never fires, and ISO and WB in use stop updating. Original 1.6.0 has no call in applyCoreState. It sets the interval on socket state changes and after poll and command replies (ui-upstream src/ApertarControlBridge.cpp:125-145, :1041-1104, :1585). UIC-4 says state keys are applied inline in applyCoreState. A side effect tied to all state, not to one key, does not fit that rule.

**How to spot it.** grep -n 'updateRefreshTimer\|setInterval\|\.start(' inside applyCoreState, applyCoreMessage or any per-event handler. Ask: does this run for every event? If yes, does it restart a running timer? QTimer::setInterval and QTimer::start both restart the countdown.

**Options.**

- Delete the call entirely, exactly as 1.6.0: smallest diff, but an ISO/WB Auto switch made by the WebUI or a button (a settings event, no reply here) would leave the poll at 30 s until the next command reply
- Call it inside the iso_auto and wb_auto branches (the plan): +2 lines of logic; the interval follows Auto switches from any client; a get_state reply or the rare settings event that carries the keys restarts the timer, which is harmless right after a poll
- Call it only when m_isoAuto or m_whiteBalanceAuto actually changes: strictest, about 6 more lines with a compare and a local, more than the item asked for

**Chosen, and why.** I chose the plan's form: the call goes inside the two branches, with braces added. It keeps the port's real gain over 1.6.0: an Auto switch made by another client still speeds the poll up. It also removes the restart on unrelated events. I did not add a compare-on-change. Which events carry iso_auto and wb_auto (checked in core-work): get_state and command replies, which already call updateRefreshTimer() on their own path, and the settings event, which has one caller (CC:12879) and is rare. A restart from those does no harm. What I gave up: a settings event still restarts the timer even when the Auto flags did not change.

**After.**

```
    if (state.contains(QStringLiteral("iso_auto"))) {
        m_isoAuto = state.value(QStringLiteral("iso_auto")).toBool(m_isoAuto);
        updateRefreshTimer();
    }
...
    if (state.contains(QStringLiteral("wb_auto"))) {
        m_whiteBalanceAuto = state.value(QStringLiteral("wb_auto")).toBool(m_whiteBalanceAuto);
        updateRefreshTimer();
    }
```

**Checked.** Here: /home/user/build/bin/check_ui.sh /home/user/wt/lane-ui1 lane-ui1 returned PASS with 0 warnings. That is the Qt build with the QML compiled ahead of time. Nothing can be run on a screen here. Still needs the camera: (1) Set ISO Auto and start a 1 s timelapse in Still Mode. Change the light. The green ISO in use should follow within 2 s. (2) Switch ISO Auto on from the WebUI. The touch ISO in use should start to move within about 1 s, not after 30 s. Optional: apertar-cmd '{"cmd":"get_state","id":1}' | grep -o '"iso_auto":[a-z]*' to confirm the mode.

**Rule.** Restart or retune a QTimer only where its inputs change. Never do it in a function that runs for every message.


---

## U8. ui: SettingsBridge reads fileTimecodeSeparate

Apertar-UI `dba1995`. Finding: touch-ui commit 11. Reviewed by a second agent: accept.

**What was there.**

The port had no way to tell whether the file timecode was set apart. src/SettingsBridge.hpp:59@lane-ui1 (before 30961b6) only has the screens' mode:
    Q_PROPERTY(QString timecodeMode READ timecodeMode WRITE setTimecodeMode NOTIFY timecodeModeChanged)
The port always treats the file timecode as separate. The tap and the Settings first row change only the screens' timecode (design page, "How it works in the port today", Timecode).

**Why it is a problem.** Commit 12 brings back 1.6.0's tap, which sets both timecodes, unless the operator has set the file timecode apart. For that the UI must be able to read the UI.conf key fileTimecodeSeparate that Core will write. In original Apertar, every UI.conf toggle reaches QML through one SettingsBridge Q_PROPERTY, built like zebraEnabled (conventions R3 steps 1-2; ui-upstream src/SettingsBridge.cpp setZebraEnabled and pollExternalSettings). Core writes UI.conf, and the bridge's file watcher re-reads it.

**How to spot it.** Run grep -n 'zebraEnabled' src/SettingsBridge.cpp src/SettingsBridge.hpp. Each place it shows up (constructor, poll, setter, serialize, apply, header) should have a twin for the new key. Also watch for QSettings reads of UI.conf outside SettingsBridge.

**Options.**

- Copy the zebraEnabled pattern into SettingsBridge (property, member, constructor read, setter, poll re-read, preset save/apply): about 27 lines, the original pattern
- Read the key ad hoc with QSettings inside ApertarControlBridge or QML: fewer lines, but a second way to read UI.conf, and QML could not bind to it or be notified of changes
- Have Core add a field to get_state: wire change, and it breaks the rule that UI.conf values live only under "ui":{}

**Chosen, and why.** Option 1, as the design page and R3 say. The setter also writes UI.conf, so touch presets can carry the key, as every UI.conf toggle does. What was given up: nothing in behaviour. The cost is a property that no QML reads until commit 12.

**After.**

```
bool SettingsBridge::fileTimecodeSeparate() const { return m_fileTimecodeSeparate; }
void SettingsBridge::setFileTimecodeSeparate(bool value)
{
    if (m_fileTimecodeSeparate == value) return;
    m_fileTimecodeSeparate = value;
    if (!m_externalSettingsSyncing) m_settings.setValue("fileTimecodeSeparate", value);
    m_settings.sync(); updateSettingsFileState(); emit fileTimecodeSeparateChanged();
}
```

**Checked.**

Run here: /home/user/build/bin/check_ui.sh /home/user/wt/lane-ui1 lane-ui1 gave PASS with 0 warnings (UI build, QML compiled ahead of time). Nothing could be run on a screen. Still needs the camera, after Core commit 9 is deployed:
1. Run apertar-cmd '{"cmd":"set_timecode_mode","value":"rec_run","target":"ui","id":1}'.
2. Run grep fileTimecodeSeparate ~/.config/CinePi/UI.conf. It should show true.
3. Save a touch preset. Its JSON should hold "fileTimecodeSeparate": true.
The screen check (that the tap follows the key) belongs to commit 12.

**Rule.** A new UI.conf key reaches QML through one SettingsBridge Q_PROPERTY built like zebraEnabled, in the same six places. Never read it ad hoc.


---

## U9. qml: without fps_max and iso_max the touch caps are fork main's again

Apertar-UI `0cbd664`. Finding: touch-ui commit 15. Reviewed by a second agent: accept.

**What was there.** qml/CameraPage.qml:526@cinemate-port: const maximum = root.controlBridge ? root.controlBridge.isoMax : (root.losslessIsoLimitedMode ? 1600 : 0); with a bridge and iso_max 0 lossless offered the whole list with Auto. qml/CameraPage.qml:~820: the IMX585 4K modes were capped at 25 fps in Clear HDR 16-bit. fpsCeiling: the IMX585 lossless cap was an empty block.

**Why it is a problem.** These fallbacks run only when Core sends no fps_max or iso_max, and there they differed from the merge target. Apertar 1.6.0 and fork main cap lossless at ISO 800 with no Auto, the IMX585 4K modes at 30 fps and IMX585 lossless at 30 fps (ui-upstream qml/CameraPage.qml:511-513, :815-816).

**How to spot it.** grep -n "controlBridge ? .* : (" qml/*.qml and ask which branch runs when the bridge is present but the field is 0.

**Options.**

- Restore fork main's fallbacks exactly (small diff, matches the merge target)
- Drop the fallbacks altogether because Core always sends the fields (larger change, outside this item)

**Chosen, and why.** Restore fork main's fallbacks: isoOptions uses Core's isoMax only when it is above 0, otherwise lossless stops at 800 with no Auto; the IMX585 4K modes go back to 30 fps; IMX585 lossless gets its 30 fps cap back. This round only corrects the Why sentence about the 1600 fallback.

**After.**

```
const coreMaximum = root.controlBridge ? root.controlBridge.isoMax : 0
const losslessFallback = !(coreMaximum > 0) && root.losslessIsoLimitedMode
const maximum = coreMaximum > 0 ? coreMaximum : (losslessFallback ? 800 : 0)
if (root.clearHdrActive || losslessFallback)
    return entries
```

**Checked.** Ran here: /home/user/build/bin/check_ui.sh /home/user/wt/lane-ui1 lane-ui1, PASS with 0 warnings. Nothing can be seen on a screen here. On the camera, the current Core always sends fps_max and sends iso_max in lossless and Clear HDR modes, so these lines run only against a Core that sends neither field.

**Rule.** Check a ternary fallback against the branch that runs on the device, not only the literal in it.


---

## C55. core: the controls and media events carry the state keys

Apertar-Core `07ed294`. Finding: touch-ui commit 6. Reviewed by a second agent: not reviewed.

**What was there.**

src/ApertarCoreApp.cpp:12352@cinemate-port
"\"errors\":" + ... + ",\"warnings\":" ...  (controls event)
src/ApertarCoreApp.cpp:10827@cinemate-port mediaEventJson:
out << "{\"event\":\"media\",\"state\":\"" << snapshot.stateName() ...
    << ",\"mounted\":" << (snapshot.mounted() ? ...)

**Why it is a problem.** 1.6.0 events that carry state are written with the same key names as get_state (standby, still_exposure, timelapse_progress, media_write_state), and the UI passes them whole to applyCoreState (ui-upstream src/ApertarControlBridge.cpp applyCoreMessage; conventions UIC-4). A media event with a top-level state key would hit applyCoreState's standby branch and set standby from the card state. The port needed its own branches and a setter that took key names.

**How to spot it.** grep -n 'publishEvent("{\\"event' src/ApertarCoreApp.cpp and compare each member name with the get_state body. Ask: could the UI reuse one reader for the event and the reply? A member that means the same thing under a second name is the smell.

**Options.**

- Rename the event members to the state keys (4 lines, chosen)
- Keep the names and let the UI map them in two branches (what the port did; two spellings forever)
- Drop the events and rely on the 30 s poll (card pull shows late)

**Chosen, and why.** The first option. The UI then needs no key-name setter. Given up: any outside script that reads the old event keys; the KB search found none (longtakes.py reads media_state from get_state).

**After.**

```
out << "{\"event\":\"media\",\"media_state\":\"" << snapshot.stateName() << "\""
    << ",\"media_alive\":" << (snapshot.mounted() ? "true" : "false")
...
"\",\"controls_errors\":" + std::to_string(controlsErrors_.load()) + ",\"controls_warnings\":" + ...
```

**Checked.** Ran here: check_core.sh lane-tc both tests (PASS), --simulate with scratch HOME and APERTAR_HARDWARE_CONFIG: set_controls over the socket produced {"event":"controls","applied":"h4a4b...","groups":"","controls_errors":0,"controls_warnings":0}; smoke_core + shape_subset: every base field present with the same type. Not provoked here: the media event (needs a card change). On the Pi: keep socat - UNIX-CONNECT:/tmp/apertar-core.sock open, pull the card, look for {"event":"media","media_state":...}. Also: grep -rn '"mounted"' ~/ on the rig for scripts that read the old key.

**Rule.** An event that carries state uses the state's key names, so one reader serves the event and the reply.


---

## C56. core: set_timecode_mode records in UI.conf whether the file timecode is set apart

Apertar-Core `ba1aa75`. Finding: touch-ui commit 9. Reviewed by a second agent: not reviewed.

**What was there.**

src/ApertarCoreApp.cpp:13295-13316@cinemate-port
if (target != "files") {
    (void)updateSharedUiGeneralSettings({ { "timecodeMode", mode == RecRun ? "Rec Run" : "Free Run" } });
}
// target=ui / files split the two timecodes; nothing recorded that the split was chosen

**Why it is a problem.** 1.6.0 has one timecode and Core writes the mode into UI.conf beside the camera setting (ui-upstream ApertarControlBridge.cpp:1466-1471 copies it; conventions C1-I18: UI.conf and camera mode equal). The port's split breaks that on purpose, so the operator's choice has to be stored where the UI can read it. Otherwise a stock camera and a deliberately split one look the same.

**How to spot it.** Ask: when a client can send an optional argument that changes meaning (target=), where is the result of that choice stored? grep for the argument name in the writers; an argument that changes behaviour but leaves no trace is the smell.

**Options.**

- One UI.conf bool written by the one command that sets the meaning (chosen, about +12)
- Add a state field and a new command (new surface, 1.6.0 clients unaffected but more to keep)
- Infer the split by comparing UI.conf and camera mode (guesses wrong when they are equal by chance)

**Chosen, and why.** The first option. The writer sits beside timecodeMode (CMD-26: one writer for the meaning). The false write happens only over a true, so a stock UI.conf stays without the key. Presets carry the key with the existing bool forms (addBoolFromMap writer, addBoolUpdate reader). Given up: a state field; no reader needs it yet (the WebUI commit adds ui.file_timecode_separate).

**After.**

```
std::vector<std::pair<std::string, std::string>> updates = { { "timecodeMode", ... } };
if (target == "ui")
    updates.emplace_back("fileTimecodeSeparate", "true");
else if (readSharedUiSettings().fileTimecodeSeparate)
    updates.emplace_back("fileTimecodeSeparate", "false");
(void)updateSharedUiGeneralSettings(updates);   // target=files: its own call with the one pair
```

**Checked.** Ran here: check_core.sh lane-tc both tests (PASS). --simulate, fresh HOME and APERTAR_HARDWARE_CONFIG: no target on a fresh HOME left no fileTimecodeSeparate line; target=files wrote true; target=ui true; no target afterwards false. apply_preset with fileTimecodeSeparate=true wrote the key; /api/presets/save wrote "fileTimecodeSeparate":true into the preset file. smoke_core + shape_subset: every base field present with the same type. Needs the camera: apertar-cmd '{"cmd":"set_timecode_mode","value":"rec_run","target":"ui","id":1}' then grep fileTimecodeSeparate ~/.config/CinePi/UI.conf shows true.

**Rule.** An optional argument that changes meaning leaves its trace in the setting file, written by the one command that sets that meaning.


---

## C57. core: a split timecode on an existing camera is taken over at start

Apertar-Core `038fc4a`. Finding: touch-ui commit 10. Reviewed by a second agent: not reviewed.

**What was there.**

src/ApertarCoreApp.cpp:8077-8091@cinemate-port
// after camera_.start: only the still-mode and bracketing reconcile against UI.conf
// nothing for the timecode: two different modes were simply left as they were

**Why it is a problem.** The port's earlier UI let the operator split the timecodes without leaving any mark. Once fileTimecodeSeparate exists (previous commit), an already split camera has no key and would be seen as a stock camera, and the touch UI would copy one mode over the other. Original Apertar already reconciles UI.conf against camera settings at this point for still mode (core-upstream ApertarCoreApp.cpp:6845-6857).

**How to spot it.** When a new settings flag is added, ask: what do cameras that were already in that state have? A flag with a safe default and no migration is the smell.

**Options.**

- Reconcile at start, one write, one log line (chosen, about +6)
- Let the UI infer the split at every get_state (race with the copy, runs every second)
- Do nothing and ask owners to set it by hand (stock-safe, but the port's own users lose their setting silently)

**Chosen, and why.** The first option, in the same place and shape as the still-mode reconcile. It writes true only, never false, and only when the modes differ. Given up: a UI.conf with no timecodeMode line reads as Free Run, so a camera on Rec Run with no line gets the key; 1.6.0 never leaves that state.

**After.**

```
if (!secondaryRole() && !stillSettings.fileTimecodeSeparate &&
    stillSettings.timecodeMode != (camera_.settings().timecodeMode == TimecodeMode::RecRun ? "Rec Run" : "Free Run")) {
    (void)updateSharedUiGeneralSettings({ { "fileTimecodeSeparate", "true" } });
    std::cerr << "ApertarCore timecode: UI and file timecode differ, kept apart (fileTimecodeSeparate=true)\n";
}
```

**Checked.** Ran here: check_core.sh lane-tc both tests (PASS). --simulate, one fresh HOME per case with APERTAR_HARDWARE_CONFIG: UI.conf timecodeMode=Rec Run and Core Free Run: key and log line appear; equal modes (Free Run/Free Run): no key, no line; UI.conf without timecodeMode: no key; key already true: unchanged. Needs the camera (owner's rig): journalctl -u apertar-core -b | grep 'ApertarCore timecode'; his modes are equal so no line is expected.

**Rule.** A new flag that changes meaning needs a start-up step for the cameras that were already in the new state.


---

## C58. web: the timecode Mode sends no target; Files sets the file timecode apart

Apertar-Core `5c98f4d`. Finding: webui timecode. Reviewed by a second agent: not reviewed.

**What was there.**

src/web/WebControlPage.cpp:16094-16099, :11183-11188@cinemate-port (line numbers earlier tip)
for (const [id, target, current] of [["settingsTimecodeOptions", "ui", uiTimecodeLabel(snapshot)], ["settingsFileTimecodeOptions", "files", ...]])
    sendCommand(timecodeCommand(value, target));   // target always sent: "UI timecode" / "File timecode"

**Why it is a problem.** 1.6.0 has one timecode control that sends set_timecode_mode with no target (core-upstream WebControlPage.cpp:10021-10023, :7042-7043). With fileTimecodeSeparate recorded by Core, a WebUI that always sends target would split a stock camera on its first timecode change. 1.6.0 also publishes a ui object with timecode_mode (core-upstream ApertarCoreApp.cpp:7966), the precedent for ui.file_timecode_separate.

**How to spot it.** For every client of an optional command argument, ask: what does the stock path send? grep -n 'timecodeCommand\|set_timecode_mode' in the page and the touch UI; both clients must treat 'no target' as the default.

**Options.**

- WebUI gets the touch card's shape: Mode (no target), Files (Same as Mode / fixed), state ui.file_timecode_separate (chosen, about +2 Core, +25 page)
- Core ignores target from the WebUI (hides the problem, breaks the owner's UI-only tap)
- Leave the WebUI as is (a stock camera's first WebUI change splits it)

**Chosen, and why.** The first option. Mode sends target=ui only while the split is on, so Mode never undoes the operator's choice; Same as Mode sends the Mode value with no target so Core writes false. Labels are the ones the page already uses (the label commit stays held for Patrik); the option 'Same as Mode' is new. The Favorites card got the same two blocks. Given up: nothing in behaviour.

**After.**

```
function timecodeCommand(value, target) { const command = { cmd: "set_timecode_mode", value: ... }; if (target) command.target = target; return command; }
function timecodeModeCommand(value) { return timecodeCommand(value, fileTimecodeSeparate(state.snapshot) ? "ui" : ""); }
function timecodeFilesCommand(value) { return value === "Same as Mode" ? timecodeCommand(uiTimecodeLabel(state.snapshot)) : timecodeCommand(value, "files"); }
// Core ui block: << ",\"file_timecode_separate\":" << (uiSettings.fileTimecodeSeparate ? "true" : "false")
```

**Checked.** Ran here: check_core.sh lane-tc both tests (PASS, 0 warnings). --simulate, fresh HOME and APERTAR_HARDWARE_CONFIG, page driven with Playwright (Settings > Record): Mode Clip sent no target (state: separate false, both rec_run); Files Time of Day sent target=files (separate true, files free_run, screens rec_run); Mode then sent target=ui; Files Same as Mode sent no target (separate false, both equal); rows followed the state; no page error. Favorites card (favorites_order=timecode) shows Mode/Files and sent target=files. smoke_core + shape_subset: every base field present with the same type (ui.file_timecode_separate is a new field). Needs a browser on the camera for the look: http://<camera>:8000/, Settings > Record > Timecode.

**Rule.** Every client of an optional argument sends nothing for the stock case; the setting that changes the meaning is a separate, visible control.


---

## U10. ui: controls and media events go through applyCoreState

Apertar-UI `8385490`. Finding: touch-ui commit 7. Reviewed by a second agent: not reviewed.

**What was there.**

src/ApertarControlBridge.cpp:1328-1340@cinemate-port
if (event == "controls") { setControlsStatus(message, "errors", "warnings"); return; }
if (event == "media") { setCoreMediaState(message.value("state").toString(), message.value("mounted").toBool(true)); return; }
void setControlsStatus(obj, errorsKey, warningsKey) // one setter, two spellings

**Why it is a problem.** 1.6.0 sends every event made of state keys to applyCoreState in one if-list (standby, still_exposure, timelapse_progress, media_write_state) and keeps only audio_level apart because it is frequent (ui-upstream ApertarControlBridge.cpp applyCoreMessage; conventions UIC-4). Two key spellings need a setter that takes key names; that is a layer 1.6.0 does not have.

**How to spot it.** In applyCoreMessage look for an event branch that does its own parsing: if the keys could be the state keys, the event belongs in the list. Question: does a helper take key names as arguments?

**Options.**

- Add controls and media to the 1.6.0 event list, read the keys inline (chosen, about -22/+8)
- Keep the branches and rename only the keys (setter stays)
- Send the events through get_state polling only (card pull late by up to 30 s)

**Chosen, and why.** The first option, after Core commit 6 renames the keys. setCoreMediaState stays because it emits the signal MediaStatusBridge listens to. The buffer event keeps its own branch (frequent, as audio_level). Given up: any use of the old key names; no fallback for an older Core (Core and UI ship together).

**After.**

```
if (event == "standby" || event == "still_exposure" ||
    event == "timelapse_progress" || event == "media_write_state" ||
    event == "controls" || event == "media") {
    applyCoreState(message); return; }
// applyCoreState: if (state.contains("controls_errors")) { compare, assign, emit controlsStatusChanged(); }
```

**Checked.** Ran here: check_ui.sh lane-ui-tc lane-ui-tc: PASS, 0 warnings. One conflict while cherry-picking (neighbouring applyCam1State from the dual-sensor work), resolved by keeping it. Checked that no key of either event other than media_state/media_alive/controls_* is read by applyCoreState. Needs the camera: pull the card, NO MEDIA within a second; save a bad pin in Controls, the warning chip appears; 4K take with ISO Auto, ISO in use still moves. Watch: printf '%s\n' '{"cmd":"get_state","id":1}' | socat - UNIX-CONNECT:/tmp/apertar-core.sock

**Rule.** An event made of state keys goes whole to applyCoreState; only a frequent event gets its own branch.


---

## U11. ui: touch presets carry the camera settings Core's presets carry

Apertar-UI `041ec9d`. Finding: touch-ui commit 8. Reviewed by a second agent: not reviewed.

**What was there.**

src/ApertarControlBridge.cpp:1254-1286@cinemate-port cameraPresetSettings()
result.insert("cameraFps", m_fps);
result.insert("cameraIso", m_iso);
result.insert("cameraExposureCompensation", ...);   // only the 1.6.0 key set
// no cameraFpsSpeedRamp*, cameraClipNameTemplate, cameraFpsPhaseLock,
// cameraTimecodeMode, cameraConformFps, cameraClearHdr, cameraHdr*, cameraCdngLog

**Why it is a problem.** Core's buildCurrentPresetPayload (App.cpp 8188-8190@lane-tc) writes these keys and apply_preset reads them. In original Apertar both writers carry the same camera* set and one reader takes it, and a value kept only for presets is a plain member (ui-upstream m_lossyDngRatio). A touch preset that drops keys loses those settings when loaded.

**How to spot it.** Diff the key list of cameraPresetSettings() against buildCurrentPresetPayload (grep -n 'addString("camera\|addBool("camera\|addNumberString("camera'). Any key in one list and not the other is a lost setting.

**Options.**

- Add plain members read in applyCoreState and write Core's keys in Core's order and value words (chosen, about +40)
- Make the touch UI ask Core to build the preset payload (new command, new layer)
- Leave the new keys out (presets silently lose them)

**Chosen, and why.** The first option. Plain members, not Q_PROPERTY, because no QML reads them. conform_fps is kept because the owner asked for it (DA-92, request 21); the lane's first version had dropped it. Loading needs no change: applyCameraPreset forwards every camera* key. Given up: nothing; the key set is bigger.

**After.**

```
result.insert("cameraFpsPhaseLock", m_fpsPhaseLock);
result.insert("cameraTimecodeMode", parseTimecodeModeValue(m_fileTimecodeMode));
result.insert("cameraConformFps", m_conformFps);
result.insert("cameraClearHdr", m_clearHdr);
// applyCoreState:
if (state.contains("conform_fps")) m_conformFps = state.value("conform_fps").toDouble(m_conformFps);
// header: double m_conformFps = 25.0;
```

**Checked.** Ran here: check_ui.sh lane-ui-tc lane-ui-tc, PASS 0 warnings. Core --simulate with a fresh HOME and APERTAR_HARDWARE_CONFIG: apply_preset with exactly the keys the writer now writes, at non-default values, then /api/state: all 14 values matched (conform 24, ramp true/exposure/real/return, phase lock, rec_run, Clear HDR, 3000/10/7/2, cdng_log auto). Cherry-pick was clean on the dual-sensor tree. Needs the camera (HDMI look): save a touch preset with Clear HDR 16-bit and Log On, change both, load it; apertar-cmd '{"cmd":"get_state","id":1}' | grep -o '"cdng_log":"[a-z]*"' shows auto.

**Rule.** Both preset writers carry the same keys under the same names; a value that only presets need is a plain member.


---

## U12. ui: the timecode tap and Mode set both timecodes again unless the file timecode is set apart

Apertar-UI `69e37b5`. Finding: touch-ui commit 12. Reviewed by a second agent: not reviewed.

**What was there.**

src/ApertarControlBridge.cpp:750-771@cinemate-port
bool applyTimecodeMode(const QString &displayValue, const QString &target) // ui|files|both
    sendCoreCommand("set_timecode_mode", {{"value", normalized}, {"target", target}});
    if (target != "files") { m_settings.setValue("timecodeMode", displayValue); ... }
qml/CameraPage.qml:1837 applyTimecodeMode(nextMode, "ui")   // screen only
applyCoreState: no copy of Core's mode into UI.conf

**Why it is a problem.** 1.6.0 has one applyTimecodeMode(displayValue), the tap changes both timecodes, and applyCoreState copies Core's mode into UI.conf so camera and screens stay equal (ui-upstream ACB:622-636, :1466-1471, CPg:1709-1715; CMD-26). The port's tap changed the screens only, so on a stock camera the clips kept the old timecode.

**How to spot it.** grep -n 'applyTimecodeMode' src qml and compare the signature and the callers with ui-upstream. An invokable that gained a mode argument the 1.6.0 caller never sent is the smell.

**Options.**

- 1.6.0 body for the stock path; the split is an operator setting read from UI.conf (chosen, about -20/+26)
- Keep the port's target argument and default to ui (a stock camera changes behaviour: not mergeable)
- Drop the split altogether (loses Patrik's DA-76 decision)

**Chosen, and why.** The first option. Core records the split (previous Core commits); the UI reads it. The copy of Core's mode into UI.conf runs only while the key is false, after m_settings.sync() because Core writes the file. The preset forward closes a race: without it a split touch preset loaded on an unsplit camera would see the reply's copy run before SettingsBridge applies the key. Given up: one m_settings.sync() per get_state reply (QSettings re-reads only a changed file; not measured on a Pi 4).

**After.**

```
bool applyTimecodeMode(const QString &displayValue) { ... sendCoreCommand("set_timecode_mode", {{"value", normalized}}) ... }
bool applyFileTimecodeMode(const QString &displayValue) // adds {"target","files"}
// applyCoreState: m_settings.sync(); if (!m_settings.value("fileTimecodeSeparate", false).toBool()) { setValue("timecodeMode", ...); sync(); }
// applyCameraPreset: ... || it.key() == "timecodeMode" || it.key() == "fileTimecodeSeparate" ||
```

**Checked.** Ran here: check_ui.sh lane-ui-tc lane-ui-tc, PASS 0 warnings; cherry-pick applied cleanly. Core --simulate (fresh HOME): apply_preset with fileTimecodeSeparate=true writes the UI.conf key. Nothing on a screen. Needs the camera (HDMI look on the owner's rig), with the Core commits deployed: stock camera, tap the timecode, apertar-cmd '{"cmd":"get_state","id":1}' | grep -o '"timecode_mode":"[a-z_]*"' shows the new mode; a Rec Run DNG take starts at 00:00:00:00. With the key true: tap changes the screen only. Also: top -H -p $(pidof ApertarUI) during ISO Auto for the sync cost. Must land in the same push as Core commits 9 and 10.

**Rule.** A stock camera takes the 1.6.0 path; a port feature is a setting the operator turns on, read from the settings file.


---

## U13. qml: the timecode card has Mode and Files, Files starts at Same as Mode

Apertar-UI `ed9e539`. Finding: touch-ui commit 13. Reviewed by a second agent: not reviewed.

**What was there.**

qml/SettingsPage.qml:3998-4028@cinemate-port
label: "UI timecode" ... label: "File timecode"
value: apertarControlBridge.fileTimecodeMode   // second row always shows a fixed file value
options: root.timecodeChoices

**Why it is a problem.** 1.6.0 has one row, Mode, that sets both timecodes (ui-upstream SettingsPage.qml:3766-3780). A second row that always shows a fixed file value makes a stock camera look split. The split is Patrik's decision (DA-76), so it is shown only after the operator picks a fixed Files value.

**How to spot it.** Ask of any new settings row: what does it show on a camera where the feature was never turned on? A row that shows a concrete value for an unused feature is the smell.

**Options.**

- Files row whose first option is Same as Mode, value read from UI.conf fileTimecodeSeparate (chosen, about -8/+14)
- Hide the second row until a toggle is on (one more control)
- Keep the always-visible File timecode row

**Chosen, and why.** The first option. SettingsBridge already watches UI.conf (previous commits), so the row follows the key, also after a WebUI split. Labels Time of Day / Clip stay until the held label commit. Given up: nothing in behaviour.

**After.**

```
label: "Files"
value: settingsState.fileTimecodeSeparate && apertarControlBridge ? apertarControlBridge.fileTimecodeMode : "Same as Mode"
options: ["Same as Mode"].concat(root.timecodeChoices)
onValueSelected: v === "Same as Mode"
    ? apertarControlBridge.applyTimecodeMode(settingsState.timecodeMode)
    : apertarControlBridge.applyFileTimecodeMode(v)
```

**Checked.** Ran here: check_ui.sh lane-ui-tc lane-ui-tc, PASS 0 warnings (QML is compiled ahead of time, so unknown properties would fail). Clean cherry-pick. Nothing on a screen. Needs the camera (HDMI look on the owner's rig, hdmi_external_only=false temporarily): Settings > Timecode, Files = Free Run then Same as Mode; grep fileTimecodeSeparate ~/.config/CinePi/UI.conf goes true then false; a WebUI target=files change shows in the row.

**Rule.** A port feature's control shows the stock value until the operator moves it.



---

## C59. core: get_state sends the clip merge keys once

Apertar-Core `0889122`. Finding: CLIP-C-1 (`raw/rev-clip-core.md`). Made by hand. Short entry: same kind as C4.

The clip-split commit 6e340c8 added a second `<< clipMergeStateJson()` to the `get_state` chain, after the settings body, so every `clip_merge_*` key came twice. The second line is gone. How to spot it and the rule: see C4 (read each value once at the top of the handler, write each key once; grep the raw reply, because a JSON parser hides duplicate keys).

---

## C60. build: __int128 is declared with __extension__, as FramePhaseLock.hpp does

Apertar-Core `7962744`. Finding: CLIP-C-6. Reviewed by a second agent: not reviewed.

**What was there.**

src/audio/RecordingClock.hpp:48-56@cinemate-port
  const __int128 period = static_cast<__int128>(1000000) * periodDen;
  const __int128 scaled = static_cast<__int128>(bootUs) * periodNum;
  __int128 slot = scaled / period;
src/util/TakeSlots.hpp:30-91: the same, 12 more lines

**Why it is a problem.** ISO C++ has no __int128; -Wpedantic (CMakeLists.txt, core and both plugins) warns at every declaration and cast. src/camera/FramePhaseLock.hpp:42 already writes '__extension__ typedef __int128 PhaseLockInt128;', which is silent. Upstream 1.6.0 has no __int128 and a clean build, so a new warning source is a mismatch with the build's habit of staying quiet.

**How to spot it.** Count warnings in the gate's build log before and after a series: grep -c 'warning:' <log>. grep -rn __int128 src shows every user. A 'warning: ISO C++ does not support' line is the smell.

**Options.**

- One shared typedef header util/Int128.hpp (chosen, one new 6-line file)
- Reuse PhaseLockInt128 from camera/FramePhaseLock.hpp (no new file, but TakeSlots.hpp is 'std only' and would pull in the phase lock)
- Put the same typedef in each of the two headers under one guard (no new file, two copies)
- Replace __int128 by a mulDiv helper with 64-bit pieces (also builds on 32-bit ARM, much larger change)

**Chosen, and why.** The shared header, because the plan asked for one typedef used by both. A typedef is just another name for a type; __extension__ tells GCC and Clang that the use of a non-standard extension is on purpose. RecordingClock.hpp includes it by relative path because the ProRes and H.264 plugins are compiled without -I src. Given up: 32-bit ARM still cannot build (as before, FramePhaseLock.hpp has the same limit).

**After.**

```
src/util/Int128.hpp:
  namespace apertar {
  __extension__ typedef __int128 Int128;
  }
RecordingClock.hpp: #include "../util/Int128.hpp"; const Int128 period = static_cast<Int128>(1000000) * periodDen;
TakeSlots.hpp: #include "Int128.hpp"
```

**Checked.** Ran here: gate both builds and 21 host tests (take_slots arithmetic included): warnings 166->1 and 169->4, none left in touched files. The first try failed in both builds because the plugins have no -I src; that is why the include is relative. Needs the Pi only for an aarch64 build, which uses the same compiler family.

**Rule.** A compiler extension is declared once, with __extension__, in one place; a warning count that grows by 165 hides the next real warning.


---

## C61. scripts: the pipeline config is exported only when APERTAR_PIPELINE_CONFIG names it

Apertar-Core `cc7203c`. Finding: CLIP-C-2. Reviewed by a second agent: not reviewed.

**What was there.**

scripts/start-apertar-core.sh:20-26@cinemate-port
  PIPELINE_CONFIG=/home/pi/Tuning-Files/pipeline/pisp-depth4.yaml
  if [[ -z "${LIBCAMERA_RPI_CONFIG_FILE:-}" && -f "$PIPELINE_CONFIG" ]]; then
      export LIBCAMERA_RPI_CONFIG_FILE="$PIPELINE_CONFIG"
  fi

**Why it is a problem.** The file's presence switched a behaviour on, for the primary and cam1 alike. Original start script (start-apertar-core.sh:16-18@upstream-1.6.0) exports a libcamera variable only from an APERTAR_* variable the operator set. A pisp file on a Pi 4 (vc4) is also the wrong target. Conventions R8: bench knobs are APERTAR_<AREA>_<KNOB>, default off.

**How to spot it.** In a start script or unit: any 'if [ -f /home/pi/... ]' that exports something. Ask: what does a camera that merely has this file do?

**Options.**

- Delete the block (stock safe, the rig loses depth 4 unless it exports the variable itself; trivial)
- APERTAR_PIPELINE_CONFIG opt-in, mapped like APERTAR_TUNING_FILE (chosen, 5 lines + README row)
- Keep the file test but also require a UI or hardware-file key (more code, no gain)

**Chosen, and why.** The opt-in variable, as the plan said. An env var set in a systemd drop-in is the Apertar way to switch a bench knob. Given up: the rig must add one Environment line to two units once.

**After.**

```
if [[ -n "${APERTAR_PIPELINE_CONFIG:-}" && -z "${LIBCAMERA_RPI_CONFIG_FILE:-}" ]]; then
    export LIBCAMERA_RPI_CONFIG_FILE="$APERTAR_PIPELINE_CONFIG"
fi
README: row APERTAR_PIPELINE_CONFIG=/path/file.yaml | off
```

**Checked.** Ran here: the script with a stand-in binary printing the env, fresh HOME: unset gives no variable, the variable gives the path, LIBCAMERA_RPI_CONFIG_FILE already set wins; gate clean. Needs the Pi: on the rig, systemctl edit apertar-core.service and apertar-core-cam1.service, add [Service] and Environment=APERTAR_PIPELINE_CONFIG=/home/pi/Tuning-Files/pipeline/pisp-depth4.yaml, restart; LIBCAMERA_LOG_LEVELS=RPI:DEBUG shows the config being read.

**Rule.** A libcamera variable is exported from an APERTAR_ variable the operator set, never from the presence of a file.


---

## C62. core: the socket get_state no longer carries the ui object

Apertar-Core `332bde9`. Finding: CLIP-C-3. Reviewed by a second agent: not reviewed.

**What was there.**

src/ApertarCoreApp.cpp:14204@cinemate-port (get_state, after settingsBody)
  << ",\"ui\":{" << dualSensorUiStateJson(uiState) << "}"
  << cam1StateMembers(cam1Client_, uiState, camera_.isRecording());

**Why it is a problem.** Original get_state is flat: status keys + settingsBody; UI.conf values live in the ui group of /api/state only (conventions CMD-11, CMD-8, CMD-9; /api/state at ApertarCoreApp.cpp:7965@upstream-1.6.0). A flat-line client saw a nested shape on a stock camera for fields no one reads.

**How to spot it.** grep -n '\\"ui\\"' src/ApertarCoreApp.cpp: a ui object outside the /api/state builder. Then grep the readers (ui-work, tools, the WebUI page) for the keys before deleting.

**Options.**

- Drop ui from get_state, keep it in /api/state (chosen, one line)
- Keep it only when cam1 is configured (still a shape difference on dual rigs, nothing reads it)
- Keep it and document it (a protocol field for no reader)

**Chosen, and why.** Drop it. Grep of /home/user/wt/ui-work (src, qml), the WebUI page and /home/user/apertar-kb/working/tools: every reader of dual_sensor_enabled, preview_source and friends uses /api/state (web_state() in longtakes.py says 'not in get_state'). The relay reads the secondary's get_state only by key (state, recording, sensor, resolution..clip_merge_env_off, fps_phase_lock_locked), none inside ui. Given up: nothing in behaviour. A reader of the socket that wants them uses /api/state.

**After.**

```
             << ",\"media_alive\":" << ...
             << clipMergeStateJson()
             << "," << settingsBody(camera_.settings())
             << cam1StateMembers(cam1Client_, uiState, camera_.isRecording());
(comments naming get_state beside dualSensorUiStateJson and the /api/state cam1 line updated)
```

**Checked.** Ran here: Core --simulate, get_state over the socket and /api/command: no ui, no cam1 key; /api/state has ui.dual_sensor_enabled and preview_source; smoke_core.sh + shape_subset.py: every base field present with the same type; gate clean (the one warning is convertPlanarYuv420ToRgb, also in 1.6.0). Needs the Pi with cam1: apertar-cmd '{"cmd":"get_state","id":1}' still shows "cam1":{...} and the touch UI's cam1 view works.

**Rule.** get_state is flat status plus camera settings; grouped UI values belong to /api/state.


---

## C63. core: time_left_percent is out of 2 hours again unless a second camera records

Apertar-Core `1ceda63`. Finding: CLIP-C-8. Reviewed by a second agent: not reviewed.

**What was there.**

src/ApertarCoreApp.cpp:9628-9640@clip-split (0902ac5)
  cardRecordMinutes = mediaTotalBytes / estimatedBytesPerSecond / 60.0;
  timeLeftPercent = clamp(recordTimeLeftMinutes / cardRecordMinutes * 100, 0, 100);
  time_left_label = timeLeftEstimateLabel(settings, cardRecordMinutes)  // '<format> estimate (card: 2 h 10 min)'

**Why it is a problem.** 1.6.0 (ApertarCoreApp.cpp:7817@upstream-1.6.0): timeLeftPercent = clamp(recordTimeLeftMinutes / 120.0 * 100.0, 0, 100) and time_left_label 'Current format estimate' (:7926). A field keeps its 1.6.0 meaning on a stock camera (campaign rule 1, 3).

**How to spot it.** Diff a published numeric field against upstream: grep the key in core-upstream and compare the expression, not only the type. A constant that became a variable is the smell.

**Options.**

- Card-wide scale only when the second camera is in the take set, 1.6.0 otherwise (chosen, about 10 lines)
- A UI.conf setting for the card scale, default off (keeps Patrik's choice on his single-sensor rig; a new setting, command and WebUI row)
- New field time_left_card_percent beside the old one (the finding's fallback; a new field)
- Keep as is (changes a stock camera)

**Chosen, and why.** The first option, as the lead's item says. A local bool secondCameraRecords is set where the code already asks which cameras record. Given up: Patrik's card-wide bar on a one-sensor rig; if he wants it there, option 2 or 3 is the way and needs his decision.

**After.**

```
bool secondCameraRecords = false;   // set where record_cameras is read: both or cam1
timeLeftPercent = !secondCameraRecords ? clamp(minutes / 120.0 * 100.0) : clamp(minutes / cardRecordMinutes * 100.0)
time_left_label: secondCameraRecords ? timeLeftEstimateLabel(settings, cardRecordMinutes) : "Current format estimate"
```

**Checked.** Ran here: Core --simulate, /api/state system.time_left_label is 'Current format estimate'; the sim has no mounted card, so time_left_percent is null and the arithmetic itself was not exercised; gate clean. Needs the camera: one-sensor rig with a card: curl -s :8000/api/state | python3 -c 'import sys,json;s=json.load(sys.stdin)["system"];print(s["time_left_percent"],s["record_time_left_minutes"])' gives minutes/1.2 capped at 100; dual rig, record_cameras both: card-wide percent and '(card: ...)' label.

**Rule.** A published value keeps its 1.6.0 formula on a stock camera; a new scale starts only where the new feature is on.


---

## C64. core: the relay's forward queue is capped and a signal ends the secondary's sensor wait

Apertar-Core `aac5980`. Finding: CLIP-C-14. Reviewed by a second agent: not reviewed.

**What was there.**

src/ipc/ControlClient.cpp:233-262@clip-split
  queue_.push_back(std::move(forward));   // no limit while linked
  if (pending_++ == 0) busySinceMs_ = nowMs();
src/main.cpp:150@clip-split
  secondaryHasSensor({}, options.camera, ..., 20000, 500, &why)   // sleep_for loop, no stop

**Why it is a problem.** A bounded queue is the usual rule for a producer faster than its consumer; the knob is the producer, a stuck cam1 the consumer. Original start path ends waits at a signal (signal pipe, main.cpp@upstream-1.6.0 uses no long waits) and the port's own waitForPrimaryIdle takes a stop lambda (src/ipc/PrimaryWait.hpp:130). The sensor wait was the one wait that did not.

**How to spot it.** grep -n 'push_back' on any queue_ guarded by a mutex: where is the limit? grep -n 'sleep_for' in loops reached before the signal thread starts: does a signal end it?

**Options.**

- Coalesce the last same setter and cap at 64, dropping the oldest plain forward (chosen)
- Cap only: refuse the new forward when full (the caller would say 'CAM1 is offline.', wrong)
- Coalesce anywhere in the queue (can reorder dependent setters such as fps and resolution)

**Chosen, and why.** Coalesce only with the last entry so the order of different setters never changes; a hard cap of 64 drops the oldest forward that nobody waits for. A dropped forward is the same case as a forward with no link: the 1 Hz compare and resync bring cam1 back to the primary's settings when both are idle. The stop callback is a std::function (a callable object) passed down as an optional last parameter, so the callers and tests that pass nothing behave as before. Given up: a lost step is only corrected at the next idle compare.

**After.**

```
if (origin == Origin::Forward && !reply && !queue_.empty()) { Forward &last = queue_.back(); if (same kind, origin, name, keys, no reply) { last.fields = fields; return true; } }
if (queue_.size() >= kMaxQueued) erase the first Setter/Forward/no-reply entry; --pending_;
waitForSensorSubdev(root, node, timeoutMs, pollMs, stop)  // stop(ms) waits and returns true at a signal
main.cpp: secondaryHasSensor(..., &why, [&](int ms){ pollfd stop{signalPipe[0], POLLIN, 0}; return ::poll(&stop, 1, ms) > 0; })
```

**Checked.** Ran here: a throwaway harness (not committed) with a silent cam1 socket: 1000 set_iso forwards leave pending 2, 1000 alternating setters stop at 65; waitForSensorSubdev with a stop callback returns at the first true, without one it waits as before; gate clean. Needs the Pi: config.txt naming cam1, no sensor fitted, start apertar-core-cam1 then systemctl stop apertar-core-cam1 within the 20 s: it returns at once and logs 'stopped by a signal while waiting for a sensor'.

**Rule.** Every queue has a limit and every wait has a stop; the knob and the signal are the two producers you do not control.


---

## C65. core: the relay thread sleeps until its next tick while there is no cam1 link

Apertar-Core `d4fd79a`. Finding: CLIP-C-10. Reviewed by a second agent: not reviewed.

**What was there.**

src/ipc/ControlClient.cpp:272-285@clip-split
  while (running_) { tick when due; ioStep(kIoStepMs /*100*/); watchTake(); ... }

**Why it is a problem.** A thread that has nothing to do should not wake. Original Apertar has no relay; its threads are started when needed and block on a condition variable or a long timeout (CMD-19, CMD-21). 10 wake-ups a second forever is cost for a camera that never turns the feature on.

**How to spot it.** strace -f -c -e trace=poll,ppoll,futex on an idle Core; or grep for poll/wait_for with a small constant in a loop that runs unconditionally.

**Options.**

- Poll timeout = time to the next tick while unlinked (chosen, 2 lines)
- Start the client only while the Dual sensor switch is on (finding option a; needs start/stop from the 1 Hz loop, the switch is read inside the client today: M)
- Return early in noteRelayEvent when cam1 is not configured (finding option b; separate, per-event cost, not done)

**Chosen, and why.** The first. poll() is the system call that waits on file descriptors with a timeout; the wake pipe is how other threads cut the wait short. Stop, enqueue, reads and takes need a link, so with no link only the tick has work. Given up: the thread still exists and wakes once a second (and stats UI.conf in tick); option 2 would remove that and is left to the lead.

**After.**

```
ioStep(fd_ < 0 ? static_cast<int>(std::max<int64_t>(1, nextTickMs_ - nowMs())) : kIoStepMs);
```

**Checked.** Ran here: a harness with an unlinked client under strace -c: 5 poll calls in 5 s (about 50 before); the silent-cam1 harness still links and forwards; gate clean. Needs the Pi: dual rig, journalctl -u apertar-core | grep 'cam1 linked' shows the link within about a second of cam1 starting; one-sensor rig: strace -f -c -p $(pidof apertar-core) -e trace=poll shows the relay thread at 1 per second.

**Rule.** An idle thread waits for its next deadline, not for a fixed short step.


---

## U14. ui: remaining time counts cam0 after cam1 goes; rate sum is in the bridge

Apertar-UI `9a66b24`. Finding: CLIP-U-5. Reviewed by a second agent: not reviewed.

**What was there.** src/main.cpp@clip-split: auto syncMediaRates = [&]() { recordCameras = bridge.recordCameras(); cam1InTake = cam1Present && (cam1|both); cam0InTake = recordCameras != cam1 && != none; ... 25 more lines parsing cam1Settings, resolution(), rawBitDepth() ... mediaBridge.setCameraRates(...) }; five QObject::connect(..., syncMediaRates). ApertarControlBridge::clearCam1State cleared every cam1 field except m_recordCameras.

**Why it is a problem.** Core sends record_cameras only while a cam1 exists, so a stale 'cam1' or 'none' stays after an unplug and cam0InTake stays false: REMAINING is 0 on one sensor. Apertar 1.6.0 main() only wires with connect and setters (UIC-1, main.cpp:374-396@upstream-1.6.0) and derived numbers live in the bridge that owns the inputs (UIC-4, UIC-11).

**How to spot it.** grep -n 'auto .* = \[&\]' src/main.cpp: any lambda longer than a few lines in main() is logic in the wrong place. Ask of every 'clear...State' function: does it reset every field the apply... function sets?

**Options.**

- Reset record_cameras and move the computation into the bridge, one signal (chosen, S)
- Only reset record_cameras and leave the lambda (fixes the bug, leaves logic in main.cpp)
- New cam1SizeScale Q_PROPERTY plus a setter on MediaStatusBridge (more API for four numbers that travel together)

**Chosen, and why.** The first. A Qt signal can carry several arguments, so one signal cameraRatesChanged(bool,bool,double,double) matches the existing setter signature and main() needs one connect. The sums are unchanged; the cam1 resolution parse stays as it was (CLIP-U-2 may share it later).

**After.**

```
connect(&apertarControlBridge, &ApertarControlBridge::cameraRatesChanged, &mediaBridge, &MediaStatusBridge::setCameraRates);
// bridge: updateCameraRates() runs after record_cameras, cam1 state, resolution and raw bit depth change
clearCam1State(): m_recordCameras.clear(); emit recordCamerasChanged() if it had a value; updateCameraRates();
```

**Checked.** Gate passes, 0 warnings. Nothing can run a second sensor here. Needs the Pi with two sensors: set record cam1, unplug cam1 (journalctl -u apertar-ui | grep 'cam1: gone'), REMAINING must still count from cam0.

**Rule.** A clear function resets everything its apply function sets; main() wires, the bridge computes.


---

## U15. qml: Split Long Takes and Merge Split Clips follow the Settings page style

Apertar-UI `98937b8`. Finding: CLIP-U-3. Reviewed by a second agent: not reviewed.

**What was there.** qml/SettingsPage.qml:5396-5523@lane/ui-tc before: Text { text: "Merge Split Clips"; color: "white"; font.pixelSize: 14 } ; Row { ActionTile { label: "On"; tone: enabled ? "accent" : "default"; onClicked: apertarControlBridge.applyClipMerge(true) } ActionTile { label: "Off" ... } } ; Text { color: "#9aa5b1"; font.pixelSize: 12 } ; Repeater { model: ... ? 2 : 0 ; clipRow: index === 0 } ; label "Split Long Takes (set by APERTAR_CDNG_FRAMES_PER_FOLDER)"; void applyFramesPerFolder / applyClipMerge

**Why it is a problem.** Text sizes did not scale with the layout flags (QML-13), no Inter font or NativeRendering (QML-17), off-palette greys (QML-16), on/off as two tiles where the page uses TogglePill (SettingsPage.qml:5157@upstream-style rows), failures never shown because the invokables were void (UIC-9, QML-8), nothing locked during a take (QML-25).

**How to spot it.** grep -n 'pixelSize: [0-9]*$' qml/*.qml: a bare number with no ternary is a missed layout flag. grep -n 'font.family' near every Text. Ask of each Q_INVOKABLE void apply...: where does the user see a failure?

**Options.**

- Rebuild the rows with the card's own tokens, bool invokables and a copy of an existing error popup (chosen, M)
- Reuse the mount-error popup with a variable title (smaller, but misnames that popup and touches its code)
- Show lastError as a Text in the card (no popup, differs from every other failure on the page)

**Chosen, and why.** The first. Every failure on this page opens its own popup, so a Media Setting Failed popup copies the thermal one. Core allows both commands during a take (frames_per_folder applies to the next take) but the page locks format-like controls then (QML-25), so both rows are locked as asked. Given up: 75 more lines in an already big file, because the page has no generic error popup.

**After.**

```
TogglePill { id: clipMergeToggle; checked: apertarControlBridge.clipMergeEnabled; enabled: !recording && !clipMergeEnvOff; onToggled: function(value) { root.executeApplyClipMerge(value) } }
function executeApplyClipMerge(enabled) { if (!apertarControlBridge.applyClipMerge(enabled)) { mediaSettingErrorText = lastError...; mediaSettingErrorOpen = true } }
```

**Checked.** Gate passes, 0 warnings (QML compiled ahead of time). Nothing visible here. Needs the owner on HDMI with a mouse: Settings, System, Media; both rows match Mount Drive; during a take both dim and ignore input; with Core stopped, a toggle shows the popup. Also check the 720x720 layout.

**Rule.** A new settings row copies the card's tokens and shows its failure the way the page does; a void apply function hides errors.



---

## C66 and U16. Mode names follow Apertar 1.6.0, "Clear HDR" written in full

Apertar-Core `web, camera: resolution and Mode Ladder names follow Apertar 1.6.0`, Apertar-UI `qml: the Log note says "outside Clear HDR" instead of "in SDR"`. Asked for by Patrik (2026-11-21): resolution buttons and the Mode Ladder info in the original Apertar naming, and "Clear HDR" exactly so. Made by the lead.

**What was there.** The port named modes in its own words: a WebUI pill "4K UHD", the IMX585 family "Full HD binned", and in the Mode Ladder and Core's `ladder_text` the codes "ClearHDR16" and "SDR12", plus "SDR" in many labels ("4K SDR", "2K SDR binned").

**Why it is a problem.** Apertar 1.6.0 names a mode by its size and its bit depth: "4K", "Full HD", "12-bit" (`imx585BaseResolutionOptions`, `rawBitDepthOptions` in `WebControlPage.cpp@upstream-1.6.0`). "SDR" appears nowhere in 1.6.0's screens. Two vocabularies for the same mode make an operator wonder whether they are two things.

**How to spot it.** Grep the visible strings, not the code: `grep -o '"[^"]*\bSDR\b[^"]*"'` and `grep -o 'ClearHDR'` in the page and the QML, then compare the labels with 1.6.0's option lists.

**Chosen, and why.** The plain mode has no class word at all, as in 1.6.0; only "Clear HDR" and "N×N binned" are named. Where a line joined the class name with " · ", it now skips the empty one, so no line shows a dangling dot. The touch UI already used 1.6.0's labels ("Full HD", "2K", "4K", "4K Clear HDR"); only its Log note said "in SDR".

**Checked.** Both Core builds and the host tests; the UI build; the WebUI loads in headless Chromium with no page errors; `ladderClassText` gives "Clear HDR 16-bit" and "12-bit 2.39:1"; `/api/state` `ladder_text` reads "3840×2160 · 12-bit · Uncompressed (ladder off)". On the camera: read the resolution pills and the Mode Ladder card.

**Rule.** A new mode or feature gets the words the original screens already use for the same thing; a new word only for a new thing.

---

## C67. core: Stop on Dropped Frame ends a take at its first dropped frame

Apertar-Core `affe7da`. Finding: drop 1. Reviewed by a second agent: not reviewed.

**What was there.** New feature, no earlier code. 1.6.0 only latches drops: src/util/RecordingDropWarning.hpp markDropped() -> changed_(true) -> a recording_health event. Nothing stops the take.

**Why it is a problem.** Owner rule DB-59: stop a test at the first drop. Shape follows conventions R2 (camera setting end to end: Types, load, save, three serialisers, setter, command, help) and the buffer safety stop (App::runBufferSafetyStop) for stopping from a worker thread.

**How to spot it.** Any feature that must stop a take from a worker thread: grep dispatchHardwareInputCommand and the safetyStopHook. Rule of thumb: if the code path holds a writer or queue lock, it may only set a flag.

**Options.**

- Call stopRecording from the drop callback: deadlock risk, the callback runs on the writer thread under queue locks. Rejected.
- Poll recordingHasDroppedFrames in runBufferEvents (250 ms): no new hook, but a late stop and logic in an event thread.
- Lock-free hook in CameraController plus a flag on the existing safety-stop thread: instant, one thread, same record_stop path. Chosen.

**Chosen, and why.** Third option. CameraController gets setDroppedFrameHook (a std::function, set once before any take); the App hook checks an atomic mirror of the setting (like mediaTrimSetting_) and sets droppedFrameStopPending_. runBufferSafetyStop handles it first and sends record_stop through dispatchHardwareInputCommand. Given up: no recording_error is set, because the stop is clean like the buffer stop and the WebUI would show 'Recording stopped: Recording stopped'. The log line and the existing recording_has_dropped_frames field tell it.

**After.**

```
camera_.setDroppedFrameHook([this] { if (!stopOnDroppedFrameSetting_.load(std::memory_order_acquire)) return; droppedFrameStopPending_.store(true, std::memory_order_release); bufferSafetyStopCv_.notify_one(); });
if (droppedFrameStopPending_.exchange(false) && camera_.isRecording()) { std::cerr << "ApertarCore recording: Recording stopped: a frame was dropped.\n"; ... record_stop ... }
```

**Checked.** Built lc and nolc, 21 host tests. Simulate: command refused without enabled and during a take, true shows in /api/state and help, camera_settings.conf has stop_on_dropped_frame=1, restart reads it back, smoke shape check passes. Simulate cannot drop frames. Pi: 4K Clear HDR 16-bit at 30 fps on the CM5 with the switch on; the take ends at the first drop; journalctl -u apertar-core | grep 'a frame was dropped'.

**Rule.** A worker thread that wants a take stopped only sets a flag; the app thread runs record_stop on the command path.


---

## C68. web: Stop on Dropped Frame is an On/Off row in the Performance card

Apertar-Core `38c8875`. Finding: drop 2. Reviewed by a second agent: not reviewed.

**What was there.** New feature; no earlier code.

**Why it is a problem.** Conventions R3 step 12 / R2 step 12: a switch is a section.select-block with a pill-grid, filled by buildOptionButtons(..., toggleOptions, formatToggleLabel(!!snapshot.x), ...) that sends the command.

**How to spot it.** Copy the nearest row (settingsPreviewTdnOptions): one section in the HTML string, one buildOptionButtons call in renderSnapshot. No patch case is needed; the page re-reads state after a command.

**Options.**

- Row in the Performance card next to Merge split clips (chosen): next to other take options, no new card.
- New 'Recording' card: new layer, more CSS and ids.
- Row in Recording format card: that card is dual-sensor tied to resolution; the switch is per Core.

**Chosen, and why.** First option. No data-dual-tie, like the media trim row. Given up: a patch case in applyCommandSnapshotPatch; preview_tdn does not have one either and the state refresh updates the pills.

**After.**

```
buildOptionButtons("settingsStopOnDroppedFrameOptions", toggleOptions, formatToggleLabel(!!snapshot.stop_on_dropped_frame), async (value) => { try { await sendCommand({ cmd: "set_stop_on_dropped_frame", enabled: value === "On" ? "true" : "false" }); } catch (error) { showToast(error.message, true); } });
```

**Checked.** Playwright against --simulate: row present with Off active, click On, pill turns On, /api/state true, no page errors. Nothing needs the camera.

**Rule.** A WebUI switch is one select-block plus one buildOptionButtons call, copied from its neighbour.


---

## U17. qml: Stop on Dropped Frame is a toggle row in the Media settings

Apertar-UI `67d1a41`. Finding: drop 3. Reviewed by a second agent: not reviewed.

**What was there.** New feature. Separate bug on the branch tip: qml/SettingsPage.qml (98937b8) copied the thermal error popup for the media error popup and kept 'id: thermalApplyErrorCloseArea' and 'onClicked: root.thermalApplyErrorOpen = false'.

**Why it is a problem.** Row shape copies the Merge Split Clips row (SettingsPage.qml, TogglePill + executeApplyClipMerge). Bridge shape copies applyClearHdr and setClearHdrValue (conventions R4). QML needs unique ids in one component; a duplicate stops the whole page loading, and the OK button would also have closed the wrong popup.

**How to spot it.** After copy-pasting a QML block, grep the ids: grep -o 'id: [A-Za-z0-9]*' file | sort | uniq -d. Run the UI once offscreen; the gate only compiles.

**Options.**

- Fix the id inside this commit (chosen): the row cannot be seen otherwise.
- Separate fix commit: cleaner history but breaks one commit per item.
- Leave it: Settings stays broken.

**Chosen, and why.** First option; renamed to mediaSettingErrorCloseArea and closed mediaSettingErrorOpen. Lead may want to move it into its own commit or into 98937b8.

**After.**

```
TogglePill { id: stopOnDroppedFrameToggle; checked: apertarControlBridge ? apertarControlBridge.stopOnDroppedFrame : false; enabled: !!apertarControlBridge && !apertarControlBridge.recording; onToggled: function(value) { root.executeApplyStopOnDroppedFrame(value) } }
```

**Checked.** check_ui.sh passes. Offscreen UI against --simulate Core: SettingsPage loads; the run then stops at ClipPlayerPage (retainWhileLoading needs Qt 6.5, host has 6.4), so the row was not seen. Pi: Settings, Media, flip the row, grep stop_on_dropped_frame ~/.config/apertar-core/camera_settings.conf; the pill is greyed during a take.

**Rule.** Copy a block, then rename its ids and handlers; run the UI once, a compile does not catch duplicate ids.


---

## C69. core, web: the Boot Config card saves through /api/command

Apertar-Core `4e8e08f`. Finding: boot 1. Reviewed by a second agent: not reviewed.

**What was there.**

src/ApertarCoreApp.cpp:9783@cinemate-port: if (request.method == "POST" && request.path == "/api/boot-config") { ... payload.insert(brace + 1, "\"cmd\":\"set_boot_config\","); ... const BootConfigReply reply = bootConfigSet(parsed.command, revision, request.headers.count("origin") > 0); response.status = reply.status; ... }
src/ApertarCoreApp.cpp:3661@cinemate-port: std::mutex &bootConfigMutex() { static std::mutex mutex; return mutex; }  (taken by bootConfigSet, bootConfigGet and applyFanMode)
src/web/WebControlPage.cpp@cinemate-port: bootConfigPost(): fetch("/api/boot-config", { method: "POST", headers: { "X-Apertar-Revision": revision } }) and result.httpStatus / result.code

**Why it is a problem.** Original Apertar has one door for a change: POST /api/command -> handleWebCommand -> handleCommand under commandMutex_ (App handleWebCommand@upstream-1.6.0; conventions CMD rules), with okReply/errorReply and one sentence. The fan mode writes config.txt the same way (set_fan_mode in handleCommand). A file the browser only reads gets a GET route (GET /api/config). The port added a second write door with its own lock, its own header and an 'is it a browser' rule, so the same command behaved differently on the socket and on the web.

**How to spot it.** grep -n 'request.path == "/api/' src/ApertarCoreApp.cpp and ask for each POST route: is this a setting? A setting belongs in handleCommand. Also grep -n 'static std::mutex' for a second lock around data the command lock already covers. A reply struct with an int status is a smell: original replies are strings with HTTP 200.

**Options.**

- Delete the POST route, keep the command, send from the page with sendCommand (chosen; about -90 / +40 lines).
- Keep the route but make it call handleCommand (keeps two doors; the header and codes would still need a home).
- Leave it and document it (no change; the next developer meets a second door).

**Chosen, and why.** The first option, as the plan says. commandMutex_ already covers the fan mode and set_boot_config, so bootConfigMutex() had nothing left to guard; the read takes no lock, as GET /api/config. Given up: the HTTP status codes 400/403/409/500 on a refusal (the page never needed them) and the revision header. bootConfigPost keeps its { ok, error } contract on top of sendCommand so reviewBootConfig and saveBootConfig change very little. The 400/409 'code' members stay in the reply body until the refusals are made one sentence (item boot 9-refusals).

**After.**

```
std::string bootConfigGet(int id) { const bootconf::Facts facts = bootConfigFacts(); return okReply(id, "\"boot_config\":" + bootConfigJson(readTextFileRaw(bootConfigPath()), facts)); }
std::string bootConfigSet(const ControlCommand &command) { const std::optional<std::string> revision = command.string("revision"); ... }
handleCommand: if (command.name == "set_boot_config") return bootConfigSet(command);
WCP: async function bootConfigPost(body, revision) { const payload = Object.assign({ cmd: "set_boot_config" }, body); if (revision) payload.revision = revision; try { return await sendCommand(payload); } catch (error) { return { ok: false, error: ... }; } }
```

**Checked.** Ran here: the gate (both builds, 21 host tests); --simulate with APERTAR_BOOT_CONFIG on a copy of the test fixture: POST /api/boot-config -> 404 Not found, set_boot_config over /api/command with dry_run, with a stale revision (refused with the sentence) and with the right revision (one line changes, .apertar.bak left); Chromium: change the cam0 sensor, review, Save Only: the page posts set_boot_config to /api/command and reads GET /api/boot-config after; smoke_core shape diff clean. Needs the Pi: Save from the card on the CM5, reboot, journalctl -u apertar-core | grep 'boot config'.

**Rule.** A setting has one door: a command in handleCommand under commandMutex_; a route is for reading a file or serving a page.


---

## C70. core, web: config.txt text editing is a switch, off by default

Apertar-Core `158a28f`. Finding: boot 3+4 (variant). Reviewed by a second agent: not reviewed.

**What was there.**

src/ApertarCoreApp.cpp bootConfigSet@cinemate-port: const std::optional<std::string> edited = command.string("text"); if (edited) { textProblem(*edited) ... } bootconf::applyRequest(edited ? *edited : text, request, facts);
The text went to writeBootConfigText and from there to the root helper, whatever the caller. WCP: the Edit file button was always shown.

**Why it is a problem.** A text door lets any client that can reach the WebUI put any bytes into config.txt as root (kernel=, cmdline=, os_prefix=; save 1 writes a file, save 2 copies it to .apertar.bak and points cmdline= at it). Original Apertar's browser-written files are never a boot file (GET/POST /api/config writes the hardware file as pi), and the fan mode writes one generated block. The owner's own rule for what the browser may write is the ssh-only switch (APERTAR_SCRIPT_PATHS=ssh, HardwareConfigStore.cpp:346@lane-core3, fix log C29). Rule 1 of the campaign: a stock camera has no such door until the operator turns it on.

**How to spot it.** Ask of every field a command accepts: can a LAN client make Core write bytes it did not generate? grep -n 'command.string("text")\|body.text' for whole-file fields. Then ask who may set the switch: only a process environment (ssh) is out of the LAN client's reach.

**Options.**

- Delete Edit file and text (the plan; -170 lines, but the owner keeps the feature, DA-104).
- A switch read from Core's environment, off by default (chosen; +12 lines).
- A deny list of dangerous keys (never complete: cmdline= can be reached in two saves).
- A hardware-file key (the browser can write that file, so the switch would be in the attacker's reach).

**Chosen, and why.** The environment switch, as the owner's recorded rule for the ssh-only script paths. bootConfigTextEnabled() compares the variable to 'on' each call, like the script-path check. The refusal is written with errorReply (the target shape) and sits before the file is read. The page learns the state from text_editable in GET /api/boot-config and hides the button with the existing .hidden class. Given up: nothing for the owner (set the variable and the card is as it was); a stock camera loses Edit file, which 1.6.0 never had.

**After.**

```
bool bootConfigTextEnabled() { const char *value = std::getenv("APERTAR_BOOT_CONFIG_TEXT"); return value && std::string(value) == "on"; }
bootConfigSet: if (command.string("text") && !bootConfigTextEnabled()) return errorReply(command.id, "config.txt is edited as text over ssh, not here.");
bootConfigJson: ",\"text_editable\":" + (bootConfigTextEnabled() ? "true" : "false")
WCP renderBootConfig: document.getElementById("editBootConfigButton").classList.toggle("hidden", !(payload && payload.text_editable));
```

**Checked.** Ran here: the gate; --simulate on a fixture copy. Switch unset: GET shows text_editable:false, set_boot_config text with and without dry_run gives the sentence and the file is unchanged, Chromium shows no Edit file and a sensor change still reviews and saves. Switch on (APERTAR_BOOT_CONFIG_TEXT=on): text_editable:true, a text dry_run is answered, Edit file is shown. The host test cannot see this switch (it lives in App, the engine is pure); the engine's text checks are unchanged. Needs the Pi: nothing new; to see Edit file there put Environment=APERTAR_BOOT_CONFIG_TEXT=on in a systemd drop-in and restart Core.

**Rule.** A door that lets the browser hand Core bytes to install as root is opened by the operator in Core's environment, never by a field in the request.


---

## C71. core, web: a display change on the Boot Config card asks with window.confirm

Apertar-Core `5bd566d`. Finding: boot 5 (variant). Reviewed by a second agent: not reviewed.

**What was there.**

src/web/WebControlPage.cpp reviewBootConfig@cinemate-port: gate = document.createElement("input"); gate.type = "checkbox"; row.appendChild(document.createTextNode(" Change the display anyway")); ... const syncGate = () => { const blocked = changes.length === 0 || (gate && !gate.checked); ... };
src/ApertarCoreApp.cpp@cinemate-port: drmConnectorsJson() read /sys/class/drm; its result went into the GET, the dry run and the confirm_display refusal as "drm":[...].

**Why it is a problem.** Original Apertar confirms a system action in the page: if (!window.confirm("Restart the Apertar system now?")) return; then sendCommand({ cmd: "restart_system" }) (WCP:11325@upstream-1.6.0). The port built a second confirmation vocabulary (a checkbox, a connector summary, a drm list in every reply). The DRM list is not proof of a panel (a DPI overlay shows 'connected' with no panel), so it added bytes and code without deciding anything.

**How to spot it.** grep -n 'createElement("input")' near a Save button: a checkbox that gates a save is a confirm in disguise. Ask: does upstream confirm this kind of action with window.confirm? Then ask whether the owner recorded a rule that Core itself must refuse (DA-81): if yes, the page asks and Core still checks.

**Options.**

- Plan: page window.confirm, Core drops confirm_display (a script can then change the display; breaks the owner's DA-81).
- Page window.confirm, Core keeps the confirm_display refusal (chosen; about -45 / +6 lines).
- Keep the checkbox (no change; the port's own confirmation vocabulary stays).

**Chosen, and why.** The second option, as the audit says: the page matches upstream's way of asking, and Core's guard stays, so 'Do not change the display on a rig where you cannot reach the camera' still holds for the socket and for curl. The refusal sentence is untouched (the refusals-as-one-sentence commit rewords it later). Given up: the connector summary line; the diff notes about the DPI panel stay in the review box.

**After.**

```
async function saveBootConfig(reboot) { ...
  const displayChanged = !!(review && review.display_changed);
  if (displayChanged && !window.confirm("Change the display overlays and save? A DPI panel that is the camera's only screen stays dark without them.")) return;
  ... bootConfigPost(bootConfigRequestBody({ confirm_display: displayChanged }), bootConfig.payload.revision);
review box: saveReboot.disabled = changes.length === 0; saveOnly.disabled = changes.length === 0;
Core: if (result.displayChanged && !confirmDisplay) return errorReplyBody(... "Send confirm_display=true to save anyway.", "\"code\":\"confirm_display\"");
```

**Checked.** Ran here: the gate; --simulate on a fixture copy: set_boot_config display=waveshare4 without confirm_display refused with the sentence, file unchanged; dry run display_changed:true with no drm member; Chromium with page.on('dialog'): Display -> Waveshare, Save Only: exactly one confirm with the plan's text; dismiss -> no save request, file unchanged; accept -> save with confirm_display:true, the three overlay lines uncommented. Needs the Pi: nothing; no display is switched in the test (his DPI overlays are commented out, so the guard cannot fire on his CM5).

**Rule.** Ask in the page the way upstream asks (window.confirm); keep a guard in Core when the owner decided a script must not skip it.


---

## C72. core: config.txt is read by GET /api/boot-config only

Apertar-Core `71cbcc9`. Finding: boot 7. Reviewed by a second agent: not reviewed.

**What was there.**

src/ApertarCoreApp.cpp@cinemate-port: if (command.name == "get_boot_config") return bootConfigGet(command.id).body;
The commands reply listed ..."set_fan_mode","get_boot_config","set_boot_config"... and README said 'Socket commands: get_boot_config, and set_boot_config with ...'.

**Why it is a problem.** Original Apertar has get_state and get_media_test_state as its only get_ commands (handleCommand@upstream-1.6.0), and a file the browser shows is read by a GET route with no command twin (GET /api/config, App:7168@upstream-1.6.0). A second way to read the same thing doubles the surface the next developer must keep in step, and nothing used it.

**How to spot it.** grep -n 'command.name == "get_' src/ApertarCoreApp.cpp and compare with upstream's two. For each one ask: who calls it? A grep over src, qml and the UI repo that finds only the README is a dead door.

**Options.**

- Delete the command (chosen; -4 lines).
- Keep it and document it (no change; one more get_ command than upstream, with a nested reply).
- Make it return the same text as GET but as a flat reply (more code for a reader nobody has).

**Chosen, and why.** Delete it. The KB handoff once checked the card with printf '{"cmd":"get_boot_config"}' | socat; that check becomes curl -s localhost:8000/api/boot-config. bootConfigGet lost its id parameter, since only the route calls it now. Given up: a socket-only reader of config.txt (none existed in practice).

**After.**

```
std::string bootConfigGet() { const bootconf::Facts facts = bootConfigFacts(); return okReply(-1, "\"boot_config\":" + bootConfigJson(readTextFileRaw(bootConfigPath()), facts)); }
GET /api/boot-config: response.body = bootConfigGet();
handleCommand has only: if (command.name == "set_boot_config") return bootConfigSet(command);
```

**Checked.** Ran here: the gate; --simulate: get_boot_config over /api/command and over the socket answers 'Unknown command: get_boot_config'; GET /api/boot-config unchanged; smoke_core shape diff: every base field present with the same type. Needs the Pi: nothing.

**Rule.** A file the browser shows has one read (a GET route); a get_ command is for state every client needs.


---

## C73. core: the Boot Config card knows the board by its SoC string

Apertar-Core `5c51183`. Finding: boot 11. Reviewed by a second agent: not reviewed.

**What was there.**

src/hardware/BootConfigText.hpp:85-97@cinemate-port:
  std::replace(compatible.begin(), compatible.end(), '\0', ',');
  const std::string c = lower(compatible);
  if (contains(c, "bcm2712")) board.family = "pi5";
  else if (contains(c, "bcm2711")) board.family = "pi4"; ...
  board.detected = !board.family.empty();
  if (!board.detected) board.family = "pi5";
linkOptionsFor: if (board.family != "pi4" || !sensor.pi4MaxHz || option.hz <= sensor.pi4MaxHz)
bootConfigFacts read only /proc/device-tree/compatible.

**Why it is a problem.** recordingCapabilitiesFromCompatible splits the NUL-separated compatible list and compares each SoC string whole; the reader tries /sys/firmware/devicetree/base/compatible then /proc/device-tree/compatible (include/apertar/core/RecordingCapabilities.hpp:18-50@upstream-1.6.0, conventions PLT-3). Substring search matches text inside a longer name, and 'unknown means Pi 5' lets the card edit [pi5] lines on a board whose firmware ignores them, and hand Pi 5 link rates to a Pi 3.

**How to spot it.** grep -n 'contains(.*bcm\|std::replace(.*\\0' for substring searches on NUL-separated device-tree data. Ask of every 'if nothing matches, assume X' line: what runs on the boards that do not match? An unknown input should be refused or read-only, not mapped to the main board.

**Options.**

- Whole-entry match, unknown = read-only, cap on every non-Pi 5 board, dev fallback only with APERTAR_BOOT_CONFIG (chosen; about +30 / -15 lines).
- Keep substring search but unknown = read-only (still matches text inside other strings).
- Share the SoC walk with RecordingCapabilities.hpp (a new dependency of a pure header on an I/O-flavoured one; a bigger change).

**Chosen, and why.** The first option, as the plan says. The walk is the same loop as upstream's, so a reader of one understands the other; sharing code was not worth a new include in a pure engine header. boardFromDeviceTree takes a string_view. Only a dev host (no device tree, APERTAR_BOOT_CONFIG naming a copy) is read as a Pi 5, so a real Pi 1 or Zero stays read-only. Given up: the page note 'No Raspberry Pi device tree here' (it described the old fallback); the card on a dev host now says nothing about it. On the owner's CM5 nothing changes: bcm2712 -> pi5, no cap.

**After.**

```
while (!compatible.empty()) { const auto end = compatible.find('\0'); const auto soc = compatible.substr(0, end);
  if (soc == "brcm,bcm2712") board.family = "pi5"; else if (soc == "brcm,bcm2711") board.family = "pi4"; else if (soc == "brcm,bcm2837" || soc == "brcm,bcm2710") board.family = "pi3"; ... }
readState: if (!board.detected) state.problem = "This board is not one the Boot Config card knows. Edit config.txt by hand.";
linkOptionsFor: if (board.family == "pi5" || !sensor.slowBoardMaxHz || option.hz <= sensor.slowBoardMaxHz)
bootConfigFacts: if (compatible.empty() && bootConfigPath() != std::filesystem::path(kBootConfigPath)) compatible = std::string("brcm,bcm2712\0", 13);
```

**Checked.** Ran here: the gate; boot_config_test new cases (empty, Zero 2 W = pi3, bcm2835 unknown, 'vendor,not-brcm,bcm2712-x' unknown, unknown board read-only with [pi5] lines not applying and a request refused, IMX477 list 8 on Pi 5 / 1 on Pi 4 and Zero 2 W); --simulate: with APERTAR_BOOT_CONFIG the copy is a detected Pi 5 and editable; without it (no /boot/firmware/config.txt here) board.family is empty, detected false, the card read-only. Needs the Pi: on a Pi 4 with an IMX477 the list ends at 500 MHz; on the CM5 curl -s localhost:8000/api/boot-config must show board.family pi5, detected true; a Zero 2 W (pi3) if one is at hand: the card edits [all]/[pi3] lines (board-support T5).

**Rule.** Match device-tree strings whole, entry by entry; a board you do not know is refused, not mapped to the main board.


---

## C74. core: the Boot Config card leaves a sensor from include camera-selection.txt alone

Apertar-Core `5bbd67d`. Finding: boot 12. Reviewed by a second agent: not reviewed.

**What was there.**

src/hardware/BootConfigText.hpp lineFrom@cinemate-port:
  const size_t eq = s.find('=', pos);
  if (eq == std::string::npos || eq >= end) return line;   // a line without '=' has no key
So 'include camera-selection.txt' was invisible: the card showed no sensor, and a pick wrote a dtoverlay line next to what the include loads.

**Why it is a problem.** The stock image loads its sensor with 'include camera-selection.txt'; its own comment says to remove that line before uncommenting a dtoverlay. Original Apertar reads the camera-selection file first and calls it authoritative (UI src/DeviceInfoBridge.cpp:213-215@upstream-1.6.0). A second dtoverlay beside the include loads two sensors on one port, which is the kind of edit the read-back exists to prevent.

**How to spot it.** Run the engine on the stock image's config.txt and ask: which lines of the real file does the parser give no key? A line type the parser drops (include, initramfs, [gpio..] filters) is a line it cannot respect. Grep the shipped file for lines without '='.

**Options.**

- Read the include, keep the sensor rows read-only with one sentence (chosen; about +30 lines).
- Follow the include and read camera-selection.txt in the engine (a file read in a pure header; decision 5's larger option, for the owner).
- Refuse to edit anything while an include is active (also blocks buses and display for no reason).

**Chosen, and why.** The first option, as the plan says. lineFrom gives 'include' a key and takes the file name as its value; State::cameraProblem holds the sentence for the first active include in a section that applies. applyRequest refuses a sensor or link that differs from what the file says, so a page that sends the unchanged values still saves buses. Given up: switching sensors from the card on a file that has an include; the operator removes the include line first, as the image's comment says.

**After.**

```
lineFrom: if (s.compare(pos, 7, "include") == 0 && pos + 7 < end && blank(s[pos + 7])) { key = "include"; vb = pos + 7; } else { ...the '=' case... }
readState: else if (line.key == "include" && state.cameraProblem.empty()) state.cameraProblem = "config.txt includes " + line.value + ": the sensor comes from that file.";
applyRequest: if (!result.before.cameraProblem.empty() && key != current.sensor) return fail(result.before.cameraProblem);   (and the same for a changed link frequency)
stateJson: "camera_problem":"..."; WCP: select.disabled = ... || !!bootState.camera_problem;
```

**Checked.** Ran here: the gate; boot_config_test new cases (lineFrom, state, no-op request, bus change, sensor change refused on cam0 and cam1, commented include ignored, include under [pi4] counts on a Pi 4 only, JSON); --simulate on a fixture copy with an include line and the IMX585 line commented: Chromium shows both sensor selects disabled with the sentence, the I2S switch still enables Save; set_boot_config cam0_sensor=imx477 refused with the sentence. Needs the Pi: on a fresh Apertar 1.6.0 image: grep -n '^include' /boot/firmware/config.txt; cat /boot/firmware/camera-selection.txt (settles the premise: which section holds the include). Then cp /boot/firmware/config.txt /tmp/before.txt, pick IMX585 in the card, Save: refused with the include sentence; cmp /tmp/before.txt /boot/firmware/config.txt prints nothing. The owner's CM5 has the include removed, so its card is unchanged.

**Rule.** A parser that drops a line type cannot respect it: read every line kind the stock file ships, and make the card read-only where another file decides.


---

## C75. core: the Boot Config test covers re-enabling a commented IMX283 line

Apertar-Core `0292490`. Finding: boot 13. Reviewed by a second agent: not reviewed.

**What was there.** Plan: sensors() gains {"imx283", ...}. Code at the tip: src/hardware/BootConfigText.hpp sensors() already has {"imx283", "imx283", "OneInchEye (IMX283)", false, 720000000, 0, {360 MHz, 720 MHz}}; tools/boot_config_test.cpp checks it is offered. No test covered a commented imx283,always-on line.

**Why it is a problem.** DB-79: on the owner's rig keep always-on on the imx283 line. The engine reuses a commented sensor line of the same overlay in the board section (BootConfigText.hpp applyRequest, reuse loop), so always-on survives. The audit's caveat holds and is shown by a probe: the commented line must sit in the same section as the other sensor lines; one under [all] is not reused and a new plain line is added.

**How to spot it.** When a plan says a thing is missing, grep the name first (grep -n imx283 src/hardware/BootConfigText.hpp tools/boot_config_test.cpp). When an owner decision is about a byte-level result, look for a test that pins those bytes.

**Options.**

- Skip the commit as already done (leaves DB-79 untested).
- Add one test check, no code change (chosen; +12 lines).
- Make the engine reuse a commented line from any section (changes how firmware sections are respected; not asked for).

**Chosen, and why.** The test-only commit, because the audit asked for exactly that host test. Given up: nothing. If the owner's commented imx283 line is not in the same section as his imx585 line, the card writes a plain dtoverlay=imx283 line and always-on is lost; that is for him to check on the CM5.

**After.**

```
same_section.replace(..., cam0Line + "#dtoverlay=imx283,always-on\n");
Request q = same(s); q.sensors["cam1"] = "imx283";
check(r.ok && r.changes.size() == 1 && lineOf(r.text, 43) == "dtoverlay=imx283,always-on", ...);
```

**Checked.** Ran here: the gate (21 host tests); a probe: commented line in [pi5] reused with always-on kept; in [all] not reused, plain dtoverlay=imx283 added in [pi5]. Needs the Pi: with the imx283 driver installed, pick IMX283 on cam1, reboot, camera starts; grep -n imx283 /boot/firmware/config.txt shows the line in the same section as imx585.

**Rule.** Check a plan's 'missing' claim against the code before building it; pin an owner's byte-level decision with a test.


---

## C76. core: Boot Config refusals are one sentence

Apertar-Core `fa1dc5c`. Finding: boot 9-refusals. Reviewed by a second agent: not reviewed.

**What was there.**

src/ApertarCoreApp.cpp bootConfigSet@cinemate-port: return {409, errorReplyBody(command.id, "config.txt changed since the card loaded it ...", "\"code\":\"stale\",\"revision\":" + bootconf::jsonString(current))};
Others: "code":"invalid", "unreadable", "refused", "confirm_display", "permission", "write_failed".
errorReplyBody(int id, message, body) in the anonymous namespace.

**Why it is a problem.** Original Apertar has two reply builders only, okReply and errorReply (App:108-128@upstream-1.6.0), and every surface shows the refusal sentence as written (CMD-9, CMD-28, WEB-14). A second error vocabulary (code) makes each client learn it; here the page had stopped using it once the card sent set_boot_config through sendCommand, which hands over the sentence only.

**How to spot it.** grep -n 'errorReplyBody\|"code\\"' src/ApertarCoreApp.cpp. A helper with one theme's callers is a smell; after the last caller goes, delete it or the build warns about an unused function.

**Options.**

- Convert every refusal and delete errorReplyBody (chosen; about -25 lines).
- Keep the codes for scripts (a second vocabulary nobody reads).
- Leave errorReplyBody for the next user (unused-function warning).

**Chosen, and why.** The first option. The status codes went with the route in item boot 1, the display guard and its sentence stay as the owner decided, and the stale sentence already tells the operator to reload. Given up: the revision in the stale reply (the page re-reads it with GET /api/boot-config) and the machine codes.

**After.**

```
if (!bootConfigRequestFrom(command, &request, &error)) return errorReply(command.id, error);
if (revision && *revision != current) return errorReply(command.id, "config.txt changed since the card loaded it ... Reload the card and choose again.");
if (result.displayChanged && !confirmDisplay) return errorReply(command.id, "This changes the display overlays. ... Send confirm_display=true to save anyway.");
if (!writeBootConfigText(result.text, &error, &how, &denied)) return errorReply(command.id, error);
```

**Checked.** Ran here: the gate; --simulate: stale revision, display change without confirm_display, dry_run=yes and an unknown sensor each answer {"ok":false,"error":"..."} only; Chromium: a sensor change reviews and saves; smoke_core shape diff clean; grep -rn errorReplyBody src is empty. Needs the Pi: change a sensor link on the CM5, Save, reboot, check /boot/firmware/config.txt and vcgencmd get_config str.

**Rule.** One error vocabulary: errorReply with one sentence; when a helper loses its last caller, delete it in the same commit.


---

## C77. web: lever info lines under the performance switches

Apertar-Core `57da4eb`. Finding: W1. Reviewed by a second agent: not reviewed.

**What was there.** WebControlPage.cpp@cinemate-port: Performance card TDN hint explained the mechanism ('Smooths noise ... six times faster per frame'), phase lock hint said what it does, no cost text. Peaking, Zebra, Record Audio, Log and Live preview had no cost line.

**Why it is a problem.** Original Apertar puts short <span class="subtle-note"> hints under controls (e.g. 'Frame buffer bar' in Live preview). The operator needs the cost of each lever, because the limit depends on it (requirements item 10).

**How to spot it.** grep -n 'pill-grid' WebControlPage.cpp and look for controls with no subtle-note next to them; ask 'what does this switch cost?'

**Options.**

- Static text in the page: small, no Core change
- Strings in SustainedFps.hpp sent by get_mode_ladder: one source for numbers, but needs Core and the D1 file, which this lane may not touch

**Chosen, and why.** Static text, as the task says. Cost: the numbers live in the page until D1/W2 can send them from Core. The Automatic split sentence is left out because no Automatic mode exists yet; D5 should add it.

**After.**

```
<span class="subtle-note">Costs under 1 fps, only at the limit of 4K Clear HDR. Record sound as you like; at the limit, turning it off gains about 1 fps.</span>
```

**Checked.** node --check of the extracted script; headless Chromium load with mocked routes: no page errors, lines present. On the rig: open the WebUI Settings and read the lines.

**Rule.** A switch that changes performance gets one plain line saying what it costs and when to use it.


---

## U18. ui: lever info lines under Record Audio, Peaking, Zebra, Log, Split

Apertar-UI `0981e32`. Finding: U1. Reviewed by a second agent: not reviewed.

**What was there.** No lever text in the touch UI. Cards had one short elided description, e.g. qml/SettingsPage.qml Focus Peaking: description: "Highlight in-focus edges"; Record Audio: "Capture audio alongside recorded clips".

**Why it is a problem.** The operator cannot see which switches cost frames at the limit of 4K Clear HDR (design auto-ladder.md, Lever info lines). Original Apertar shows hints as a grey secondary Text under the control (Split Long Takes hint, SettingsPage.qml@upstream-1.6.0, same colour #8cffffff, interRegular, WordWrap). MonitoringRow.description is one elided line, so it cannot hold a long sentence.

**How to spot it.** Question: where does the operator learn what a switch costs? Grep the design page for exact texts, then grep SettingsPage.qml for the card title and see whether a Text line already exists.

**Options.**

- Put the text in MonitoringRow.description: no layout change, but it is elided to one line and the text is cut off.
- Add a wrapped note property to MonitoringRow.qml: clean, but edits a shared component for five users and is outside the plan's file list.
- Wrap the card in a Column with a Text under it in SettingsPage.qml (chosen): local, copies the existing Text style; the diff re-indents the card bodies.

**Chosen, and why.** Third option. Column is a Qt Quick item that stacks children vertically and takes its height from them, so the Loader around the component still sizes correctly. Given up: a small re-indent diff for Peaking, Zebra and Record Audio (git diff -w shows 66 added lines only). Split text drops 'Automatic turns it on above 32 fps' because the UI has no Automatic mode until D5; adding it now would be untrue.

**After.**

```
Column {
    width: parent.width
    spacing: 6
    MonitoringRow { ... unchanged ... }
    Text { width: parent.width; text: "No measured cost. ..."; color: "#8cffffff"
           font.family: interRegular.font.family; wrapMode: Text.WordWrap; renderType: Text.NativeRendering }
}
```

**Checked.** Ran check_ui.sh lane-dr-ui: PASS, 0 warnings (QML compiled ahead of time). Nothing seen on a screen. On the HDMI build with a mouse: open Settings, Overlays & Assist (Peaking, Zebra), Audio, Record (Log with a Clear HDR cDNG mode, Split Long Takes); check the lines wrap and that the favourites page still shows Peaking/Zebra/Record Audio correctly.

**Rule.** A card's description line is one elided line; a longer hint goes in a wrapped grey Text under the control, in the existing style.


---

## C78. camera: the fps ceiling is the lower of Core's table and the probe again

Apertar-Core `0101a6c`. Finding: CM6. Reviewed by a second agent: not reviewed.

**What was there.**

src/camera/CameraController.cpp:3509-3534@cinemate-port (same code at the lane tip fa1dc5c):
 bool fpsLimitTableOnly() { static const bool tableOnly = [] { value = getenv("APERTAR_FPS_LIMIT"); table = value && string(value)=="table"; ... }(); }
 double maximumSupportedFpsForResolution(...) {
   const bool minWithTable = sensorFamily == Imx283 ? !imx283ProbeFpsOnly() : fpsLimitTableOnly();
   return fpsceiling::resolveSensorMaxFps(probed, table, minWithTable);   // probe alone unless =table
 }
 Dead: backendMaximumFps() returned nullopt; applyBackendCap wrapped it at three call sites.

**Why it is a problem.** The port made the probe the whole ceiling by default, so a stock camera with the original driver offered 60 fps at 4K 12-bit where 1.6.0 offered 30 (table alone, CameraController.cpp:2629-2681@upstream-1.6.0, 4K = 30). Fork main, the merge target, lets the probe only lower the table: probed ? std::min(table, *probed) : table (CameraController.cpp:2763-2769@f60e301). Conventions CAM-24 and R8: a bench knob is an env var APERTAR_<AREA>_<KNOB> read at the point of use, default in code, echoed on the take-start line. The port read it once into a static and printed its own log line. Rule 2 of the campaign: the owner's decision (probe alone) stays, as a setting whose default is the 1.6.0 value.

**How to spot it.** grep -n 'getenv("APERTAR_' src/camera/CameraController.cpp and ask of each knob: what does a camera without the variable do, and is that what 1.6.0 did? Also grep for functions that return a constant (nullopt, 0) and have callers: dead code that hides a decision (backendMaximumFps).

**Options.**

- Keep the probe-alone default and document the knob: leaves every stock camera with 60 fps at 4K, a change from 1.6.0 (cost: breaks the stock rule)
- min(table, probe) by default, APERTAR_FPS_LIMIT=probe for the probe alone (cost: the owner adds one drop-in line, and a saved fps above the table is clamped if he forgets)
- A [camera] max_fps key in apertar-hardware.conf (cost: the owner rejected a file key for this, and the camera side never reads that file, CAM-19)
- A socket command or WebUI switch (cost: the original developer sees a new setting for an internal limit, CAM-24)

**Chosen, and why.** Option 2, as the camera-modes page and the owner's recorded decision say. The switch is an env var read at use, so no state is cached and a restart picks it up. 'table' is still accepted as a spelling of the default, so an existing drop-in line keeps its meaning. The IMX283 keeps min(probe, floor) whatever the variable says, because its probe can report more than the sensor delivers; its own knob APERTAR_IMX283_PROBE_FPS is gone. Given up: the host test for the pure rule (resolveSensorMaxFps) is gone, the rule is now three lines in CameraController.cpp that only the probe (libcamera, a camera) reaches. boolEnvValue moved back inside the libcamera guard, because its last unguarded user was deleted and the no-libcamera build would warn.

**After.**

```
bool fpsLimitProbeOnly()
{
    const char *value = std::getenv("APERTAR_FPS_LIMIT");
    return value && std::string(value) == "probe";
}
...
    if (!probed)
        return table;
    // The IMX283 stays at min(probe, the driver's floor): the probe can report more than it delivers.
    return fpsLimitProbeOnly() && sensorFamily != SensorFamily::Imx283 ? *probed : std::min(table, *probed);
// recording clip line: if (fpsLimitProbeOnly()) std::cerr << " fps_limit=probe";
```

**Checked.** Run here: check_core.sh both builds and 21 host tests pass, lc 0 warnings, nolc 3 (the old mediumGone, basePathOverride, allocatePhotoBasePath). The first gate run showed a new nolc warning (boolEnvValue unused); fixed by moving the #endif. Not run here: the probe needs libcamera and a sensor, and --simulate has sensor Unknown, so nothing reaches the changed rule and no reply field changed. Needs the Pi: no env knob, get_state at 3840x2160 12-bit has fps_max 30; with Environment=APERTAR_FPS_LIMIT=probe in the unit it is 60, and journalctl -u apertar-core -b | grep 'recording clip:' shows fps_limit=probe on a take.

**Rule.** A bench knob defaults to the original behaviour and the operator who needs the port's behaviour sets it; read it where it is used and echo it on the take-start line.


---

## C79. camera: camera_settings.conf holds the mode ladder

Apertar-Core `fc78555`. Finding: CM10. Reviewed by a second agent: not reviewed.

**What was there.** src/camera/CameraController.cpp:404-430@cinemate-port: modeLadderPath() copied persistedSettingsPath() with another file name; saveModeLadderLocked() called settingsFile::atomicWrite(modeLadderPath(), ladder::fileText(modeLadder_)) under mutex_; saveModeLadderAspectsLocked() read the file back and replaced one line (withAspectsLine) so a filter click never erased a resolutions line it could not read; the constructor read the file with ifstream. fileText's header line carried 'T34'.

**Why it is a problem.** Original Apertar keeps camera-wide settings in camera_settings.conf: one field in CaptureSettings, one loader key, one writer line, copied across format profiles, written only by Core's debounced persister (tuning_file, CameraController.cpp:7939-7955 and :742-889@upstream-1.6.0; conventions CAM-25, CAM-29, CAM-40). A second file has its own writer, its own failure path and its own read-back check. The take-over of an old value follows the UI's presets folder and DefaultTuningSelection.hpp:74@upstream-1.6.0: the loader reads the retired form while the new place is empty.

**How to spot it.** grep -n 'atomicWrite\|Path()' src/camera/CameraController.cpp and ask: is there a second settings file beside camera_settings.conf? A function that copies persistedSettingsPath() with another name is the smell.

**Options.**

- Keep mode_ladder.conf and only tidy it: no change for the owner, but a second persistence path stays for the original developer to learn
- Three keys as the plan says, without the aspect filter: loses the filter, which the port added after the plan
- Four keys in CaptureSettings, loaded and written in every block like tuning_file: one shape, the filter rides along (chosen)
- Write the ladder keys only in the active block: shorter file, but a profile block then misses the keys the format carry expects

**Chosen, and why.** Four keys in every block, the tuning_file shape. The plan named three keys; the aspect filter (mode_ladder.conf had an aspects= line by the time of this commit) needs a fourth, so I added mode_ladder_aspects and said so in the commit. modeLadder_ stays the parsed form so ladderActiveForLocked, which holds the DB-45 block, is untouched; it is set only in the constructor, setModeLadder and the start() rung step. A preset keeps the camera's ladder (applyCapturePreset copies the four fields from settings_), because App keeps old settings snapshots for timelapse and preset rollbacks and a stale snapshot would otherwise bring an old ladder back. Given up: a ladder edit is now debounced about 25 ms by the persister instead of written synchronously; the 'Could not write mode_ladder.conf' warning is gone (the WebUI still looks for it in showLadderWriteWarning, which never fires now; W3 deletes it). The resolutions text is kept as the file had it when it cannot be parsed, so an unreadable line is never erased by a later save.

**After.**

```
output << prefix << "mode_ladder_enabled=" << s.modeLadderEnabled << '\n';   // + _ramp_ready, _resolutions, _aspects
...
else if (key == "mode_ladder_resolutions")
    settings.modeLadderResolutions = value;
...
modeLadder_ = ladder::fromText(settings_.modeLadderEnabled, settings_.modeLadderRampReady,
                               settings_.modeLadderResolutions, settings_.modeLadderAspects);
// loader: if (!modeLadderKeys) takeOverModeLadderFile(current, formats, still);
```

**Checked.** Run here: check_core.sh both builds and 21 host tests pass; the only warnings in CameraController.cpp are the three old nolc ones. In --simulate with fresh HOME folders under /home/user/build/sim/drcore/: an old mode_ladder.conf is taken over at the first start (also when camera_settings.conf did not exist); the first persist writes the four keys with the same resolutions text; a restart without the old file shows the same ladder; set_mode_ladder with resolutions, enabled and aspects persists across a restart; a record format switch cdng, h264, cdng keeps it; set_mode_ladder enabled=false works after enter_standby; set_resolution is still refused while the ladder is on; smoke shapes match 1.6.0. Needs the camera: get_mode_ladder before and after the update on the owner's rig, diffed, and one blocked set_resolution with the ladder on.

**Rule.** A camera-wide setting is one more key in camera_settings.conf, carried across the format profiles; an old file is read once while the new place is empty and then left alone.


---

## C80. camera: known-limits table

Apertar-Core `980a05b`. Finding: D1. Reviewed by a second agent: not reviewed.

**What was there.** Nothing in Core knew what the recording path holds for a long take: grep -rli sustained src found no file. The only ceilings were the sensor's (probe, table, FpsCeiling.hpp) and the lossless cap. The numbers lived in the owner's test notes (estimator-campaign pre-analysis and findings).

**Why it is a problem.** A screen or a rule that needs a limit has nothing to ask, so each would copy numbers from a note and drift from it. Original Apertar keeps pure logic in one small header named after the concept, std only, host-tested (CAM-4, StillBracketing.hpp:8-19@upstream-1.6.0); this tree does the same for FpsCeiling.hpp and ModeLadder.hpp.

**How to spot it.** Ask where a number that a user will see comes from. If the answer is a KB page or a comment, it needs a row in a table with a label and a source, and a test that pins it.

**Options.**

- One header with a constexpr table and pure functions, test pins the rows (chosen)
- Numbers inside CameraController.cpp next to the sanitiser: no new file, but not host-testable without libcamera
- A data file Core reads at start: the operator could edit limits, but a typo changes what the camera records and the original developer has no such file

**Chosen, and why.** Option 1, the new file the plan names. Data and rules sit together so an update to the analysis edits rows only. The header stays std only: no MediaProfile and no libcamera types, the caller maps its own enums onto Kind, Board and Mode. Choices made while writing it: (1) a Cell carries width and height, not only the long side, so the nearest-larger rule can compare pixels and 2880x2160 has its own cell; (2) the USB SSD pixel rate (149 Mpx/s) is mine, derived from the same 4K 18 fps and 2880x2160 24 fps cells as the NVMe one, the page gives only the NVMe 330; (3) fpsShort is 27 for NVMe 4K Clear HDR 16-bit only: the page also lists 37 and 38 fps for 4K SDR 12-bit, but those takes were uncompressed and the cell is lossless, so I left that cell's short number at 0 rather than print a number for the wrong format; (4) the lever info lines are not in this header: W1 already put them in the WebUI as static text, so a second copy would drift. Given up: the info strings as one source (see kb_changes).

**After.**

```
inline constexpr Cell kCells[] = {
  { Kind::Nvme, Board::Pi5, 3840, 2160, true, 16, false, "none", 20, 27, Label::Unconfirmed, Group::BackEnd, "..." }, ...
inline Limit limitFor(const Context &context, const Mode &mode);   // own cell, nearest larger, pixel rate, none
inline Cap capFor(const Context &context, const Mode &mode, double sensorCeiling);   // levers, then stepDown
inline double stepDown(double fps);   // 25, 30, 33, 50, 60, 70, 80 ...
```

**Checked.** Run here: check_core.sh both builds and 22 host tests pass; sustained_fps_test pins the 18 cells and caps, the steps, the lookup order, the levers and the flat-folder formula (32 fps for 30 minutes). Nothing calls the header, so there is nothing to run on the camera. The numbers themselves need the three hot 30-minute takes of 4K Clear HDR 16-bit (24, 22, 20 fps) before the 20 is more than a placeholder.

**Rule.** A number the camera shows to the operator lives in one table with its label and source, in a pure header, and a host test pins it so a change is deliberate.


---

## C81. camera: Core reads the storage and lever context and publishes the known limit

Apertar-Core `52a37e7`. Finding: D2. Reviewed by a second agent: not reviewed.

**What was there.** CameraController.cpp@cinemate-port: fps_max and fps_take_max were the only limits in the state, from the sensor probe, the table and the lossless cap (maximumFpsForSettings). Nothing in Core knew the storage type or how full the card was for the camera; App had the media profile (mediaProfile_, ApertarCoreApp.cpp:11662) and UI.conf values but never gave them to the camera.

**Why it is a problem.** Original Apertar fills camera-derived values as runtime fields of CaptureSettings (a 'Runtime' comment, set in settings() and emitSettingsEventLocked; exposureCompensationAvailable, Types.hpp:132, CameraController.cpp:8570 and :8779@upstream-1.6.0, conventions CAM-18). The state stays flat scalars. The camera never reads App's files or threads; App pushes (CAM-10, the camera takes mutex_ first).

**How to spot it.** Ask: which of this value's inputs does the owning class not have? If App has them, add one setter on the camera that App calls where the input changes (a push), and let the camera fill the derived field where it fills the others.

**Options.**

- App pushes one Context struct when a fact changes; the camera fills the fields on read and on event (chosen)
- The camera pulls through a std::function that App supplies: no push sites, but it calls into App (file reads, locks) while the camera holds mutex_
- App computes the limit and the camera only stores it: the table logic would sit in the big App file and the camera could not use it to choose a mode in D3

**Chosen, and why.** Option 1, as the plan says. The push sites are the media change hook, the media watcher poll (only when the card crosses 94 percent, so a fuller card is not an event), the UI switches through handleUiToggle (hardware button toggles go through the same command), a preset, and set_frames_per_folder. Not covered yet: other writers of the hardware file that refreshBufferRequest() serves (a whole-file save, set_buffer_mode); D5 changes the split and should push there. A simulated camera counts as a Pi 5 so the table can be tried without a Pi; any other board without BCM2712 gets no limits and says so. The Log lever is read from the setting (cdng_log), not cdng_log_applied, so it also works in simulation. Given up: audio is carried but the table does not use it yet (the page says audio changes nothing).

**After.**

```
void ApertarCoreApp::refreshLadderContext() { ... context.fatLike = profile.filesystem == MediaFilesystem::Exfat || ...; camera_.setLadderContext(context); }
void CameraController::fillLimitFieldsLocked(CaptureSettings &out) const { ... const sustained::Cap cap = sustained::capFor(context, mode, ceiling); out.limitFps = cap.fps; ... out.limitWhy = sustained::whyText(context, mode, cap, ceiling); }
// state: "limit_fps":0.000,"limit_short_fps":0.000,"limit_basis":"unconfirmed","limit_by":"TDN","limit_why":"..."
```

**Checked.** Run here: check_core.sh both builds and 22 host tests pass; only the old ApertarCoreApp.cpp unused-function warning shows. In --simulate with fresh HOME folders: get_state and the socket settings event carry the five fields as valid JSON; limit_why reads like the page's examples; set_preview_tdn false, set_clear_hdr, set_raw_bit_depth 16 and set_fps_phase_lock change limit_fps and limit_why; H.264 gives 'Limits are not measured for H.264, ProRes and stills.'; smoke shapes match 1.6.0's. Needs the Pi: on the NVMe get_state at 4K Clear HDR 16-bit has limit_fps 20 and limit_basis unconfirmed; pull the card and mount the T7 and the fields change while fps, mode and fps_max stay.

**Rule.** A value the camera derives from facts that live in App is pushed by one setter where the facts change; the camera fills the derived field where it fills the others.


---

## C82. camera: Dynamic resolution picks the mode from the table

Apertar-Core `f66f27e`. Finding: D3. Reviewed by a second agent: not reviewed.

**What was there.** ModeLadder.hpp@cinemate-port: Rung carried threshold, compression, cdngLog; chooseRung took the first rung whose min(threshold, sanitiser ceiling) reached F; validate() refused rising-threshold and repeat errors and 'No FPS left for it' when saving.

**Why it is a problem.** The owner replaced the user ladder by a table of known limits (design auto-ladder.md, owner answers). The validator also blocked enabling a tile with the ladder off, which the owner reported. Original Apertar has no ladder (grep -rli ladder src@upstream-1.6.0 finds only ProresEncoder), so this is new ground kept in the port's own pure header plus the sanitiser as the arbiter (CAM-4, CAM-21).

**How to spot it.** A save path that runs a whole-list validator for a one-item edit. Ask: can the operator add one item at any time, or must the whole list be consistent first?

**Options.**

- New Candidate/tryOrder/chooseMode beside the old code, old code removed in D4 (chosen)
- Rewrite ModeLadder.hpp in one go: bigger diff, harder to review
- Keep thresholds as optional overrides: contradicts the owner's answer

**Chosen, and why.** First option. Size note: the commit is about 430 lines added, over the 300 guide, because the CM10 fields were renamed (about 60 lines of mechanical change), the pool extraction and the tests count too; splitting would have left a build that cannot take enable_mode. Compression comes from the table cell for cDNG only; boards without RAW compression get uncompressed. The default list is every pool mode whose window (size x binning) equals the largest; crops are opt-in. enable_mode starts from the default list when the list is empty. Check validateModes: only repeats and modes the sensor lacks are errors, a mode that cannot run in this format is a warning.

**After.**

```
inline int chooseMode(const std::vector<Candidate> &c, double targetFps);  // first usable in tryOrder with cap >= F, else highest cap
if (enableMode || disableMode) { list = enabledModesLocked(draft); add or erase one mode; if (list.empty()) *error = "Enable at least one resolution."; }
```

**Checked.** Run here: gate passes, 22 host tests; table C reproduced for NVMe and USB SSD in mode_ladder_test; simulate: modes/enable_mode/disable_mode work with ladder on and off, set_fps 20/25/33/50 pick and clamp, set_resolution still refused when active (D7 changes that). Simulated camera uses the USB column (storage unmeasured). Needs the Pi: set_fps 25/30/33/50 on NVMe lands on table C; tile enable/disable rebuilds the list at once; nothing changes in a take.

**Rule.** An edit of one list item must not depend on the rest of the list being valid; let the arbiter (the sanitiser) judge each mode alone.


---

## C83. camera: a manual mode pick pins until the next fps change

Apertar-Core `e2658d4`. Finding: D7. Reviewed by a second agent: not reviewed.

**What was there.** CameraController.cpp setResolution/setRawBitDepth@lane tip: if (ladderActiveForLocked(settings_)) { setErrorLocked(kLadderOwnsMode); return false; }

**Why it is a problem.** A block on manual picks plus on-by-default makes a stock camera unable to choose 4K Clear HDR 16-bit by hand; 1.6.0 accepts every pick. The port already had the softer ladderOverride_ for set_clear_hdr.

**How to spot it.** grep -n 'LadderOwns' src/camera/CameraController.cpp: each setter that refuses instead of pinning.

**Options.**

- Pin via ladderOverride_ (chosen): reuses an existing flag, no new state
- Keep the block: contradicts owner answer 1
- A new pinned-mode field persisted: survives restart, but adds saved state nobody asked for

**Chosen, and why.** Reuse ladderOverride_. Not saved, so a restart returns control to the table. A second manual pick while pinned keeps the pin (ladderWasActive || overrideBefore). No host test: the logic is in CameraController (libcamera-free but not host-testable); checked by simulate run.

**After.**

```
const bool ladderWasActive = ladderActiveForLocked(settings_);
...
ladderOverride_ = ladderWasActive || overrideBefore;
if (!applySettingsLocked(next, true)) { ladderOverride_ = overrideBefore; return false; }
```

**Checked.** Simulate: set_fps 25 picks 2K HDR16; set_resolution 4K and set_raw_bit_depth 12 accepted with ladder_override true; set_fps 33 hands back to the table. Pi: same at the camera, get_state shows the picked mode's limit.

**Rule.** When a feature is on by default, an explicit operator choice pins instead of being refused.

