# Long-take campaign: plan (2026-11-06, runner written, not yet run)

Request (User, 2026-11-06): unsupervised 30-minute takes with audio, to find out whether the storage tuning is optimal.
Status: runner written (`working/tools/longtakes.py`, runs on the Pi, copy in `~/longtakes/bin/`). **No real take has run.**
The smoke test was cut off twice by Pi resets (21:57 and ~22:00); the kernel logged `Voltage normalised` just before, and
EXT5V read 4.78 V at idle: power supply suspected (unconfirmed). The User is trying another supply.

## Decisions (User, 2026-11-06)

- Staged vs full grid: just run it, see how far it gets. Order: baseline first, then by number of factors changed.
- Drive: Kingston SKC3000S512G (477 GB), formatted by the User. NOT the Corsair of earlier campaigns.
- Target per take: 30 min **or as long as the drive allows** at those settings (about 25 min at the top fps). A take that
  fills the drive with no drop is a pass (`pass_drive_full`, minutes logged); every take that fills the drive is logged.
- Before each take all clip folders (`cDNG_*`) on the drive are removed. Nothing else is deleted.
- Lowest fps tried: **25**. Phase 2, after the 64 configs at 16-bit: the same 64 at **12-bit** 4K (Log configs will be
  skipped where Core reports Log unavailable at 12-bit).
- Audio: the configured USB PnP Sound Device (`hw:2,0`), unchanged.

## Rules from the request

- Start in 4K Clear HDR 16-bit at the sensor's maximum fps and step **down one fps at a time**.
- A take stops at the **first dropped frame** (then the next config starts) or at **30 minutes** (a pass).
- Audio is recorded in every take.
- Drive: the NVMe for now (assumed: Corsair MP600 Mini, exFAT, `/media/RAW`); an SSD later.
- Factors: WebUI open on a client (on/off), preview temporal denoise (on/off), trim (on/off), frame-rate phase lock
  (on/off), compression (uncompressed / lossless), Log (on/off). All combinations: **64 configs per fps step**.
- **Do not wait for the NVMe to cool down** between takes. The temperature at the start of each take is logged instead,
  so a hot start shows up in the table.
- Delete all recordings when the drive gets full (and after each take, so a take never starts on a full drive).
- Log every take; keep the logs for review.

## What is logged

- Once per session: Pi model (`/proc/device-tree/model`), Core commit, tuning file, kernel.
- Once per second per take: Pi temperature, NVMe temperature (if readable without sudo), CPU load, RAM, drive fill,
  Core drop counters (write queue full, copy slot busy, capture gap, re-queue failure).
- Per take: config, fps, seconds recorded, result (pass or first drop), which counter moved, and the state of the above at
  the moment of the drop.

Results table: one row per take with an **estimated cause** (labelled confirmed / probable / unconfirmed), under
`tests-2026-11/` as `longtakes-<date>.csv` plus a findings page.

## Size and the proposal

64 configs x up to 30 min is up to ~32 h per fps step. Proposal (needs the User's decision): a **staged** run. Baseline
first (uncompressed, TDN off, trim on, phase lock off, no WebUI, no Log), stepping fps down until a take reaches 30
min; then one factor at a time at that fps; the full 64-config grid only at one or two fps values.

## Expectations from earlier findings (`recipe.md`)

- Lossless at Clear HDR 16-bit encodes at ~17.5 fps: lossless takes should fail almost at once above that.
- Log (16-bit stored as 12) is ~25 % fewer bytes and is an untried lever for 30 fps.
- Trim off: stalls expected after ~0.9 TB written. A 30-minute take at 510 MB/s is ~900 GB, so trim-off takes will
  reach that range.
- Last clean: 25 fps (10 min) and 28 fps (3 min, FE config queue depth 4). 30 fps lost ~3 frames in 2 min.

## Open before the first take

1. Pi reachable. 2. Time budget: staged or full grid. 3. Audio input device (default: Core's current setting).
4. The running Core is still the `9b5ea14` binary; the `cinemate-port` build (trim and TDN switches) needs
`sudo systemctl restart apertar-core`, which the User runs.
