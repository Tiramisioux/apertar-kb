# Tutorials

Patrik learns Apertar by making each change himself. So when a problem comes up, the
`apertar-dev` skill writes a tutorial **first**. It does not make the change itself unless Patrik
asks it to ("just do it", "fix it for me").

## Where tutorials live

Obsidian vault `Patrik Obsidian`, folder `02_PROJEKT/CINEMATE/APERTAR/notes/`.
Disk path: `~/local anteckningar/obsidian vaults/Patrik Obsidian/02_PROJEKT/CINEMATE/APERTAR/notes/`.

- File name: `<YYYYMMDDHHMMSS> CINEMATE APERTAR <topic>.md`, topic in kebab-case or snake_case.
- Frontmatter, exactly these keys (the APERTAR hub picks the note up via `projekt`):

```yaml
---
datum: 2026-10-25 18:00:00
kontext: CINEMATE
projekt: "#APERTAR"
fritext: <topic>
typ: digital anteckning
---
```

- End the note with the tags `#CINEMATE` and `#APERTAR` on their own lines.
- **Written on the Pi?** The vault isn't there. Claude saves the note, already named and formatted as
  above, in `~/apertar-kb/tutorials/inbox/`. After the next KB sync the Mac side moves each inbox file
  into the vault folder (`git mv` out of `inbox/` is wrong: the vault isn't in the repo; copy, then
  `git rm` the inbox copy) and adds the index row.
- Obsidian syntax: callouts `> [!note]`, collapsible answers `> [!tip]- Answer`, wikilinks
  `[[file name|label]]`. Not MkDocs `!!!`.
- Never rename a folder by case only (Syncthing `_CaseConflict` trap).

## Shape of a tutorial

Reference example: `20261025152945 CINEMATE APERTAR start-tutorials` (the I2C/DPI diagnosis). It
shows the depth wanted: a rig table, the exact symptom output, the evidence with `path:line`
refs, the resolution, the side effects, what upstream could change, open questions, sources.
A learning tutorial adds the doing: Patrik runs and types every step.

| # | Section | Contents |
| --- | --- | --- |
| 0 | Header | Title = the outcome ("Make HDMI the touch screen at 1080p"). One status line. **You will learn** (2-4 bullets). **Risk** (reboot? `config.txt`? can it brick boot? how to undo). Time estimate |
| 1 | The problem | Exact symptom, command output in a code block, what was expected |
| 2 | How this part works | The mental model in under a page. Diagram if it helps. "Open `src/…/X.cpp` and read lines A-B" reading assignments |
| 3 | Find it yourself | Guided checks. Each: command, **prediction** ("you should see…"), a question. Answers in collapsed `> [!tip]- Answer` callouts so they don't spoil |
| 4 | Make the change | Numbered steps. File, location (`path:line`, plus a search string in case lines moved), the change and why. Show the target code; Patrik types it. One **Check:** per step |
| 5 | Build, deploy, test | Exact commands (VS Code task names too), expected output, what success looks like on the camera |
| 6 | Commit and push | Which machine, `git add <files>`, the full commit message in house format, `git push`, then `apertar_status.sh` |
| 7 | If it went wrong | Table: what you see / what it means / what to do. Always includes how to undo |
| 8 | What you learned, going further | Recap. 1-2 follow-up exercises. Upstream issue/PR it could become |
| 9 | Sources | Files with commit/release, docs, datasheets, KB pages |

Rules:

- Commands are copy-pasteable, one per line, with a comment saying what each proves.
- `path:line` refs name the version (`upstream-1.6.0` or a fork sha). Add a grep string as backup.
- Mark anything not verified on this Pi **unconfirmed**, with the command that would settle it.
- Never put the Pi password or any token in a tutorial.
- Short sentences. Tables over prose. No scene-setting intro.

## Step numbers and the tutor block

So the tutor (`apertar-dev`, Mac or Pi) can check a tutorial and Patrik's progress, every new
tutorial has:

- **Numbered steps** in sections 3 and 4: a bold line starting with the number,
  `**3.1 Is anyone home?**`, `**4.2 Find where it was saved** (Pi):`. "I'm at 4.2" then means one thing.
- A **tutor block** just above the closing tags. Obsidian hides `%% … %%` in reading view:

```
%% tutor
ref core src/ApertarCoreApp.cpp 9091 std::string ApertarCoreApp::handleCommand
ref ui src/ApertarControlBridge.cpp 1013 bool ApertarControlBridge::sendCoreCommand
check 3.1 | curl -s -m 3 -X POST http://127.0.0.1:8000/api/command -d '{"cmd":"ping"}' | "pong":true
check 4.1 | grep -n 'label: "CODEC"' /home/pi/ApertarUI/qml/CameraPage.qml | CODEC
%%
```

| Line | Format | Rules |
| --- | --- | --- |
| `ref` | `ref <core\|ui\|drv> <repo path> <line> <literal anchor>` | One per `path:line` the note asks him to read or edit. The anchor = a literal string that occurs once in that file (rest of the line) |
| `check` | `check <step> \| <command> \| <expected regex>` | The step's **Check:** as a command that runs **on the Pi** (`127.0.0.1`, `/home/pi/…`). Read-only only: `tutorial.py` refuses anything else (no `set_*`, no `sudo`, no `>`, no `git checkout`). For a code change, check the source file or `git diff`, not the running camera |

Check it before handing the note over (the Mac: notes in Obsidian; the Pi: `~/apertar-tutorials`):

```bash
python3 ~/Documents/Apertar/apertar-kb/tutorials/tutorial.py refs T01     # every ref still at its line on the Pi tree
python3 ~/Documents/Apertar/apertar-kb/tutorials/tutorial.py show T01     # outline, checks, progress
```

Working through a tutorial together: `llm/tutoring.md` §7. Progress lives in
`tutorials/progress/<ID>.md` (written by `tutorial.py log`, committed in the KB).

## Index

The planned order (learning path T01-T15, with the mental model each builds) is in
`llm/tutoring.md` §5 and, for Patrik, in the Obsidian note
`20261025190000 CINEMATE APERTAR learning-path`. Keep both in step with this table.

| Date | Note | Topic | Status |
| --- | --- | --- | --- |
| 2026-10-23 | `20261025152945 CINEMATE APERTAR start-tutorials` | I2C bus 1 missing: DPI overlays, CFE hat Qwiic hub, NeoRotary 4 | Done on hardware, confirmed |
| 2026-10-25 | `20261025191000 CINEMATE APERTAR T01 talk-to-core` | T01: the command protocol by hand (curl + Python socket) | written |
| 2026-10-25 | `20261025190927 CINEMATE APERTAR clearhdr16-tutorial` | **T16.** 16-bit Clear HDR on the IMX585, Steps 0-8 (WDR switch, 16-bit raw path, HDR knobs, guards, UI). External workbook (Downloads). Checked on the Pi 2026-10-25: Core/UI refs valid; driver refs are Apertar-Studio `main`, and on `e5b74d3` WDR=1 still offers 12-bit (mode [10]); callout + tutor block added | written |
| 2026-10-25 | `20261025193414 CINEMATE APERTAR tally-gpio21-tutorial` | **T17.** Tally LED on GPIO 21: which definition wins, polarity, wiring test. External workbook (Downloads). Pi-checked: GPIO 21 is the trigger output's pin on this rig; callout + tutor block added | written |
| 2026-10-25 | `20261025193415 CINEMATE APERTAR media-yank-tutorial` | **T18.** Yanked card/drive: `media_mounted` = alive, record gates, abort on removal, CFE surprise removal, USB remount. External workbook (Downloads). Pi-checked: refs valid, Step 0 and the automounter install corrected in the callout; tutor block added | written |
| 2026-10-25 | `20261025194053 CINEMATE APERTAR T19 list-sensor-modes` | **T19.** Core reports the sensor's real modes (`list_sensor_modes`, from libcamera's Raw stream formats); first step from hard-coded mode lists to the Cinemate model | written |

Status values: `written` → `in progress` → `done` (Patrik did it) → `confirmed` (result on hardware,
logged in `lessons/hardware-log.md`).
