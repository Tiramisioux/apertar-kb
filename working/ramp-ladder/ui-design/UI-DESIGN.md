# Mode Ladder UI design (approved by Patrik, 2026-10-28)

The look and behaviour Patrik approved for the Mode Ladder in the WebUI, the Camera settings card and the touch UI.
The mockup is the reference: `../mockup/Main.dc.html` (Settings > Record) and `../mockup/Quick.dc.html` (Camera settings),
live at https://claude.ai/artifact/YKbhhk8aMUS8sxEWa6UfRL (private to Patrik). Screenshots: `shots/mockup-*.png`.

`shots/reference-*.png` are screenshots of a cloud build of the same design on Core `3c4f07d` + T31-T34
(`../build/patches-on-3c4f07d/`). They show the real WebUI classes and states the mockup does not (recording, locked
controls, phone width). Two things in them are out of date: the switches (now **Off/On buttons**) and the sensor modes grid
(now **one column, collapsible groups**).

## Decisions (in the order Patrik made them)

| # | Decision |
| --- | --- |
| 1 | One colour for every resolution (badge and coverage bar `#4ade80`) |
| 2 | Compression per resolution, on the right of each row, with the file size per frame and per second |
| 3 | "Resolution 1, 2, 3", always numbered down the list; never "rung" in anything a user reads |
| 4 | No illegal values: the editor never sends what Core would refuse |
| 5 | "Activate ladder"; short texts that only explain the function |
| 6 | Speed Ramp is one setting, "Allow speed ramping" (FPS change during recording); no ramp targets or actions in the WebUI |
| 7 | Camera settings: the resolution under each FPS pill only while the ladder is on; the Resolution list stays last, labelled as in Apertar today; a "Resolution ladder on" pill |
| 8 | Crop graphics in Cinemate's style; "CROP IN" only for a real sensor crop-in (the window is narrower than the sensor); no aspect-ratio text in the graphic; a same-width mode is a shorter full-width window with no label |
| 9 | Running line: `Resolution 1 · 3840×2160 · ClearHDR16 · ≤25 · Uncompressed`; "ClearHDR" is the compact HDR tag (`ClearHDR16`, `SDR12`); names stay "4K Clear HDR 16-bit" |
| 10 | **Off/On buttons, not toggle switches** (Activate ladder, Allow speed ramping, and the touch UI's Mode Ladder row) |
| 11 | Activated sensor modes: the tiles, **in one column, in collapsible groups** (no dropdown) |
| 12 | **"Max" instead of "Up to"** for each resolution's highest FPS (`Max (fps)`, `Above 25, max 50 fps`, `max 50 fps`) |

## Settings > Record (WebUI), after the Recording format card

Screenshots: `shots/mockup-00-record-page.png` (whole page), `mockup-01-mode-ladder.png`, `mockup-02-speed-ramp.png`,
`mockup-03-activated-sensor-modes.png`, `mockup-03b-sensor-modes-crops-open.png`.

### 1. Mode Ladder card

- Head: title "Mode Ladder"; copy "Switches resolution automatically when you change FPS. Each resolution runs to its max FPS,
  then the next one takes over."; status pill `On` (green) / `Off`.
- **Activate ladder** row: title, one-line note (`On: changing FPS switches resolution.` / `Off: changing FPS never switches
  resolution.`), and two buttons **Off | On** (the page's pill buttons, the active one white). Takes effect at once
  (`set_mode_ladder enabled=true|false`). Disabled with a short note while recording or when no resolution is saved.
- **Running now** box: caps label, the running line in bold (ladder off: `3840×2160 · ClearHDR16 · Uncompressed (ladder off)`),
  note "Same line on the camera screen (FORMAT) and next to Frame rate in Camera settings.", the crop graphic (160×98) on the
  right, no caption.
- **During a take** note: "FPS stops at the running resolution's ceiling. Resolutions change between takes only, with a short
  preview blink. …" and "While the ladder is on, Resolution, Bit Depth and Clear HDR are greyed in Recording format: the FPS
  picks the mode."
- **Resolutions, first one first** (right: "Drag the handle, or use the arrows"). One row per resolution:
  - left: drag handle, number badge, crop graphic (78×48), name, meta (`3840×2160 · 16:9 · 16-bit · Clear HDR`), crop text
    (amber when it crops in), range (`Lowest FPS, max 25 fps` / `Above 25, max 50 fps`), a red problem line if any;
  - **Max (fps)**: number input, placeholder = the ceiling, min = the row's "from" + 1, max = the ceiling, empty = the ceiling;
    under it `Ceiling 25 (accepted maximum)` / `(build max)` / `(lossless cap)`;
  - **Compression**: select with Uncompressed, Lossless JPEG, Lossy 3:1, Lossy 5:1 (lossy disabled with "(not for Clear HDR)"
    on Clear HDR modes), a note (`Exact, largest files` / `Capped at 30 fps` / `Smaller files`), `≈ 12.4 MB per frame`,
    `≈ 622 MB/s at 50 fps` (amber with "above N MB/s" when over the card's measured write speed);
  - up, down, remove buttons (44 px).
  - Between rows: `↓ Above 25 fps: Clear HDR 16-bit → SDR 12-bit. Switches between takes only, with a short preview blink;
    in a take FPS stops at 25.`
- Draft line (`Saved on the camera.` / `Unsaved changes. Core checks the ladder again when you save.` / a red notice) with
  **Revert** and **Save ladder** (disabled while clean or while Core's dry run reports errors).
- **FPS coverage, 1 to 50**: one bar, a numbered segment per resolution, ticks at each top, caption
  `Build maximum 50 fps · apertar-hardware.conf, [camera] max_fps`; a gap line when the ladder does not reach the maximum.

Legal values (decision 4), as the mockup's `normalize`, `legal`, `spans`, `setThrAt`: a "Max" is clamped into
[from + 1, ceiling] with a notice (`Resolution 2: FPS must be between 26 and 50. Set to 50.`), equal to the ceiling = empty;
a move, add, remove or compression change that would leave a resolution unused is refused with a red notice
(`Resolution 3 (…) would never be used: the ones above already reach 50 fps.`); lossy on Clear HDR cannot be picked.

### 2. Speed Ramp card

Title "Speed Ramp", copy "Change the frame rate during recording. The clip keeps the rate it started at, so the faster parts
play back as slow motion.", label **Allow speed ramping** with **Off | On** buttons (`set_fps_ramp enabled=…`). Disabled with a
short note in H.264, ProRes and photo mode, and while recording.

### 3. Activated sensor modes card

- Copy: "From the sensor probe at start: 42 modes on this IMX585. Add the ones you want on the ladder. Ceilings are Core's,
  capped at the build maximum."
- Bit-depth pills: 12-bit, 10-bit, Any depth (Clear HDR modes always show).
- **Collapsible groups, one column**: Clear HDR, 4K SDR, 3840 wide crops, 2K binned. Each group header is a full-width button
  (chevron, name, `9 modes · 1 on the ladder`, `aria-expanded`). Clear HDR and 4K SDR start open, the crops and 2K start closed.
- Each tile, full width: crop graphic, name (`2.39:1, 12-bit`, `2K binned 12-bit`), meta
  (`3840×1608 · 2.39:1 · SDR · max 50 fps · 9.3 MB/frame`, `· crop in` when it crops in), and on the right **Add**, or
  `Resolution 2` when it is already on the ladder. Add is disabled, with the reason as its tooltip, when adding it would make
  the ladder illegal or the ladder has 8 resolutions.

### Crop graphic (all three places)

Cinemate's `cropDiagram`: frame border `1px solid #8a8a8a`, background `#131210`; window `2px solid #90ee90`, fill
`rgba(120, 220, 150, 0.13)` (`0.08` when it is the whole area); placed from the mode's sensor window (the probe's crop
rectangle) inside the full readout area; tag `CROP IN` in amber `#fbbf24` top left, only for a real crop-in. 2x2 binned modes
are drawn by their native window (1920x1080 binned = the whole 3840x2160 area). 16-bit Clear HDR reads 3840x2200 but is the
same 3840x2160 picture: it must not make the 4K modes look letterboxed.

## Camera settings card (WebUI main page)

Screenshot: `shots/mockup-04-camera-settings.png` (reference: `shots/reference-02-camera-settings-ladder-on.png`).

- Head: green pill **Resolution ladder on** while the ladder is active.
- Frame rate: right of the label the running line; while a `set_fps` that changes resolution is in flight
  `Switching to Resolution 2…` (amber).
- FPS pills: with the ladder on, a second line `Resolution 1` / `Resolution 2`; pills in another resolution than the running
  one get a dashed amber border. With the ladder off, no second line.
- Resolution (last, Apertar's own labels `4K Clear HDR`, `4K`, …): note `Resolution ladder on: set by the frame rate`; the
  pills are disabled, the running one stays white, the others dimmed. Crop mode the same.

## Locked while the ladder is on

Recording format card (Resolution, Crop, Bit Depth, Compression) and the Favorites Format card: disabled with one line
`Mode Ladder on: the FPS picks the resolution and compression.` (`shots/reference-03-*.png`, `reference-04-*.png`).

## Touch UI

- FORMAT row on the camera screen: the running line (from Core), wrapped inside its column, never over the preview. In the
  square layout the full line takes 4 lines: drop the size part there (`Resolution 1 · ClearHDR16 · ≤25 · Uncompressed`,
  2 lines). *Ask Patrik if he wants the size kept.*
- Settings page: a **Mode Ladder** row with **Off | On** buttons; disabled with "Set up the ladder in the WebUI (Settings >
  Record > Mode Ladder)." when no resolution is saved; Core's reason in red when it refuses.
- Resolution, crop, bit depth and Clear HDR controls disabled while the ladder is on, with the caption
  `Mode Ladder on: the FPS picks the resolution.`

## What Core must provide (names used by the cloud build; adapt if T33/T34 in VS Code chose others)

State: `fps_max`, `fps_take_max`, `ladder_enabled`, `ladder_active`, `ladder_rung` (1-based, 0 = off the ladder),
`ladder_count`, `ladder_text` (the running line), `ladder_tops` (each resolution's top FPS, for the pill labels).
Commands: `get_mode_ladder`, `set_mode_ladder` with `rungs` (`3840x2160:16:hdr:none:25,3840x2160:12:sdr:lossless_jpeg`),
`enabled`, `dry_run`. The `mode_ladder` reply carries each resolution's ceiling and crop and the sensor pool with ceilings per
compression: `../build/SPEC.md` sections 2.5-2.7, and `ModeLadder.hpp` (`toJson`) in the Core patch.
