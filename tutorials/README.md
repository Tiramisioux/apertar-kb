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

## Index

The planned order (learning path T01-T15, with the mental model each builds) is in
`llm/tutoring.md` §5 and, for Patrik, in the Obsidian note
`20261025190000 CINEMATE APERTAR learning-path`. Keep both in step with this table.

| Date | Note | Topic | Status |
| --- | --- | --- | --- |
| 2026-10-23 | `20261025152945 CINEMATE APERTAR start-tutorials` | I2C bus 1 missing: DPI overlays, CFE hat Qwiic hub, NeoRotary 4 | Done on hardware, confirmed |
| 2026-10-25 | `20261025191000 CINEMATE APERTAR T01 talk-to-core` | T01: the command protocol by hand (curl + Python socket) | written |

Status values: `written` → `in progress` → `done` (Patrik did it) → `confirmed` (result on hardware,
logged in `lessons/hardware-log.md`).
