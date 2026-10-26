# Tutoring Patrik

How a model teaches Apertar here. The format of a tutorial note is in `../tutorials/README.md`; this
page covers what to teach, in what order, and how to behave while Patrik works through it.

Patrik is an experienced camera-stack developer (Cinemate: libcamera → cinepi-raw → Python) but new
to this codebase, Qt/QML and C++-at-this-size. Teach the **Apertar-specific** shape, not C++ basics.

## 1. Three modes

| Mode | Trigger | You do | You don't |
| --- | --- | --- | --- |
| **Write** | a problem, a "how do I…", a wanted change, "next tutorial" | Diagnose read-only, write the note in Obsidian, add the index row, tell him in 2-3 lines (note, first step, risk) | Edit repos, build, restart |
| **Tutor** | "work with me on T01", or he asks something mid-tutorial | Run the session protocol (§7): `tutorial.py show/refs/check/log`, hint ladder (§2), diff checks (§3) | Paste the finished code unless he asks |
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
| T16 | Project | 16-bit Clear HDR on the IMX585 (`clearhdr16-tutorial`, imported workbook, Steps 0-8) | M1-M7 | Core (setting, WDR write, 16-bit path, knobs, guards) + UI + WebUI; Step 1 bench with `v4l2-ctl` | Core stop/restart; WDR writes; no `config.txt`. Pi-checked 2026-10-25: driver refs and the "WDR ⇒ 16-bit only" premise differ on `e5b74d3` (note's callout) | days | written |
| T17 | Intermediate | A tally LED on GPIO 21 (`tally-gpio21-tutorial`, imported, Steps 1-6) | M4 | `~/apertar-hardware.conf` only (code reading); Step 4 `pinctrl` with Core stopped. Pi-checked: GPIO 21 is held by `[trigger_output]`, the enabled `[recording_indicator]` points at a PCF8574 that isn't on bus 10 (note's callout). Done 2026-10-25: section route, `active_high=true`; note now in `APERTAR/_archive/` | Core restart | 45 min | confirmed |
| T18 | Project | Surviving a yanked card or drive (`media-yank-tutorial`, imported, Steps 0-8) | M1, M2, M5 | Core (`mediaRootAlive`, record gates, abort), CFE automounter (surprise removal), USB remount. Pi-checked: refs valid; Step 0 paths/build dirs wrong for this Pi; Step 5 needs the `/usr/local/libexec` install | Core/UI/automounter restarts; yanking media | days | written |
| T19 | Intermediate | Ask the sensor: a `list_sensor_modes` command (libcamera's real modes via Core) | M1, M2, M7 | `CameraController.hpp` (struct + accessor), `CameraController.cpp` (`start()` keeps `generateConfiguration({Raw}).formats()`, `:5375`; getter like `sensorName()`, `:8576`), `ApertarCoreApp.cpp` (handler next to `ping`, `:9212`; `help`) | Core restart | 2 h | written |
| T20 | Intermediate | The WebUI "records" with no drive (`webui-false-recording-tutorial`, imported; WebUI half of T18) | M1, M5 | `WebControlPage.cpp` (record button `disabled` rule, `media_state` display) + Core `buildWebStateJson`. Needs T18 Step 2 first. Pi-checked: WebUI/UI refs valid, Core lines shifted by the Clear HDR commit (note's box) | Core restart | 1.5 h | written |
| T21 | Intermediate | Why the WebUI "Time left" disagrees with HDMI (`webui-time-left-investigation`, imported; investigation + fix) | M5 | Core `estimatedRawBytesPerSecond` ported from the QML model, truthful `time_left_label`. Pi-checked: with 16-bit Clear HDR the WebUI now over-reports (note's box) | Core restart | 2 h | written |
| T22 | Intermediate | Where Clear HDR frames are lost (`clearhdr-drops-measure`): CSI-2 counters, writeback vs direct, tmpfs, knob test | M7 | `cmdline.txt` token, measurement only; tools `writeback_watch.py`, `ipa_rate.py`, `takes.sh` | **reboot** once; sudo for debugfs | 2 h | written |
| T23 | Intermediate | One request per raw buffer, 8 in Clear HDR, warm pool (`requests-follow-buffers`) | M7 | `CC:1047-1048`, `:1154`, `:6411`, `:6796`, `:3596`, `:3992`,  `:6666` | Core restart | 1.5 h | written |
| T24 | Advanced | Direct I/O for uncompressed cDNG (`cdng-direct-io`) | writer path | `src/cdng/CdngEncoder.{hpp,cpp}` (`:1235`, `:1388`, `:1458`, `:1748-1779`, `:1861`), `CC:3028`, `:3843`, `:7268` | Core restart; `APERTAR_CDNG_DIRECT_IO=0` to undo | 3-4 h | written |
| T25 | Advanced | Raw copy off libcamera's completion thread (`raw-copy-off-completion-thread`) | M7, threads | `CC:4799` pattern, `:5757` stop order, `:6762`, `:6833`, `:6915`, `:7189` | Core restart; threading | 4-6 h | written |
| T26 | Advanced | Driver reports each mode's sensor window (`driver-crop-rectangles`) | M7 | `drv/imx585.c:794-1200` `.crop` values; `:560`, `:2129`, `:2374` | **reboot**, DKMS; bad table = no camera | 1.5 h | written |
| T27 | Advanced | Frame-rate phase lock (`frame-rate-phase-lock`): cadence measurement, host simulation, HMAX hazard, enable | M7, clocks | `src/camera/FramePhaseLock.hpp`, `CC:7147`, `:7263`, `:6123`, `:6290`, `Types.hpp:127`, `App:9631`; tool `phase_lock_sim.cpp` | Core restart; setting off by default | 3 h | written |
| T28 | Advanced | Yanked media (`yanked-media-robustness`): watcher, errno classes, clean stop, gate, event, eject intent | M5, M6 | `src/util/Media{Fault,Probe,Intent}.hpp`, `CC:3560`, `:4069`, `:6273`, `:9370`, `App:9151-9240`, `:9249`; tool `media_probe_test.cpp` | Core restart; one pull test on a scratch card | 4 h | written |
| T29 | Advanced | Media profile (`media-profile`): class + filesystem, writer table, root helper, on/off comparison | M5, M7, root helper | `src/util/MediaProfile.hpp`, `CC:1173`, `:3492`, `:3922`, `:6273`, `App:9273`, `scripts/apertar-media-tune`; tool `media_profile_test.cpp` | Core restart; sudoers + tmpfiles install | 4 h + takes | written |
| T30 | Intermediate | Audio writer thread + 1 s ring (`audio-writer-thread`) | M5 | `src/audio/AudioRecordingSession.cpp:694-730`, `:359`, `TimestampedAudioCapture.cpp:195-218` | Core restart; `APERTAR_AUDIO_BUFFER_MS=100` to undo | 2 h | written |

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
| 9. Number the steps (`**4.1 …**`) and write the `%% tutor` block: a `ref` per code location, a `check` per **Check:** (format: `../tutorials/README.md`) | |
| 10. `python3 ../tutorials/tutorial.py refs <ID>` → all OK; run each `check` once to see it FAIL before the change (a check that already passes proves nothing) | |
| 11. Save to Obsidian, add the index row in `../tutorials/README.md`, update §5 status | |

Obsidian note skeleton (fill every section; see `../tutorials/README.md` for the rules, including
the tutor block that goes above the tags):

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

%% tutor
ref core src/… <line> <literal anchor>
check 4.1 | <read-only command, run on the Pi> | <expected regex>
%%

#CINEMATE
#APERTAR
```

## 7. Working through a tutorial together

Trigger: "work with me on T01", "let's do the talk-to-core tutorial", "I'm at 4.2", "continue T03".
The helper is `../tutorials/tutorial.py` (Mac: `~/Documents/Apertar/apertar-kb/tutorials/tutorial.py`;
Pi: `~/apertar-kb/tutorials/tutorial.py`). It reads the note, runs only read-only checks, and
writes only the progress log.

**Open the session**

| # | Do | Command |
| --- | --- | --- |
| 1 | Find the note, its outline, its checks, where he left off | `tutorial.py show T01` (an ID or a name fragment) |
| 2 | Are the note's code refs still true on the Pi tree? | `tutorial.py refs T01`. MOVED/MISSING → fix the note first (Mac: edit the Obsidian note; Pi: the mirror is read-only, so log `ref-fix` with the new line and tell him) |
| 3 | Is the Pi tree as the tutorial expects? | `ssh apertar 'git -C ~/ApertarCore status -s; git -C ~/ApertarUI status -s'`. A dirty tree may be **his** work in progress: ask, never clean it |
| 4 | Tell him in 2-3 lines: where he is, the next step, its risk | e.g. "Last time: 3.4 done. Next: 4.1, one ISO change, harmless. Ready?" |
| 5 | Log the start the first time | `tutorial.py log T01 - started` |

**Each step**

1. Quote only that step's commands and question. Don't run ahead: the note has the rest.
2. Ask for his **prediction**. Wait for it.
3. He runs it. He pastes the output, or says "done".
4. Verify: `tutorial.py check T01 4.1` (PASS/FAIL + actual value). No check line for that step →
   verify by hand with a read-only command, and add a `check` line to the note afterwards.
5. FAIL → don't give the fix. Ask what the output says, then climb the hint ladder (§2).
6. Discuss the `> [!tip]- Answer` only after he has answered.
7. Log it: `tutorial.py log T01 4.1 done "<what he saw, in his words>"`. Hints:
   `… 4.1 hint2 "pointed at applyCoreState"`. Stuck → `stuck`. Skipped → `skipped`.

**Code-change steps**: compare `ssh apertar 'git -C ~/ApertarUI diff'` with the step's target code.
Point out a missing copy (M5) as a question. A build error: ask him to paste it and read it
together. Find the line, then the cause.

**Close the session** (he stops, or the tutorial is finished)

| Situation | Do |
| --- | --- |
| He stops midway | Log the last step. Commit the progress file: `git -C <KB> add tutorials/progress && git -C <KB> commit -m "kb: T01 progress"`. On the Pi, it reaches the Mac with the next `deploy_to_pi.sh` |
| Finished | `tutorial.py log T01 - finished "<recap in his words>"`, then §4 (verify, his confirmation, status in the three places) |
| The note was wrong or unclear | Fix it (Mac) or log `note-fix "<what>"` (Pi). Fix the KB page too if the KB was wrong |

Progress events: `started`, `done`, `hint1`-`hint4`, `stuck`, `skipped`, `ref-fix`, `note-fix`,
`finished`, `confirmed`. The hint counts show where the tutorial is too hard. Read them before
writing the next one.

