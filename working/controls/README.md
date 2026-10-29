# Controls project: Cinemate's GPIO dropdown and method assigning, Apertar style (design v2, 2026-10-28)

Patrik's brief: port Cinemate's GPIO dropdown and method assigning in the most Apertar-like style, through Apertar's API, with
a system-controlled config file; cover the hardware Apertar uses today (I2C expanders, the NeoRotary 4, the CFE hat, …) and
the I2C bus settings that make his NeoRotary-on-the-CFE-hat fix work; offer both Cinemate's easy dropdowns/drag and drop and
manual editing for advanced users.

Status: designed, critiqued and revised in a cloud session. **Nothing is built.** Trees read: Core `eb9cc39`, Apertar-UI
`d8098d0`, Cinemate `d6cc93e`, the KB. Hand-over to Claude in VS Code: `HANDOFF-PROMPT.md`; for Sonnet, `HANDOFF-PROMPT-SONNET.md` (Claude writes the code on a `controls` branch; Patrik
tests, confirms and gives feedback at a check-in after every step).

| File | What |
| --- | --- |
| `plan-summary.md` | one page: the recommendation, the tutorials T36-T45, the questions |
| `design-controls.md` | the design (v2): how it works today, the decision, file/schema/commands/state, live apply, WebUI and touch UI, the hardware catalog with Patrik's rig, the plan file by file, tutorial outlines with tutor blocks, measurements M1-M8, risks, questions Q1-Q23 |
| `changes-from-critique.md` | each of the 120 critic points: accepted (108), changed (11), rejected (1), with evidence |
| `critique-code.md`, `critique-operator.md` | the two critiques of v1 |
| `r1-cinemate-gpio.md` … `r4-kb-hardware.md` | the reader reports: Cinemate's editor, Apertar Core's hardware layer, every other reader of the file and the touch UI, the KB's hardware facts and the I2C fix |
| `design-controls-v1.md`, `plan-summary-v1.md` | v1, kept for reference |
| `sketch/` | host-tested sketch: `hardware/ActionCatalog.hpp` (one action vocabulary), `hardware/HardwareConfigText.hpp` (parse, validate, edit the file), `controls_test.cpp` (78 checks; identical to Core's three normalizers on 355 + 44 + 51 tokens). Build from this folder: `g++ -std=c++20 -Wall -Wextra -Werror -I. -I<apertar-core>/src controls_test.cpp -o controls_test && ./controls_test <core-tree>` (the tree path is needed: the dispatcher check reads its `ApertarCoreApp.cpp`; the `D5` check needs GNU sed, so on a Mac it fails: run it on the Pi) (`make_old2.sh` regenerates the copies of today's normalizers from a Core tree) |
| `anchors.txt`, `search.txt` | the search strings the plan uses, checked on `eb9cc39` |
