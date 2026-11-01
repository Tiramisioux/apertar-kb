---
datum: 2026-10-29 22:40:00
kontext: CINEMATE
projekt: "#APERTAR"
fritext: T37 core-owns-the-hardware-file
typ: digital anteckning
---

# T37. Core owns `apertar-hardware.conf`: one store, a validator that names the line

Status: **done 2026-10-29** by Claude on the Mac, built and checked on the Pi (Core `controls` branch, `3526e4b`, `c509e9f`, `f5a61b8`, `4d80a35`). Step 2 of the Apertar Controls project (`working/controls/`).

**You will learn**
- why a file several programs read needs one writer, and why "one" means one object inside the process;
- atomic write, lock, revision, the stable-file check, and how a lost update happens;
- a validator built from what each reader really does, comment rules included.

**Risk:** a bug in the store could write a wrong file. The host tests, the history (`~/.config/apertar-core/hardware-history/`) and `.bak` cover it, and a save is refused if it adds an error. **Undo:** `git -C ~/ApertarCore switch cinemate-port`, rebuild, restart Core; to restore the file, copy a version from the history with `cp`.

## 1. The problem

Four places wrote `~/apertar-hardware.conf` with no lock and no version. The IMU writer could delete the file (it removed it, then renamed a temp file over it). A comment after `bus=1` silently meant bus 10 for the hat in one reader and not in another. Nothing checked the file when Core started: a bad line showed only when a button did nothing.

## 2. How this part works

- `HardwareConfigText.hpp` reads the file as lines and edits one key without touching any other byte. Each section carries the comment rule its own reader applies.
- `HardwareConfigStore` is the only writer in Core. It takes a mutex, then the file lock, refuses a file an editor is still writing, validates, keeps the version it replaces, and writes atomically.
- `get_controls` and `set_controls` are the API on top. The read-only commands answer before the command lock.
- At start Core validates once, logs a summary and pins the file as found in the history ("Before Controls").

Read: `src/hardware/HardwareConfigStore.cpp:240` (`saveLocked`), `src/hardware/HardwareConfigText.hpp:314` (`revision`).

## 3. Find it yourself

**3.1 How did the IMU code write the file before?** On the old tree: `git -C ~/ApertarCore show 4fa0432:src/hardware/Mpu6050RecordingSession.cpp`, search `std::filesystem::remove(path, ec);`. Prediction: 2 lines. Question: what does the touch UI do at its next start if the second rename fails too?

> [!tip]- Answer
> It writes its own template: the hat on bus 10 and the NeoRotary off.

**3.2 Is your file clean?** `get_controls` on the Pi. Prediction: `"errors":0,"warnings":0`.

**3.3 What is "a revision"?** `h` plus 16 hex digits of a hash of the whole text. Change one byte and it changes. Question: why must it start with a letter?

> [!tip]- Answer
> `core.py` turns an all-digit value into a number.

## 4. What was changed

**4.1 Text model and store** (part 1): new `HardwareConfigText.hpp`, `HardwareConfigStore.hpp/.cpp`, one line in `CMakeLists.txt`. **Check:** `grep -c 'src/hardware/HardwareConfigStore.cpp' CMakeLists.txt` is 1.

**4.2 The IMU writers** (part 2): level set, level clear and calibration each make one store edit; the temp file and the remove-then-rename code are gone. **Check:** `grep -c 'std::filesystem::remove(path, ec);' src/hardware/Mpu6050RecordingSession.cpp` is 0.

**4.3 The commands** (part 3): `errorReplyBody`, `get_controls`, `set_controls`, and `handleReadOnlyHardwareCommand` before the command lock. **Check:** `grep -c 'command.name == "set_controls"' src/ApertarCoreApp.cpp` is 1.

**4.4 Start-up check and template** (part 4): the summary line, `controls_errors` and `controls_warnings` in state, the adopted version, and a template that validates. **Check:** `grep -c 'T37: validate the hardware file once' src/ApertarCoreApp.cpp` is 1.

**4.5 KB tools** (part 5): `core.py` sends a file's bytes with `text@=path` and waits for the reply line; `tutorial.py` allows `get_controls`. **Check:** `grep -c 'get_controls' ~/apertar-kb/tutorials/tutorial.py` is 1 or more.

A save during a take is allowed (your decision Q5); nothing is applied until T39. Script paths are never changed through the store (Q2).

## 5. Build, deploy, test

```bash
ssh apertar 'cmake --build ~/ApertarCore-build -j2'     # never during a take
sudo systemctl restart apertar-core                      # Patrik
python3 ~/apertar-kb/working/tools/core.py get_controls  # revision, 0 errors, your file's text
python3 ~/apertar-kb/working/tools/core.py set_controls base=<revision> text@=/home/pi/apertar-hardware.conf dry_run=true
```

The dry run must show an empty `diff`. (`text="$(cat …)"` would drop the final newline and show one change.) The journal at start reads `ApertarCore controls: ~/apertar-hardware.conf h…: 0 errors, 0 warnings; adopted, nothing changed`. A real save of your file (a comment added, then the original saved back) left it byte-identical, with `.bak` and two history entries.

**5.1 Check:** `get_controls` answers with `"errors":0`.

## 6. Commit

Core `controls`: `3526e4b`, `c509e9f`, `f5a61b8`, `4d80a35`, one commit per part. KB: the host tests `controls_test.cpp` (89 checks; 88 on a Mac, where the `sed` check needs GNU sed) and `controls_store_test.cpp` (39 checks, Linux only), and the live file as a fixture. Not pushed to GitHub.

## 7. If it went wrong

| You see | It means | Do |
| --- | --- | --- |
| `"code":"stale"` | the revision you sent is not one Core knows | `get_controls` again and resend |
| `"code":"errors"` | the new text adds an error; the message names the line | fix the line, or send `force=true` |
| `"code":"being_written"` | an editor saved the file in the last second | try again in a second |
| `"code":"locked"` | another program holds the file lock for 2 s | try again |
| `"code":"script_paths"` | the text changes a `[run_script]` path | change script paths over ssh |
| The file looks wrong after a save | a bug in the store | copy the version from `~/.config/apertar-core/hardware-history/` back with `cp` |

## 8. What you learned, going further

- One writer, one lock, one revision: a lost update cannot happen quietly.
- The validator names the line and the rule; old errors never lock the editor out.
- Exercise: add a comment after a value in a scratch copy of the file and run the validator test. Which reader ignores the value?
- Next: T38, no more silent overwrites (old tabs, the touch UI's template, large saves).

## 9. Sources

`working/controls/design-controls.md` §3.1 to §3.5, §6 (T37), §7 (T37); `working/controls/decisions.md` (Q1, Q2, Q3, Q5, Q12, Q13); Core `controls`; host tests `working/tools/controls_test.cpp` and `controls_store_test.cpp`; live-file fixture `controls_fixture_apertar-hardware.conf`; hardware log 2026-10-29.

%% tutor
ref core src/hardware/HardwareConfigText.hpp 314 inline std::string revision(const std::string &text)
ref core src/hardware/HardwareConfigStore.hpp 59 class HardwareConfigStore {
ref core src/hardware/HardwareConfigStore.cpp 248 StoreResult HardwareConfigStore::saveLocked(const std::string &base, const std::vector<hwconf::Edit> *edits,
ref core src/hardware/Mpu6050RecordingSession.cpp 607 bool writeHardwareConfigValues(const std::string &sectionName,
ref core src/ApertarCoreApp.cpp 141 std::string errorReplyBody(int id, const std::string &message, const std::string &body)
ref core src/ApertarCoreApp.cpp 4599 std::string defaultHardwareConfigTemplate()
ref core src/ApertarCoreApp.cpp 7565 // T37: validate the hardware file once, say what it holds, and pin the version Core found. Nothing is changed.
ref core src/ApertarCoreApp.cpp 10371 std::optional<std::string> ApertarCoreApp::handleReadOnlyHardwareCommand(const ControlCommand &command)
ref core src/ApertarCoreApp.cpp 10587 if (command.name == "set_controls") {
ref core CMakeLists.txt 94 src/hardware/HardwareConfigStore.cpp
check 3.1 | git -C /home/pi/ApertarCore show 4fa0432:src/hardware/Mpu6050RecordingSession.cpp | std::filesystem::remove\(path, ec\);
check 3.2 | curl -s -m 3 -X POST http://127.0.0.1:8000/api/command -d '{"cmd":"get_controls"}' | "errors":0,"warnings":0
check 4.1 | grep -c 'src/hardware/HardwareConfigStore.cpp' /home/pi/ApertarCore/CMakeLists.txt | ^1$
check 4.2 | grep -c 'std::filesystem::remove(path, ec);' /home/pi/ApertarCore/src/hardware/Mpu6050RecordingSession.cpp | ^0$
check 4.3 | grep -c 'command.name == "set_controls"' /home/pi/ApertarCore/src/ApertarCoreApp.cpp | ^1$
check 4.4 | grep -c 'T37: validate the hardware file once' /home/pi/ApertarCore/src/ApertarCoreApp.cpp | ^1$
check 5.1 | curl -s -m 3 -X POST http://127.0.0.1:8000/api/command -d '{"cmd":"get_controls"}' | "errors":0
%%

#CINEMATE
#APERTAR
