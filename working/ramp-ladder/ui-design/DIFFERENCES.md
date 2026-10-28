# Mode Ladder UI: the approved design against the Pi tree (2026-10-28)

Pi tree: Core `ac48013`, UI `fb8ca36` (`cinemate-port`, local). Design: `UI-DESIGN.md` + the mockup. "Core" = something Core must
provide first. Items marked **ASK** conflict with an earlier decision or are open.

## Settings > Record (WebUI)

| Part | Design | Built | Change |
| --- | --- | --- | --- |
| Mode Ladder card head | title, one line of copy, status pill | title + pill ("On · Resolution 2") | add the copy |
| Activate ladder | titled row with a one-line note, Off/On pill buttons | bare Off/On pills | row + note (buttons already right: decision 10) |
| Running now | box: running line in bold, crop graphic 160×98 | none | new; **Core** `ladder_text` |
| During a take | two short notes | none | new (drop the "switch inside a take is not built" sentence) |
| Row | handle, number badge, crop graphic 78×48, name, meta, crop text, range, problem line | handle, "n. name", caption "Serves … up to …" | rebuild the row; **Core** crop rectangle per mode |
| "Max (fps)" | labelled input, placeholder = ceiling, min = from+1, max = ceiling; ceiling reason under it | unlabelled input, tooltip only | label "Max (fps)", clamp, reason; **Core** reason per ceiling |
| Compression | 4 choices (no "Default"), note, MB/frame, MB/s at max fps (amber above the card's write speed) | 5 choices incl. "Default (…)" | drop Default (always explicit); sizes from the mode |
| Between rows | "↓ Above 25 fps: Clear HDR 16-bit → SDR 12-bit …" | none | new |
| Legal values | editor clamps, refuses a move/add/remove that leaves a resolution unused, lossy on Clear HDR impossible | Core's dry run shows errors after the edit | client-side `normalize`/`legal` as in the mockup; keep Core as the judge |
| Draft line + buttons | "Saved on the camera." / "Unsaved changes…" / red; Revert, Save ladder (off while errors) | Save, Revert pills | draft line, rename, disable on errors |
| FPS coverage bar | numbered segments 1…max, ticks, gap line | none | new. **Not "build maximum 50 / max_fps"**: Patrik removed `[camera] max_fps`; the bar ends at `fps_max` |

## Speed Ramp

| Part | Design | Built | Change |
| --- | --- | --- | --- |
| Card | its own card, one setting "Allow speed ramping" Off/On, copy, disabled in H.264/ProRes/photo and while recording | a block inside Recording format: On/Off, Shutter Sync, Audio (experimental), Ramp to … over …, ×2, Back, Stop, Ramp-ready | own card; **remove** the ramp targets and actions (decision 6). **ASK** keep Shutter Sync and Audio rows? Ramp-ready is not in the design |
| Command | `set_fps_ramp` | `set_fps_speed_ramp` (renamed, Patrik) | keep ours |

## Activated sensor modes (new in the design)

Ours: one "Add" dropdown with the 40 probe modes. Design: a card with bit-depth pills (12-bit / 10-bit / Any depth), four
collapsible groups in one column (Clear HDR, 4K SDR, 3840 wide crops, 2K binned; the first two open), tiles with crop graphic,
name, meta (size · ratio · SDR/Clear HDR · max fps · MB/frame · crop in) and Add / "Resolution n"; Add disabled with a reason
when it would make the ladder illegal or at 8 resolutions. **Core**: the pool entries need the crop window, binning and a
ceiling per compression with its reason (today: `width height bits clear_hdr label class compression usable mode_ceiling`).

## Camera settings (WebUI main page)

| Part | Design | Built | Change |
| --- | --- | --- | --- |
| Head | green pill "Resolution ladder on" | none | new |
| Frame rate | running line to the right of the label; amber "Switching to Resolution 2…" | none | new; **Core** `ladder_text` |
| FPS pills | second line "Resolution n"; dashed amber border for a pill in another resolution | greyed above the ceiling | add line + border; **Core** `ladder_tops` |
| Resolution pills | last; note "Resolution ladder on: set by the frame rate"; disabled, running one white | list as before, not tied to the ladder | note + state. **ASK** Patrik: add separate "16-bit Clear HDR" / "12-bit Clear HDR" pills (where?) |

## Locks while the ladder is on

Design: Recording format (Resolution, Crop, Bit Depth, Compression) and the Favorites Format card are disabled with one line
"Mode Ladder on: the FPS picks the resolution and compression." Built: only Compression is locked (own note). **ASK**:
an earlier decision (Q2, Patrik) lets a manual resolution / bit depth / Clear HDR change switch the ladder off instead.

## Touch UI

| Part | Design | Built | Change |
| --- | --- | --- | --- |
| FORMAT row | the running line from Core, wrapped inside its column | the resolution line "3840x2160 · 16-bit · Clear HDR" | running line; **ASK** keep the size on the square layout? |
| Settings | "Mode Ladder" row with Off/On buttons; disabled "Set up the ladder in the WebUI…" when none; Core's reason in red | none | new |
| Mode controls | greyed with "Mode Ladder on: the FPS picks the resolution." | free (Q2) | see Locks |
| Compression | (greyed, by the lock) | greyed, labelled "set by Mode Ladder" | keep |

## Core: what the design needs that is not there

State: `ladder_enabled`, `ladder_count`, `ladder_text` (running line `Resolution 1 · 3840×2160 · ClearHDR16 · ≤25 · Uncompressed`),
`ladder_tops`. Present: `fps_max`, `fps_take_max`, `ladder_active`, `ladder_resolution`, `ladder_ramp_ready`.
`mode_ladder` reply: pool crop window + binning, ceiling per compression with reason. Commands present: `get_mode_ladder`,
`set_mode_ladder` (`resolutions`, `enabled`, `ramp_ready`, `dry_run`). The cloud's names differ (`rungs`, `ladder_rung`); ours are
Patrik's.
