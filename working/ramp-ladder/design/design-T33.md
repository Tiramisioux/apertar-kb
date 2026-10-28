# T33 design: value lists, free stepping, flicker-free shutter angles (2026-10-28, approved by Patrik)

Built by Claude on the Pi's `cinemate-port`, step by step (Patrik's choices). Requests 7, 13, 23 and 24 in `../README.md`.

## Storage

`~/.config/CinePi/UI.conf` `[General]`, the file Core and the touch UI already share (`sharedUiSettingsPath()`):

| Key | Meaning | Default |
| --- | --- | --- |
| `isoSteps`, `shutterAngleSteps`, `fpsSteps`, `wbSteps` | the operator's lists, comma-separated numbers | missing = today's built-in lists |
| `isoFree`, `shutterAngleFree`, `fpsFree`, `wbFree` | free stepping on the hardware controls | false |
| `isoFreeIncrement`, `shutterAngleFreeIncrement`, `fpsFreeIncrement`, `wbFreeIncrement` | step size in free mode | 100, 1, 1, 100 |
| `flickerFreeShutterAngles` | add flicker-free angles for the current FPS | false |
| `mainsHz` | the local mains frequency, 50 or 60 | 50 |

## API (least change)

- One command: `set_value_steps name=iso|shutter_angle|fps|wb [values=v1,v2,…] [free=true|false] [increment=N]`;
  for `shutter_angle` also `[flicker_free=true|false] [mains_hz=50|60]`. `values=` empty → back to the built-in list.
- State: the lists and settings in the existing `ui` object (the operator's list or the built-in one). **Built without** a
  `flicker_free_angles` field: the formula is three lines, so Core, the WebUI and the touch UI each compute it from
  `flicker_free_shutter_angles`, `mains_hz` and the current FPS (a duplicated truth, listed in `llm/core-map.md` §4).

## Flicker-free angles

Lamps on AC flicker at twice the mains frequency, so a flicker-free exposure is k / (2 × mains):
angle = 360 × fps × k / (2 × mains), k = 1, 2, … while ≤ 360°. 25 fps / 50 Hz: 90, 180, 270, 360°; 24 / 50: 86.4, 172.8,
259.2, 345.6°; 25 / 60: 75, 150, 225, 300°. Cinemate's two formulas (`cinepi_controller.py:1450-1459`, `:3286-3299`) are both
off (see README request 23).

## On screen (WebUI and touch UI)

- The operator's values; values above `iso_max` / `fps_max` greyed out; the cap added as the top selectable entry, green.
- Flicker-free angles merged into the shutter list, green when not in the operator's list.
- Auto at the top where the mode allows it; Lock while auto ISO runs (`fafc477`).

## Hardware (encoder, pots, `*_up`/`*_down`)

Step through the same selectable list. In free mode step by the increment between the list's lowest and highest value
(Cinemate's `steps_bounds`), capped by the mode.

## Steps

1. Core: keys, command, state, hardware stepping, flicker-free. 2. WebUI: editor card + lists. 3. Touch UI: lists with greyed
and green entries. 4. Test.
