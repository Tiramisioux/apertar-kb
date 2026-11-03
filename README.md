# Apertar knowledge base

Git, with a **private** GitHub repo `Tiramisioux/apertar-kb` (since 2026-10-26). Three copies: the Mac
(`~/Documents/Apertar/apertar-kb`), the Pi (`~/apertar-kb`) and GitHub. `apertar_publish.sh` on the Mac
syncs all three (`working/sync.md`, "The KB on the Pi"); the Pi gets its copy via the Mac. Read by the `apertar-dev` skill before it diagnoses a problem or
writes a tutorial. Written for Patrik, who learns Apertar by making the changes himself.

## What lives where

| Folder | Holds | Rule |
| --- | --- | --- |
| `llm/` | **LLM guide**: entry page, chapter maps of the giant files, hop-by-hop flows, change recipes, tutoring + learning path, anchor checker | Models start at `llm/README.md`. Re-run `llm/check-anchors.py` after an upstream merge |
| `architecture/` | How Core, UI, config, build and drivers work, with `path:line` refs | Source-derived. Re-check refs after an upstream release |
| `working/` | How to do things: sync, build, deploy, diagnose | Procedures, tested on the Pi |
| `lessons/hardware-log.md` | Dated findings confirmed on the Pi | Append-only. Operator confirms before an entry goes in |
| `lessons/upstream-issues.md` | Bugs and rough edges found in Apertar-Studio's code | Candidate issues/PRs for upstream |
| `tutorials/README.md` | Tutorial format and the index of every tutorial written | Tutorials themselves live in Obsidian |
| `sources/` | Raw notes and handoffs this KB was built from | Frozen copies. Don't edit; supersede in the pages above |

The human manual (conventions, how to update GitHub) is the Obsidian note
`02_PROJEKT/CINEMATE/APERTAR/notes/20261025180000 CINEMATE APERTAR manual.md`.

## Routing: where to look first

| Question | Open |
| --- | --- |
| I'm a model, new here | `llm/README.md` |
| Where is X in the code (line, function)? | `llm/core-map.md`, `llm/ui-map.md` |
| What happens, hop by hop, when the operator does Y? | `llm/flows.md` |
| How do I add or change Z, and what will I forget? | `llm/change-recipes.md` |
| What should Patrik learn next? How to tutor him? | `llm/tutoring.md` |
| Which process does X? Who owns a bug? | `architecture/overview.md` |
| A recording, sensor, format or socket-command problem | `architecture/core.md` |
| A screen, touch, HDMI or QML problem | `architecture/ui.md` |
| What does key K in `apertar-hardware.conf` do? | `architecture/config.md` |
| How do I rebuild and restart component C? | `architecture/build.md`, `working/build-deploy.md` |
| Sensor modes, overlays, the imx585 driver | `architecture/drivers.md` |
| Keep Mac, Pi and GitHub in sync | `working/sync.md` |
| Merge a new Apertar-Studio release | `working/upstream-sync.md` |
| Make a distribution image from the Pi | `working/distribution-image.md` (draft) |
| Something is broken, where do I start | `working/diagnose.md`, then `lessons/hardware-log.md` |
| Has this been seen before? | `lessons/hardware-log.md`, `sources/` |
| How do my forks differ from Apertar-Studio? What went upstream? | `fork-log.md` |
| Why does Apertar drop more frames than CineMate, and what to port (incl. CineMate Log) | `working/drop-frames/README.md`, then `working/handoff-drop-frames.md` |
| How the two DNG write chains compare, why 4K Clear HDR 16-bit and 4K 50 fps still drop, what the drop-frames work changed, whether the pre-roll matters | `working/dng-chain-answer.md`, then `working/dng-chain/STATUS.md` |
| Can Apertar record drop-free at 4K SDR 50 fps and Clear HDR 16-bit 25 fps, under which conditions, and which measurement decides it | `working/dng-chain-feasibility.md`, then `working/dng-chain/F/` |
| Why the 4K 16-bit Clear HDR preview flickers (and Cinemate's does not), and how to find the stage | `working/clearhdr16-preview.md`, then tutorial T55 |

## Writing rules

- Observations and conclusions stay separate. Label claims **confirmed** (seen in code, logs or
  on the Pi), **probable**, or **unconfirmed** (say which command would settle it).
- Every code claim carries a `path:line` ref against a named commit or release (`upstream-1.6.0`).
- Short sentences, tables over prose.
- A finding only enters `lessons/hardware-log.md` after Patrik confirms the interpretation, not
  just after a command ran.

## The stack at a glance

| Repo (Mac, `~/Documents/Apertar/`) | Pi path | GitHub (push) | Upstream (fetch only) |
| --- | --- | --- | --- |
| `Apertar-Core` | `~/ApertarCore` (build: `~/ApertarCore-build`) | `Tiramisioux/Apertar-Core` | `Apertar-Studio/Apertar-Core` |
| `Apertar-UI` | `~/ApertarUI` (build: `~/ApertarUI/build`) | `Tiramisioux/Apertar-UI` | `Apertar-Studio/Apertar-UI` |
| `imx585-v4l2-driver` | `~/drivers/imx585-v4l2-driver` (DKMS) | `Tiramisioux/imx585-v4l2-driver`, branch **`apertar`** | `Apertar-Studio/imx585-v4l2-driver`; `will` = will127534 |
| `Apertar-Beta` | (the image itself) | reference only | `Apertar-Studio/Apertar-Beta` |
| `Apertar-D1` | (hardware: STL/print files) | reference only | `Apertar-Studio/Apertar-D1` |
| `apertar-kb` | `~/apertar-kb` | none (Mac remote `pi`, push allowed) | |
