# Cloud session state (2026-10-28): T33 + T34 build, controls and playback projects

Saved as work in progress. Nothing here is on Apertar-Core or Apertar-UI GitHub.

## T33 (build maximum) and T34 (Mode Ladder)

| What | State |
| --- | --- |
| Base | Core `6ae70b5` + T31 + T32 patches (`be6775d`); UI `dc471c1` + two T32 UI patches (`9a6fc7d`) |
| Contract | `SPEC.md` (Patrik's mockup decisions: compression per resolution, no Ramp-ready, "Resolution N", ClearHDR16 tag, crop diagrams from the probe, one Speed Ramp switch) |
| T33 | committed in the scratch trees: Core `d4ed6de`, UI `e3a1a04` (`patches/core`, `patches/ui`) |
| T34 | coded in Core, WebUI and touch UI (`patches/wip-core.diff`, `patches/wip-ui.diff`, not committed). `ModeLadder.hpp` + `mode_ladder_test.cpp` (52 checks) + `core_ladder_probe_test.cpp` |
| Checks | g++ -fsyntax-only of CameraController.cpp, ApertarCoreApp.cpp, WebControlPage.cpp with libcamera-apertar headers (`hostcheck-core.sh`): 0 errors, 0 warnings; node --check; Playwright drive of the WebUI against a mock (`webtest/`, screenshots); the touch UI builds with Qt 6.4.2 |
| Critique | 23 findings, 19 confirmed (`critique-confirmed.json`), 13 distinct defects |
| Fixes | all 13 distinct defects fixed and re-checked; T34 committed in the scratch trees (Core `1164414` camera, `1ab0e37` web; UI `d5ebde4`) |
| Patches | `patches-on-6ae70b5/` (the full reviewed series: Core T31, T32 x2, T33, T34 x2; UI T32 x2, T33, T34) |
| Stopped | the rebase onto Patrik's tips (partial: `patches-tip/`) and the T33/T34 tutorials and zip: Patrik builds T33 and T34 with Claude in VS Code (2026-10-28). This folder is reference for that work |

## Controls project (Cinemate GPIO dropdown and method assignment, I2C devices, the NeoRotary 4 fix)

`working/controls/`: reader reports, then design, critiques and v2. Tutorials start at T36.

## Playback project (WebUI playback like the touch UI's clip browser and player)

`working/playback/`: reader reports, then design, critiques and v2. Tutorials T46-T54; T47-T51 are built (`working/playback/HANDOFF-next.md`).
Patrik's decision: the WebUI playback mirrors the touch UI's clip browser and player; Cinemate gives the browser mechanics.
