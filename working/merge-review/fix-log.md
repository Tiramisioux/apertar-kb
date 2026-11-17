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
