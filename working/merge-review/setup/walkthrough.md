# What cinemate-port adds: a walkthrough

A short tour for the Apertar developer. Branch `cinemate-port`, with the clip folder split, plus the review fixes.

Rule of the review: a stock camera behaves as Apertar 1.6.0. Most additions are off until the operator turns them on. "Off" and "on" below are the defaults.

Full detail per feature: `developer-handoff.md` in the KB.

## 1. Camera and modes

- **IMX585 modes.** Many more sizes, crops and bit depths, from a table in Core (`Imx585Modes.hpp`). Works with the original driver too.
- **IMX283.** A new sensor family, with 57 modes. Inert without the sensor.
- **fps ceiling from the sensor probe.** Core asks the sensor what it can do at start. `fps_max` is in the state.
- **Values the camera decides.** In Clear HDR the camera holds ISO and white balance. The screens show those values in italics.
- **Preview temporal denoise switch.** Off makes the 4K Clear HDR preview much lighter. The DNGs do not change. On by default, as 1.6.0.
- **Frame-rate phase lock.** Holds the sensor rate against the audio clock on long takes. Off.
- **Dynamic resolution** (being built now). It replaces the port's Mode Ladder. You set the fps; the camera picks the best enabled mode that holds a 30-minute take on this drive and board, and says why.

## 2. Recording and media

- **A pulled drive ends the take cleanly.** The take keeps about its last second. Record is refused without media or under 1 GiB free.
- **Faster DNG writing.** One write per frame, a sync each second, writer counts per drive type.
- **Log for cDNG.** 16 bit stored as 12 bit with a log curve. Off.
- **Speed ramp.** The fps can change inside a cDNG or MLV take. WAV and timecode stay right. Off.
- **Clip name templates.** Names built from tokens. The default name is unchanged.
- **RAM write buffer.** A large queue sized from free RAM, with a safety stop. Off.
- **Storage pre-roll.** A 2-second test take that warms the drive, then is deleted. Off.
- **Clip folder split.** A long take is written in `part_NNN` folders, because exFAT slows down in full folders. Core merges the parts back while the camera is idle, so Resolve sees one clip. Split off today, merge on.
- **Drive trim.** Core trims the NVMe after large deletes, so it does not stall. On; needs the root helper.
- **Stop on Dropped Frame.** Ends the take at its first dropped frame. Off.

## 3. Controls and hardware

- **One writer for the hardware file.** Every save is checked, versioned (20 versions, Undo) and applied without a restart.
- **Controls page** (WebUI, Config > Hardware). One row per input, its actions, free pins, live state.
- **Listen, I2C scan, output test.** Shows the last control that fired; scans the bus; blinks the tally once.
- **More inputs.** GPIO buttons, encoders, 2- and 3-way switches, Grove knobs, NeoRotary 4, four IMU chips. All off until configured.
- **Gestures.** Single, double, triple click and hold per button. Off until mapped.
- **Normally closed buttons.** `invert_on_start=true`. Off.
- **One action vocabulary.** The same action names on every input.

## 4. Second sensor

- **Dual sensor.** A second Core runs for cam1. It starts by itself only when two sensors are found. One sensor: it stays off. See `services.md`.

## 5. WebUI

- **Clip Browser.** Card grid with thumbnails, filter, sort, download and delete.
- **Clip Viewer.** Plays a clip in the browser: scrub, frame step, histogram, sound.
- **Settings search.**
- **Performance card.** The write-path switches in one place, each with a line on what it costs.
- **Boot Config card.** Edits `config.txt`: sensors, link frequency, buses, display. Shows the change, keeps a backup. Text editing off.

## 6. Touch UI

- **Value lists and capped pickers.** Values above `iso_max` or `fps_max` are greyed.
- **Recording indicators.** Red frame, red timecode, buffer bar.
- **Raw readout.** Bit depth, Clear HDR and Log on the resolution line; time left from real file sizes.
- **Split clips.** The touch UI lists and plays split clips.

## 7. System and build

- **Fan mode** goes through Core, so it cannot clash with a Boot Config save.
- **Builds without libcamera**, and runs with `--simulate`. Every review commit was built both ways.
- **Host tests** in `tools/` (21 today).
