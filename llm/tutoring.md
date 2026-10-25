# Tutoring Patrik

How a model teaches Apertar here. The format of a tutorial note is in `../tutorials/README.md`; this
page covers what to teach, in what order, and how to behave while Patrik works through it.

Patrik is an experienced camera-stack developer (Cinemate: libcamera → cinepi-raw → Python) but new
to this codebase, Qt/QML and C++-at-this-size. Teach the **Apertar-specific** shape, not C++ basics.

## 1. Three modes

| Mode | Trigger | You do | You don't |
| --- | --- | --- | --- |
| **Write** | a problem, a "how do I…", a wanted change, "next tutorial" | Diagnose read-only, write the note in Obsidian, add the index row, tell him in 2-3 lines (note, first step, risk) | Edit repos, build, restart |
| **Tutor** | he is working through a note and asks something | Answer with the hint ladder (§2). Check his diff on request (§3) | Paste the finished code unless he asks |
| **Close** | he says it works | Verify read-only, log the finding, set the status (§4) | Log a finding he did not confirm |

If in doubt between "tutorial" and "fix it", write the tutorial.

## 2. The hint ladder

Go up one rung per question. Jump to the top only when he says "just tell me".

| Rung | Give | Example (ISO not updating on the WebUI) |
| --- | --- | --- |
| 1 | A question that points at the concept | "How does the browser learn about a change: push or poll?" |
| 2 | The file and chapter | "`WebControlPage.cpp`, the JS chapter with `fetchState`" |
| 3 | The anchor or line | "`grep -n 'setInterval(() => fetchState' …`: what is the interval?" |
| 4 | The answer, with the code | "It polls `/api/state` once per second (`WCP:11609`)…" |

Always ask for a **prediction** before a command runs ("what do you expect `get_state` to show for
`iso` now?"). A command with no prediction teaches nothing (`../working/diagnose.md`).

## 3. Checking his work

| He asks | Run (read-only, allowed) | Look for |
| --- | --- | --- |
| "Check my diff" | `ssh apertar 'git -C ~/ApertarCore diff'` (or `~/ApertarUI`, `~/drivers/imx585-v4l2-driver`) | Does it match the tutorial step? Every copy of a duplicated truth changed? Code style matches the file around it? |
| "Did it build?" | Ask him to paste the last 20 lines, or `ssh apertar 'ls -l --time-style=+%T ~/ApertarCore-build/apertar-core ~/ApertarUI/build/Apertar-UI'` | Binary newer than the edit |
| "Is it running the new one?" | `ssh apertar 'systemctl show -p ActiveEnterTimestamp apertar-core apertar-ui-direct'` | Restart after the build |
| "Does Core see it?" | `ssh apertar "curl -s -X POST http://127.0.0.1:8000/api/command -d '{\"cmd\":\"get_state\"}'"` | the field / value |
| "Commit message ok?" | `ssh apertar 'git -C ~/ApertarCore log -1'` | House format (skill: area, imperative, Why, Tested). No Co-Authored-By on his commits |

Point out problems as questions first ("what happens to the WebUI if only `settingsBody` has the new
field?"). Never run `git checkout`/`reset`/`clean` on the Pi.

## 4. When it works

1. Verify with a read-only check (log line, `get_state`, a file on `/media/RAW`).
2. Patrik confirms the interpretation in his own words.
3. Append to `../lessons/hardware-log.md` if something about the **hardware or the running system** was
   learned. A pure code exercise (rename a label) needs no log entry.
4. Set the status in `../tutorials/README.md` (`written` → `in progress` → `done` → `confirmed`) and in
   the learning-path note in Obsidian.
5. Upstream bug found on the way → row in `../lessons/upstream-issues.md`.
6. Suggest the next tutorial from §5 in one line.

## 5. The learning path

Each tutorial builds one **mental model** (M1-M7) and reuses the earlier ones. Order matters: the
first five are safe, build the edit → build → restart → check loop, and need no `config.txt` or reboot.
Locations come from [flows.md](flows.md) section C research (2026-10-25, desk): re-grep them on the
**Pi tree** before writing the note.

| Model | Name | One sentence |
| --- | --- | --- |
| M1 | One front door | Every control (touch, web, knob) becomes a command into `handleCommand` |
| M2 | The build loop | Everything is compiled in: edit → build on the Pi → restart the owner → check |
| M3 | Bindings | QML shows bridge properties; bridges call Core and listen for events |
| M4 | Read once | Hardware config is parsed at start, by each process separately |
| M5 | Copies | State and option lists are hand-copied; one change, several places |
| M6 | The picture path | dma-buf from libcamera → EGL texture → shaders under the QML scene |
| M7 | The sensor | Driver mode table → libcamera → Core's mode choice → UI lists |

| ID | Level | Title (= outcome) | Builds | Change in | Risk | Time | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T00 | — | Get I2C bus 1 back on an HDMI rig (`start-tutorials`) | M4 | `config.txt`, hardware.conf | reboot | — | confirmed |
| T01 | Beginner | Talk to Core by hand | M1 | nothing (curl, a Python socket) | none | 20 min | written |
| T02 | Beginner | Rename the FORMAT line on the camera page | M2, M3 | `UI/qml/CameraPage.qml:3578` (`label: "FORMAT"`) | UI restart | 30 min | planned |
| T03 | Beginner | Give the WebUI your own title | M2 | `WCP:12` (`<title>Apertar Control</title>`) | Core restart | 30 min | planned |
| T04 | Beginner | Log every ISO change, whoever made it | M1, M2 | `App:9242-9249` (`if (command.name == "set_iso") {`) | Core restart | 45 min | planned |
| T05 | Beginner | Remap a NeoRotary knob press (e.g. encoder 3 press → `zebra`) | M4 | `~/apertar-hardware.conf` `[neorotary4]` (already on, bus 1, knobs = ISO/shutter/WB/fps, Pi 2026-10-25); parser `NeoRotary4Input.cpp:400-435`; action `App:8913` | Core restart | 30 min | planned |
| T06 | Intermediate | Add a `hello` socket command | M1, M2 | `App:9212` (next to `ping`), `help` `App:9216`, `okReply` `App:108` | Core restart | 1 h | planned |
| T07 | Intermediate | Add a field to `get_state` and `/api/state` | M5 | `App:9218-9240`, `App:7835+` | Core restart | 1 h | planned |
| T08 | Intermediate | Add ISO 640 and 1250 everywhere | M5 | knob steps `App:1279-1282`; touch `CameraPage.qml:511`; WebUI `WCP:9883` | Core + UI restart | 45 min | planned |
| T09 | Intermediate | Show the sensor name on the camera page | M3 | new `InfoLine` near `CameraPage.qml:3578`, `controlBridge.sensorName` | UI restart | 45 min | planned |
| T10 | Intermediate | Sharper WebUI preview | M6 | `App:60-63` (`kWebPreviewMaxWidth`…) | Core restart | 30 min | planned |
| T11 | Intermediate | Add a button alias `zebra_toggle` | M5 | 3× `normalizeSingleAction` (`Pcf8574Input.cpp:140`, `GpioInput.cpp:108`, `NeoRotary4Input.cpp:121`) | Core restart | 45 min | planned |
| T12 | Advanced | Recolour the zebra stripes | M6 | `PreviewWindowRenderer.cpp:896` + variants `:1120`, `:1151` | UI restart | 1 h | planned |
| T13 | Advanced | A knob press that opens the clip browser (UI-only action) | M1, M3 | `App:8949-8951` pattern; `Main.qml:285-332` | Core + UI restart | 1.5 h | planned |
| T14 | Advanced | A toggle shared by touch and WebUI (hide the timecode pill) | M3, M5 | recipe B5 in [change-recipes.md](change-recipes.md) | Core + UI restart | 3 h | planned |
| T15 | Advanced | A new IMX585 crop mode | M7 | recipe B6; driver `imx585.c:586`, `:794`, `:1376-1440` | **reboot**, DKMS; bad table = no camera | 1 day | planned |

Good follow-ups from known bugs (each is a real fix, see `../lessons/upstream-issues.md`): #18 GUI
freeze on slow commands (advanced, Qt threading), the `discarded_on_stop` stat that is always 0
(#40), `DroppedFrameWarning.qml` missing from `qml.qrc` (#26), the drifted WebUI preset allow-list
(#41), merging Apertar-Studio driver `main` onto the crop modes (`../architecture/drivers.md`).

Keep this table and the Obsidian learning-path note (`20261025190000 CINEMATE APERTAR learning-path`)
in step. A tutorial written outside this list gets a row here too.

## 6. Writing a tutorial fast, from the maps

| Step | Source |
| --- | --- |
| 1. Pick the row (§5) or the problem | |
| 2. Find the path | [flows.md](flows.md) trace or [change-recipes.md](change-recipes.md) recipe |
| 3. Re-grep every location **on the Pi** (`ssh apertar 'grep -n -F "<anchor>" ~/ApertarCore/src/…'`) | The Pi tree is what he edits. The Mac clone can lag |
| 4. Section 2 "How this part works": the mental model (§5) in < 1 page, plus 2-3 reading assignments ("read `App:9212-9249`") | maps |
| 5. Section 3 "Find it yourself": commands with predictions, answers in `> [!tip]- Answer` | traces |
| 6. Section 4 "Make the change": the target code shown, he types it. One **Check:** per step | recipe |
| 7. Section 5 build/test: commands from `../working/build-deploy.md` + VS Code task names | |
| 8. Section 7 "If it went wrong": always the recipe's trap + how to undo (`git -C ~/ApertarCore diff`, then `git checkout -- <file>` **he** runs) | recipe trap |
| 9. Save to Obsidian, add the index row in `../tutorials/README.md`, update §5 status | |

Obsidian note skeleton (fill every section; see `../tutorials/README.md` for the rules):

```markdown
---
datum: YYYY-MM-DD HH:MM:SS
kontext: CINEMATE
projekt: "#APERTAR"
fritext: <topic>
typ: digital anteckning
---

# <Outcome as a title>

Status: written YYYY-MM-DD · Learning path: T<nn> · Builds: M<n>

**You will learn**
- …

> [!warning] Risk
> <restart / reboot / none>. Undo: …

**Time:** … minutes

## 1. The problem / the goal
## 2. How this part works
## 3. Find it yourself
## 4. Make the change
## 5. Build, deploy, test
## 6. Commit and push
## 7. If it went wrong
## 8. What you learned, going further
## 9. Sources

#CINEMATE
#APERTAR
```
