---
datum: 2026-10-29 23:10:00
kontext: CINEMATE
projekt: "#APERTAR"
fritext: T38 no-silent-overwrites
typ: digital anteckning
---

# T38. No more silent overwrites: old tabs, the UI's template, large saves

Status: **done 2026-10-29** by Claude on the Mac, built and tried on the Pi (Core `controls`: `5395fa4`, `effb804`, `014fa22`, `7af9f13`; UI `controls`: `c9d841f`, `7c41a27`). Step 3 of the Apertar Controls project (`working/controls/`).

**You will learn**
- a version header on HTTP, status 409, and telling a browser from a script by its `Origin`;
- why the touch UI's "create the file if it is missing" was a revert waiting to happen;
- a line limit that drops a client without a word, and a second one on the reply side.

**Risk:** low. Core: the Config page's save now goes through the store (T37). UI: two deletions; the UI is rebuilt. **Undo:** `git switch cinemate-port` in `~/ApertarCore` and `~/ApertarUI`, rebuild, restart both services.

## 1. The problem

- The Config page saved by copying the file to `.bak`, writing a `.tmp` and renaming it. An old tab, or a tab opened before a newer save, silently overwrote the newer file.
- The touch UI's display and INA219 bridges each wrote a whole default file whenever `~/apertar-hardware.conf` was missing: the CFE hat on bus 10, the NeoRotary off. A file moved with `mv`, or lost in a failed rename, came back as that template and undid the NeoRotary fix.
- The control socket closed a client without a word when one command line passed 64 KiB, which a whole-file `set_controls` can.

## 2. How this part works

- `GET /api/config` returns the file's `revision`. `POST /api/config` carries it back in `X-Apertar-Revision`. A browser (it sends `Origin`) without one is an old tab and gets **409**. A script (no `Origin`) keeps last-writer-wins.
- A stale or conflicting save gets 409 with the reason. A save that adds an error gets 400 with the issues, with line numbers. The page keeps the text in the box on any refusal.
- Core remembers the last version it wrote. If the file is then missing, empty, or starts like the UI's default template, `get_controls` says `replaced`, and `set_controls restore=true` puts the version back.
- The UI no longer writes the file at all.

Read: `src/ApertarCoreApp.cpp:8043` (the revision header), `src/hardware/HardwareConfigStore.cpp:416` (`replacedByDefault`).

## 3. Find it yourself

**3.1 What did the UI's template say about the hat?** On the old UI tree: `git -C ~/ApertarUI show 7029db1:src/DisplayConfigBridge.cpp`, search `bus=10`. Prediction: the `[cfexpress_hat]` lines. Question: why is that bad for you?

> [!tip]- Answer
> Your hat answers on bus 1. A template with bus 10 and the NeoRotary off would silently undo the fix.

**3.2 What happened at 64 KiB?** On the old tree: `git -C ~/ApertarCore show 4d80a35:src/ipc/ControlServer.cpp`, search `64 * 1024`. Question: what does a client get back?

> [!tip]- Answer
> Nothing; the connection closes.

## 4. What was changed

**4.1 Core, the file API** (part 1): GET with `revision` (and a `/boot` copy as the start when the file is missing), POST through the store with the 409 and 400 rules, the socket line limit raised to 1 MiB. The old `.tmp`-and-rename save is gone. **Check:** `get_controls` shows the same `"revision":"h…"` that `GET /api/config` returns (the tutor tool refuses checks on `/api/config`, which can write).

**4.2 The Config page** (part 2): the page sends the revision, shows the issues box with line numbers, and keeps your text on a refusal. **Check:** `grep -c 'X-Apertar-Revision' src/web/WebControlPage.cpp` is 1 or more.

**4.3 Replaced by a default** (part 3): the store keeps the last version Core wrote; `replacedByDefault`, `get_controls` `replaced`, `set_controls restore=true`. A new file is created `rw-r--r--` like the file always was. **Check:** `grep -c 'replacedByDefault' src/hardware/HardwareConfigStore.cpp` is 1 or more.

**4.4 The UI** (part 4): both `ensureDefaultHardwareConfigFile` writers and their calls are deleted. **Checks:** the name is gone from `DisplayConfigBridge.cpp` and from `Ina219Bridge.cpp`.

**4.6 HDMI is the fallback** (part 5): found when a touch UI restart with the file moved away came up as a small 720x720 square (the old Hyperpixel layout) on the HDMI output. With no file, or no `[display]` keys, the UI now uses 1920x1080, `landscape_large`, `hdmi_external_only=true` (UI `7c41a27`), and Core's default template says the same (`7af9f13`). A file that sets the keys is read as before. `config.txt` was not touched: its DPI overlay lines are commented out and the kernel sees only HDMI.

One thing the tests showed: a socket reply bigger than about 208 KB (the socket's send buffer) cuts the client off. That has always been so (`MSG_DONTWAIT` keeps a stalled client from blocking camera events). It only matters for files over about 100 KiB; the WebUI uses HTTP and is not affected.

## 5. Build, deploy, test

```bash
ssh apertar 'cmake --build ~/ApertarCore-build -j2'      # never during a take
ssh apertar 'cmake --build ~/ApertarUI/build -j2'
sudo systemctl restart apertar-core apertar-ui-direct     # Patrik
```

Core: a browser without a revision gets 409 "Apertar was updated: reload this page"; a wrong revision gets 409; `bus=999` gets 400 with "Line 105"; a 91 KB text through the socket gets a reply. In a real (headless) Chrome against the camera, `working/tools/controls_config_page_test.js` does the three browser tests and restores the file byte for byte. The design's own test: move the file away with a safe copy, restart the touch UI, and no file appears; `get_controls` says replaced, and `set_controls restore=true` brings it back identical.

**5.1 Check:** `get_controls` answers `ok`.

## 6. Commit

Core `controls`: `5395fa4` (file API and socket), `effb804` (the page), `014fa22` (replaced by a default), `7af9f13` (the template's HDMI defaults). UI `controls`: `c9d841f` (the writers removed), `7c41a27` (the HDMI fallback). KB: the browser test and the host tests (`controls_store_test.cpp` 52 checks, Linux only). Not pushed to GitHub.

## 7. If it went wrong

| You see | It means | Do |
| --- | --- | --- |
| 409 "Apertar was updated" | the tab was open before the update | reload the page |
| 409 "The file changed since you loaded it" | someone saved after you loaded | copy your text, Reload Config, redo the edit |
| 400 "Not saved: N new errors" | the text adds an error; the box names the lines | fix them, or save by script with `force` |
| the file is missing | moved or lost | `set_controls base=h0000000000000000 restore=true` |
| the UI will not start | a build problem | `git switch cinemate-port` in `~/ApertarUI`, rebuild, restart |

## 8. What you learned, going further

- A version header turns a silent overwrite into a visible refusal.
- A default file written by a second program is a revert waiting to happen: one owner, one place.
- Exercise: send a 300 KiB text to the Config page. Which limit stops it first?
- Next: T39, save and it works: Core restarts only what changed, never inside a command, never during a take.

## 9. Sources

`working/controls/design-controls.md` §3.4, §6 (T38), §7 (T38); `working/controls/decisions.md` (Q3, Q5, Q17); Core `controls`, UI `controls`; `working/tools/controls_config_page_test.js`, `controls_store_test.cpp`.

%% tutor
ref core src/ApertarCoreApp.cpp 5715 std::string buildHardwareConfigFileJson()
ref core src/ApertarCoreApp.cpp 5765 bool checkHardwareConfigText(const std::string &text, std::string *errorMessage)
ref core src/ApertarCoreApp.cpp 8043 const auto revisionHeader = request.headers.find("x-apertar-revision");
ref core src/hardware/HardwareConfigStore.cpp 416 ReplacedInfo HardwareConfigStore::replacedByDefault() const
ref core src/ipc/ControlServer.cpp 16 constexpr size_t kMaxRequestLineBytes = 1024 * 1024;
ref core src/web/WebControlPage.cpp 14193 function showConfigIssues(title, issues) {
ref core src/web/WebControlPage.cpp 14262 async function saveConfigFile() {
ref ui src/DisplayConfigBridge.cpp 17 QString defaultHardwareConfigPath()
ref ui src/Ina219Bridge.cpp 45 QString defaultHardwareConfigPath()
check 3.1 | git -C /home/pi/ApertarUI show 7029db1:src/DisplayConfigBridge.cpp | bus=10
check 3.2 | git -C /home/pi/ApertarCore show 4d80a35:src/ipc/ControlServer.cpp | 64 \* 1024
check 4.1 | curl -s -m 3 -X POST http://127.0.0.1:8000/api/command -d '{"cmd":"get_controls"}' | "revision":"h[0-9a-f]{16}"
check 4.2 | grep -c 'X-Apertar-Revision' /home/pi/ApertarCore/src/web/WebControlPage.cpp | ^[1-9]
check 4.3 | grep -c 'replacedByDefault' /home/pi/ApertarCore/src/hardware/HardwareConfigStore.cpp | ^[1-9]
check 4.4 | grep -c 'ensureDefaultHardwareConfigFile' /home/pi/ApertarUI/src/DisplayConfigBridge.cpp | ^0$
check 4.5 | grep -c 'ensureDefaultHardwareConfigFile' /home/pi/ApertarUI/src/Ina219Bridge.cpp | ^0$
check 5.1 | curl -s -m 3 -X POST http://127.0.0.1:8000/api/command -d '{"cmd":"get_controls"}' | "ok":true
%%

#CINEMATE
#APERTAR
