---
datum: 2026-10-29 21:50:00
kontext: CINEMATE
projekt: "#APERTAR"
fritext: T36 one-action-vocabulary
typ: digital anteckning
---

# T36. One action vocabulary: `ActionCatalog.hpp` and `list_actions`

Status: **done 2026-10-29** by Claude on the Mac, built and tested on the Pi (Core `controls` branch, `916c1dd`). First step of the Apertar Controls project (`working/controls/`).

**You will learn**
- why copies of the same list drift apart, and how one header with a host test stops it;
- how a test can read the dispatcher and fail when a name has no branch;
- how a socket command serves data (`list_actions`).

**Risk:** none for the camera. Same names, same results; the host test proves it. A Core restart is needed. **Undo:** `git -C ~/ApertarCore switch cinemate-port`, rebuild, restart Core.

## 1. The problem

The action names (`iso_up`, `capture`, …) were written out in **three identical copies** of `normalizeSingleAction` (GpioInput, Pcf8574Input, NeoRotary4Input), plus two copies of the analog targets, the trigger-event list and the tally tokens. Adding `zebra_toggle` meant editing six places. A typo in `apertar-hardware.conf` was silent until you pressed the button.

## 2. How this part works

- `src/hardware/ActionCatalog.hpp` holds one table, `kSpecs[]`: the canonical id, its group, a label, every alias, and whether it is for buttons, knobs or the touch UI.
- `canonicalAction(text)` turns any alias into the canonical id. An unknown name passes through unchanged; App then logs `Hardware input action ignored: unknown action 'x'. Did you mean 'y'?`.
- The behaviour stays in `ApertarCoreApp::handleSingleHardwareInputAction`. A new action needs **a catalog line and a dispatcher branch**; the coverage test fails until both exist.
- `list_actions` serves the table plus the value lists the knobs already cycle through (ISO, shutter angle and speed, WB, fps, resolution), cut to the current mode.

Read: `src/hardware/ActionCatalog.hpp:122-132`, `src/hardware/ButtonActionList.hpp` (`parseButtonActions`).

## 3. Find it yourself

**3.1 How many copies were there?** On the old tree: `git -C ~/ApertarCore show 4fa0432:src/hardware/GpioInput.cpp | grep -c 'std::string normalizeSingleAction'`. Prediction: 1 in each of the three files. Question: what did an unknown name become?

> [!tip]- Answer
> Itself. The copy returned the name unchanged and App ignored it at press time.

**3.2 Were the copies identical?** Gpio and NeoRotary4 were byte-identical; Pcf8574 differed only in line wrapping. The host test compares the new header against all three on 300+ tokens.

**3.3 Which analog-target copy also knew `none`?** Question, then check `canonicalAnalogTarget` in the header.

> [!tip]- Answer
> Grove's. App never sees `none`, because Grove drops it first, so the shared function returns "no target" for it in both places.

## 4. What was changed

**4.1** New `src/hardware/ActionCatalog.hpp`. **Check:** `grep -c 'inline std::string canonicalAction' src/hardware/ActionCatalog.hpp` is 1.

**4.2** Host test `working/tools/controls_test.cpp` with the old code regenerated from the unedited tree (`controls_make_old.sh`, `controls_make_old2.sh`). Run: `g++ -std=c++20 -Wall -Wextra -Werror -I. -I<core>/src controls_test.cpp -o controls_test && ./controls_test <core-tree>` ends `all ok: 20 of 20 checks`.

**4.3** The three copies deleted; `normalizeAction` passes `hardware::actions::canonicalAction`. **Check:** `grep -c normalizeSingleAction src/hardware/NeoRotary4Input.cpp` is 0.

**4.4** Analog targets, trigger events and tally tokens call the header (`GroveAnalogInput.cpp:128`, `ApertarCoreApp.cpp:9287`, `TriggerOutput.cpp:133`, `RecordingIndicatorOutput.cpp:121`). **Check:** `grep -c canonicalAnalogTarget src/hardware/GroveAnalogInput.cpp` is 1.

**4.5** App's `hardwareActionSuffix` and `parseHardwareActionNumber` delegate to `suffixAfter` and `numberAfter`; an unknown action logs a suggestion. The header takes the prefixes as `std::vector<std::string_view>` so App's `vector<string>` can call it. **Check:** `grep -c 'actions::suffixAfter' src/ApertarCoreApp.cpp` is 1.

**4.6** `list_actions` in `handleCommand`, also in `help`; `SAFE_CORE_CMDS` in `tutorial.py` gets `list_actions`. **Check:** `grep -c 'command.name == "list_actions"' src/ApertarCoreApp.cpp` is 1.

Two intended behaviour changes: `isoinf` and `isonan` are refused (before, they parsed), and App's analog target maps `none`, `off`, `disabled` to nothing.

## 5. Build, deploy, test

```bash
ssh apertar 'cmake --build ~/ApertarCore-build -j2'     # never during a take
sudo systemctl restart apertar-core                      # Patrik
python3 ~/apertar-kb/working/tools/core.py list_actions  # 52 actions; iso_up has "stepping":true
```

On the camera: turn each knob one detent each way, press each knob, press `d10` (take) and `d6` (eject). All worked as before (2026-10-29). The ISO list ends at Core's `iso_max` (1585 in 16-bit Clear HDR 4K), and the fps list at 25.

**5.1 Check:** `list_actions` answers with `"stepping":true`.

## 6. Commit

Core `controls`, `916c1dd`: `core: one action vocabulary in ActionCatalog.hpp, and list_actions (T36)`. KB: the host test and its generators in `working/tools/`. Not pushed to GitHub.

## 7. If it went wrong

| You see | It means | Do |
| --- | --- | --- |
| A test FAIL line naming a token | an alias is missing from `kSpecs` | add it to that line's `aliases` |
| `dispatcher coverage` FAIL naming an id | a catalog id has no branch in `handleSingleHardwareInputAction` (or the reverse) | add the branch, or the catalog line |
| A button does nothing after the change | an alias lost | compare with the old code: `git show 4fa0432:src/hardware/GpioInput.cpp` |
| `Unknown command: list_actions` | Core is still the old binary | rebuild and restart |
| Anything else | | `git -C ~/ApertarCore switch cinemate-port`, rebuild, restart |

## 8. What you learned, going further

- One header, one test that reads the old code and the dispatcher: a vocabulary cannot drift silently.
- Exercise: add `zebra_toggle` as an alias of `zebra` (one `aliases` entry) and run the test.
- Next: T37, Core owns `apertar-hardware.conf` (one store, a validator that names the line).

## 9. Sources

`working/controls/design-controls.md` §3.2, §3.3, §6 (T36), §7 (T36); `working/controls/decisions.md` (Q10, Q11); Core `controls` `916c1dd`; host test `working/tools/controls_test.cpp`.

%% tutor
ref core src/hardware/ActionCatalog.hpp 122 inline std::string canonicalAction(std::string_view text)
ref core src/hardware/GpioInput.cpp 111 return hardware::normalizeButtonMapping(action, hardware::actions::canonicalAction);
ref core src/hardware/Pcf8574Input.cpp 143 return hardware::normalizeButtonMapping(action, hardware::actions::canonicalAction);
ref core src/hardware/NeoRotary4Input.cpp 124 return hardware::normalizeButtonMapping(action, hardware::actions::canonicalAction);
ref core src/hardware/GroveAnalogInput.cpp 128 return hardware::actions::canonicalAnalogTarget(target);
ref core src/hardware/TriggerOutput.cpp 133 const std::string event = hardware::actions::canonicalTriggerEvent(token);
ref core src/hardware/RecordingIndicatorOutput.cpp 121 return hardware::isOutputAction(normalizeToken(text));
ref core src/ApertarCoreApp.cpp 1488 return hardware::actions::suffixAfter(action, prefixViews(prefixes));
ref core src/ApertarCoreApp.cpp 9864 const std::string suggestion = hardware::actions::suggestion(action);
ref core src/ApertarCoreApp.cpp 10408 if (command.name == "list_actions") {
check 3.1 | git -C /home/pi/ApertarCore show 4fa0432:src/hardware/GpioInput.cpp | std::string normalizeSingleAction
check 4.1 | grep -c 'inline std::string canonicalAction' /home/pi/ApertarCore/src/hardware/ActionCatalog.hpp | ^1$
check 4.3 | grep -c normalizeSingleAction /home/pi/ApertarCore/src/hardware/NeoRotary4Input.cpp | ^0$
check 4.4 | grep -c canonicalAnalogTarget /home/pi/ApertarCore/src/hardware/GroveAnalogInput.cpp | ^1$
check 4.5 | grep -c 'actions::suffixAfter' /home/pi/ApertarCore/src/ApertarCoreApp.cpp | ^1$
check 4.6 | grep -c 'command.name == "list_actions"' /home/pi/ApertarCore/src/ApertarCoreApp.cpp | ^1$
check 5.1 | curl -s -m 3 -X POST http://127.0.0.1:8000/api/command -d '{"cmd":"list_actions"}' | "stepping":true
%%

#CINEMATE
#APERTAR
