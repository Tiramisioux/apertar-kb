# LLM guide: how to find your way through Apertar

For language models (the `apertar-dev` skill, a subagent, a fresh session). It does three things:
it gets you to the right file and line without reading 10 000-line files whole, it lists the traps
that make changes "do nothing", and it says how to tutor Patrik.

Humans can read it too, but `../README.md` and the `architecture/` pages are the human-facing
reference. This folder is the index into them and into the code.

## 0. Start here (every session)

| Step | Do | Why |
| --- | --- | --- |
| 1 | Read this page, then `../README.md` (routing table) | 5 minutes, saves an hour |
| 2 | `~/.claude/skills/apertar-dev/scripts/apertar_status.sh` | The Pi may hold uncommitted edits. Mac clones are not proof of what runs |
| 3 | Check the line-ref baseline (§3) | Every `path:line` here is against `upstream-1.6.0` |
| 4 | Pick the page from §1 for your task | |
| 5 | Find code with the **chapter maps** (§2), not by reading files whole | `ApertarCoreApp.cpp` alone is ~140k tokens |
| 6 | Before telling Patrik anything works, verify on the Pi with a read-only check | Rule 1 of the skill: tutorial first, no edits |

## 1. Which page for which task

| Task | Open first | Then |
| --- | --- | --- |
| "Where is X in the code?" | [core-map.md](core-map.md) or [ui-map.md](ui-map.md) chapter tables | grep the anchor, read ~60 lines around it |
| "What happens when the operator does Y?" | [flows.md](flows.md) (7 traces, hop by hop) | `../architecture/overview.md` for the process picture |
| "How do I add / change Z?" | [change-recipes.md](change-recipes.md) | the "duplicated truths" sections in both maps |
| "Teach me / write a tutorial" | [tutoring.md](tutoring.md) (curriculum, tutor protocol, writing workflow) | `../tutorials/README.md` (format + index) |
| Something is broken | `../working/diagnose.md` | `../lessons/hardware-log.md`, `../lessons/upstream-issues.md` |
| A config key, env var, `UI.conf` | `../architecture/config.md` | |
| Build, restart, "my change did nothing" | `../architecture/build.md`, §5 traps below | |
| Sensor modes, driver | `../architecture/drivers.md` (read its 2026-10-25 update first) + [flows.md](flows.md) A6 | |
| Git across Mac / Pi / GitHub | `~/.claude/skills/apertar-dev/references/workspace-contract.md` | `../working/sync.md` |

## 2. Size map: what you can and cannot read whole

Line counts at `upstream-1.6.0`. Rough rule: 1 line ≈ 12 tokens of C++.

| File | Lines | Read whole? | Use |
| --- | --- | --- | --- |
| `Apertar-Core/src/web/WebControlPage.cpp` | 11 618 | **never** (HTML/CSS/JS in one C++ string) | [core-map.md](core-map.md) §1.3 |
| `Apertar-Core/src/ApertarCoreApp.cpp` | 11 025 | **never** | [core-map.md](core-map.md) §1.1, command table §2 |
| `Apertar-UI/qml/SettingsPage.qml` | 9 851 | **never** | [ui-map.md](ui-map.md) §1.1 |
| `Apertar-Core/src/camera/CameraController.cpp` | 8 834 | **never** | [core-map.md](core-map.md) §1.2 |
| `Apertar-UI/qml/CameraPage.qml` | 4 160 | no | [ui-map.md](ui-map.md) §1.2 (indentation trap) |
| `ApertarControlBridge.cpp`, `PreviewWindowRenderer.cpp`, `SettingsBridge.cpp`, `ClipPlayerPage.qml`, `Mpu6050RecordingSession.cpp` | 2 200-2 500 | only a chapter | maps |
| `imx585-v4l2-driver/imx585.c` | 2 705 | only a chapter | [flows.md](flows.md) A6, [change-recipes.md](change-recipes.md) B6 |
| Everything else | < 2 000 | yes, if needed | |

The method: chapter map → `grep -n '<anchor>' <file>` → `Read` with `offset` = hit − 20, `limit` = 80-150.
For a broad hunt across many files, hand it to an Explore subagent and keep only the conclusion.

## 3. Line references: baseline and drift

| Repo | Baseline | Check that the refs still hold |
| --- | --- | --- |
| Apertar-Core | tag `upstream-1.6.0` (`35dbe67`); fork HEAD `ed400ba` adds only build files | `git -C ~/Documents/Apertar/Apertar-Core diff --stat upstream-1.6.0 HEAD -- src include` → empty |
| Apertar-UI | tag `upstream-1.6.0` (`43888e5`); fork HEAD `29ed99b` adds only build files | `git -C ~/Documents/Apertar/Apertar-UI diff --stat upstream-1.6.0 HEAD -- src qml CMakeLists.txt` → empty |
| imx585 driver | branch `apertar`, `e5b74d3` | `git -C ~/Documents/Apertar/imx585-v4l2-driver log -1 --format=%h` |

- If the diff is not empty, line numbers may be off. The **anchor** column in every map is a literal
  string that survives drift: `grep -nF '<anchor>'`. Run `python3 check-anchors.py` to see which anchors
  still hit exactly once.
- `architecture/drivers.md`'s mode tables are for Apertar-Studio `main`, **not** the `apertar` branch
  the Pi runs. Trust [flows.md](flows.md) A6 / [change-recipes.md](change-recipes.md) B6 for driver lines.
- After an upstream release: run the upstream-sync procedure, then `check-anchors.py`, then fix the
  maps (§8).

Abbreviations used in the maps:

| Short | File |
| --- | --- |
| `App` | `Apertar-Core/src/ApertarCoreApp.cpp` |
| `CC` | `Apertar-Core/src/camera/CameraController.cpp` |
| `WCP` | `Apertar-Core/src/web/WebControlPage.cpp` |
| `CB` | `Apertar-UI/src/ApertarControlBridge.cpp` |
| `Core/`, `UI/`, `drv/` | the three repo roots |

## 4. The system in one screen

```
 touch (QML) ──> bridge (C++ Q_INVOKABLE) ──JSON line──> /tmp/apertar-core.sock ──┐
 WebUI (JS in Core) ──POST /api/command──────────────────────────────────────────>├─> App::handleCommand (one mutex)
 GPIO / PCF8574 / NeoRotary4 (Core poll threads) ──action name──> dispatch ───────┘        │
                                                                                         v
                                CameraController setter ─> controlsForSettings ─> libcamera request
                                        │                         (or reconfigure: full stream restart)
                                        ├─> camera_settings.conf (25 ms debounce)
                                        └─> "settings" event ─> broadcast to every socket client ─> UI properties
 UI.conf (~/.config/CinePi/UI.conf): aids, audio, photo, hotspot. Written by the UI AND by Core (for WebUI
 changes). No event: the UI notices by file watch.
 apertar-hardware.conf: read ONCE at start by Core, UI and the CFE automounter, each with its own parser.
```

Five facts that explain most behaviour:

1. **One entry point.** Touch, WebUI and hardware buttons all end in `handleCommand` (`App:9091`). Learn
   that function's shape and you can follow any control.
2. **Two settings stores.** Camera settings live in Core (`camera_settings.conf`, per record format).
   Monitoring aids and UI preferences live in `UI.conf`, which both processes edit.
3. **State is copied by hand.** The same camera fields are serialised in three places
   (`settingsBody`, `settingsEvent`, `buildWebStateJson`), and option lists (resolutions, fps caps,
   ISO steps) exist in 3-6 copies across QML, the bridge, Core and WebUI JS. See the
   "duplicated truths" tables.
4. **Everything is compiled in.** QML is AOT-compiled into the UI binary; the WebUI HTML/JS is a C++
   string in Core. Any edit needs a rebuild and a service restart.
5. **Config is read at start.** `apertar-hardware.conf` changes need a restart of the owning process.
   The WebUI's config editor saves the file but does not reload anything.

## 5. Traps that fool models

| # | Trap | What to do |
| --- | --- | --- |
| 1 | "CFE" means two things: the **CFexpress hat** (`apertar-cfe-automounter`, I2C 0x34) and **rp1-cfe**, the Pi 5 camera front end (kernel). | Say which one |
| 2 | `UI.conf` sits under `~/.config/CinePi/`: a legacy name, not the Cinemate project | Don't route to the cinemate skill |
| 3 | The Cinemate stack shares the imx585 fork and much vocabulary (ClearHDR, link frequency) but not code paths | Cite Cinemate findings as comparison only |
| 4 | QML edit + restart without rebuild = no change | `cmake --build ~/ApertarUI/build -j2` first |
| 5 | Helpers in `/usr/local/libexec` (automounter, standby, start gate) are copies; a build does not update them | `../architecture/build.md` |
| 6 | `/boot/firmware/apertar-hardware.conf` is dead once `/home/pi/apertar-hardware.conf` exists (the UI creates it on first start) | Edit `/home/pi/…` |
| 7 | The socket "JSON" parser is flat: every value is a string, nested objects/arrays break it | Send scalars |
| 8 | Every socket client receives every event, including per-frame `preview_frame` | Filter them when you script against the socket |
| 9 | The driver's `v4l2_find_nearest_size` never fails: a missing mode silently becomes the nearest one | Always read `stream=` in Core's `camera configured:` log line |
| 10 | Hardware-input errors go only to stderr (journal), never to the WebUI | `sudo journalctl -u apertar-core` |
| 11 | `pi` can't read the journal without sudo (not in `systemd-journal`) | Ask Patrik to paste, or to add the group once |
| 12 | `CameraPage.qml` drops to column 0 for ~1300 lines; indentation does not show block ends | Use the `// =====` banners |
| 13 | The UI sends `set_fps` / `set_resolution` by itself (`ensureValid*Selection`) when the sensor or format changes | Check those first when Core "changes on its own" |
| 14 | Settings are stored per record format (`profile.cdng.iso=` …) | A format switch can show different values |
| 15 | `SystemActionBridge::restartCamera()` reboots the Pi | Don't offer it as a "camera restart" |
| 16 | Unknown hardware action names only log `Hardware input action ignored: unknown action` | grep the journal |
| 17 | The Mac cannot build this stack (aarch64, Qt 6, libcamera 0.7) | Build on the Pi only |

## 6. Grep cookbook (cross-repo)

Run from `~/Documents/Apertar`. Use `grep -rnF` for literal strings.

| Need | Command |
| --- | --- |
| Where Core handles socket command `C` | `grep -n 'command.name == "C"' Apertar-Core/src/ApertarCoreApp.cpp` |
| Who sends command `C` | `grep -rnF '"C"' Apertar-UI/src Apertar-UI/qml Apertar-Core/src/web/WebControlPage.cpp` |
| An HTTP route | `grep -n 'request.path == "' Apertar-Core/src/ApertarCoreApp.cpp` |
| A field in `get_state` / events / `/api/state` | `grep -nF '\"iso\"' Apertar-Core/src/ApertarCoreApp.cpp Apertar-Core/src/camera/CameraController.cpp` |
| A `UI.conf` key on both sides | `grep -rnF 'zebraEnabled' Apertar-UI/src Apertar-Core/src` |
| A hardware-config key | `grep -rnF 'key == "poll_ms"' Apertar-Core/src` and `grep -rnF '"poll_ms"' Apertar-UI/src` |
| A hardware action | `grep -rnF '"iso_up"' Apertar-Core/src Apertar-UI/qml` |
| A log line you saw in the journal | `grep -rnF 'camera configured:' Apertar-Core/src Apertar-UI/src` (strip the variable parts first) |
| A QML caller of a bridge method | `grep -rnE '(apertarControlBridge\|controlBridge)\.applyIso\(' Apertar-UI/qml` |
| A Q_PROPERTY | `grep -n 'Q_PROPERTY' Apertar-UI/src/<Bridge>.hpp` |
| Settings item → Component | `grep -n '"zebra") return' Apertar-UI/qml/SettingsPage.qml` |
| An env var | `grep -rnF 'getenv("APERTAR_' Apertar-Core/src Apertar-UI/src` and `grep -rn 'APERTAR_' Apertar-UI/*.sh` |

More recipes: [core-map.md](core-map.md) §5, [ui-map.md](ui-map.md) §5.

## 7. Pi access, in short

The skill's table is the rule (`~/.claude/skills/apertar-dev/SKILL.md`). Additions:

| Read-only and fine | Why it is safe |
| --- | --- |
| `curl -s -X POST http://127.0.0.1:8000/api/command -d '{"cmd":"get_state"}'` over `ssh apertar` | `get_state`, `ping`, `help`, `get_media_test_state`, `audio_capabilities` change nothing |
| `curl -s http://127.0.0.1:8000/api/state` | read-only snapshot used by the WebUI |
| `cat ~/.config/CinePi/UI.conf`, `cat ~/.config/apertar-core/camera_settings.conf` | read-only |

Any `set_*`, `record_*`, `capture_photo`, `format_media`, `eject_media`, `apply_preset`, `POST /api/config`
is a **change**: only when Patrik asked for it.

## 8. Keeping this folder true

| When | Do |
| --- | --- |
| A map row turned out wrong | Fix the row now, note the commit in the KB message |
| After an upstream merge | `python3 check-anchors.py`; re-grep the lines of every anchor that moved; bump the baseline in §3 |
| A trace or recipe was walked on the Pi | Mark it **confirmed** with the date |
| A new trap bit you | Add it to §5 |

Labels: **confirmed** (code, log or Pi), **probable**, **unconfirmed** (+ the command that settles it).
Commit in the KB repo: `git -C ~/Documents/Apertar/apertar-kb commit -m "kb: …"`.

## Files in this folder

| File | Contents |
| --- | --- |
| [core-map.md](core-map.md) | Chapter maps of `ApertarCoreApp.cpp`, `CameraController.cpp`, `WebControlPage.cpp`; every socket command and HTTP route with its line; small-dir map; duplicated truths; grep recipes |
| [ui-map.md](ui-map.md) | Chapter maps of the big QML and C++ files; context properties; bridge properties and invokables → Core command; reverse index; duplicated truths; QML traps |
| [flows.md](flows.md) | Seven hop-by-hop traces: ISO, record (3 paths), WebUI → `UI.conf`, preview, encoder, boot + mode selection, still photo |
| [change-recipes.md](change-recipes.md) | Seven "touch these places" recipes with rebuild/restart and the trap for each |
| [tutoring.md](tutoring.md) | How to tutor Patrik; the learning path; how to turn a map into a tutorial |
| `check-anchors.py` | Checks that every anchor in the maps still hits |
