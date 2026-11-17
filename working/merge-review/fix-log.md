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

