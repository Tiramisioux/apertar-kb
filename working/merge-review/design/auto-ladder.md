# Dynamic resolution (the automatic ladder): design

Written 2026-11-21 for the merge review of the cinemate port. Read-only design: no code changed, nothing committed.
Source of the request: the owner's messages of 2026-11-21, collected in `dynamic-resolution-requirements.md` (it wins
over every earlier line; the numbers below carry its point numbers as R1..R12). Code read at `core-work`
`9af4a3e` (branch `work/improve`) and `ui-work` `98937b8`; `core-upstream` / `core-main` have no ladder at all
(`grep -rli ladder src` finds only `ProresEncoder`). Numbers come from
`working/drop-frames/estimator-campaign/pre-analysis.md` (the owner's note, "PA" below),
`estimator-campaign/findings.md` (set EST-05fb8f1-a and the P6 warm takes of 2026-11-21), `nvme-campaign/findings.md`
and `tests-2026-11/findings-longtakes-ssd-2026-11-07.md`. Labels as in the KB: **measured**, **derived**,
**probable**, **unconfirmed**; code claims are **confirmed** when read.

## In short

1. The user-defined Mode Ladder (ordered rungs, thresholds, compression and Log per rung) goes. Dynamic resolution
   replaces it: one switch, **on by default** (R1); the pane stays, active while on, greyed while off.
2. Core holds one table of known limits: the fps a mode holds for a **30-minute take on a hot drive**, per storage
   type, Pi board, resolution, bit depth and HDR/SDR (R5, R6). Every cell carries its label and its source.
3. Steps are 25, 30, 33, 50, 60, 70, 80 ... (+10 above 60). A mode serves a requested fps F when F is at most its cap,
   the cap being its 30-minute number rounded **down** to a step (R4).
4. Order of giving up, when F is above a cap: resolution first, then bit depth, then Clear HDR to SDR (R3). In code: sort
   the enabled modes by (HDR, bit depth, pixels), best first; take the first that holds F.
5. Only enabled modes count (R7). The list lives in one key; an edit rebuilds the steps, the pane and the running mode
   at once, between takes.
6. Levers shift the numbers before rounding (TDN, phase lock, Log, aids) or only pick the row (split, audio, WebUI);
   the pane names the lever in its "why" text (R8). Optional: Dynamic resolution switches TDN off in 4K (R9).
7. Information and behaviour are separate: the limit lines and the lever info lines show on every camera; the mode
   choice, fps clamp and compression choice happen only with the switch on (see "Information and behaviour").
8. Split becomes off / on / automatic, default on; automatic turns it on above 32 fps for per-frame formats (R11).
9. Never changes during a take. A change of storage, a lever or the enabled list applies at the next idle moment.
10. Consequence the owner must see first: with 30-minute caps, **4K Clear HDR 16-bit holds no 25 fps on this NVMe**
    (25, 26, 27 all failed a 15-minute take), so at 24 or 25 fps the camera records 2K Clear HDR 16-bit. See "For the owner" 1 and 2.

## What exists

### The user ladder end to end (confirmed, `core-work` `9af4a3e`)

| Part | Where | What it does |
| --- | --- | --- |
| Rung and ladder types | `src/camera/ModeLadder.hpp:17-53` | a rung = size, bits, Clear HDR, `threshold` (highest fps it serves), `compression`, `cdngLog`; ladder = `enabled`, `rampReady`, rungs, `aspects` (display filter) |
| Chooser | `ModeLadder.hpp:89-122` | `rungCeiling` = min(threshold, sanitiser ceiling); `chooseRung` = first usable rung whose ceiling reaches F, else the highest ceiling |
| Text and file | `ModeLadder.hpp:124-206`, `361-408` | `WIDTHxHEIGHT:BITS:hdr\|sdr[:FPS[:COMP[:log]]]`; `mode_ladder.conf` keys `enabled`, `ramp_ready`, `resolutions`, `aspects` |
| Validator | `ModeLadder.hpp:250-300` | repeats, thresholds must rise, lossy cannot be Clear HDR, "never used", look changes |
| Rung state from the sanitiser | `CameraController.cpp:11748-11775` (`ladderStatesLocked`) | asks `sanitizeSettingsForSensor` at 280 fps: valid, usable, ceiling (sensor probe or table, lossless cap) |
| Active | `CC:11777-11781` | enabled, not overridden, not photo, not ProRes/H.264, one rung usable |
| Apply | `CC:11785-11804` (`ladderRewriteLocked`) | never in a take; writes size, bits, Clear HDR, compression and the clamped fps into `next`; callers at `CC:11631`, `11715`, `12244`, `12370`, `12972` |
| State | `CC:11810-11856`, `CC:182-189`, `App:336-343`, `10193-10200` | `ladder_active`, `ladder_resolution`, `ladder_tops`, `ladder_text`, `fps_max`, `fps_take_max` |
| Take cap | `CC:11634-11640` | in a take, fps is clamped to the running rung's ceiling |
| Blocks | `CC:11563-11564`, `12563-12564`, `kLadderOwnsMode` `CC:3176` | active ladder refuses `set_resolution` / `set_raw_bit_depth` (DB-45, DB-53); `set_clear_hdr` instead sets `ladderOverride_` (`CC:12608-12649`); compression refused (`CC:12311`, `12387`, `12435`, DB-46) |
| Commands | `App:15482-15500` (`get_mode_ladder`, `set_mode_ladder`), `App:13497-13540` (cam1 relay) | `set_mode_ladder` refused in a take except the aspect filter (`CC:12026`) |
| Store | `CC:408-430`, `11421-11424`, `11858-11892` | `mode_ladder.conf` beside `camera_settings.conf`; the merge plan moves it into `camera_settings.conf` (`camera-modes.md`, commit 10) |
| WebUI | `WCP:6009-6050` (cards), `8615-9728` (editor JS, about 1,100 lines), `1629-2137` (CSS, about 500 lines), `10184-10190` (`imx585LadderGroups`) | card "Activated sensor modes" (probe pool, Add puts a mode on the ladder), card "Mode Ladder" (Activate, Running now, rows with Max / compression) |
| Touch UI | `ui-work src/ApertarControlBridge.cpp:1770-1772`, `qml/SettingsPage.qml:3428`, `3439` | reads `ladder_active` only: greys Compression with "(set by Mode Ladder)". No ladder editor (DB-53) |

Findings while reading: `ramp_ready` is still in the file, the chooser and `fillLadderFieldsLocked` (`ModeLadder.hpp:48`,
`CC:11790`, `11847`) although DB-46 dropped Ramp-ready. `ladder_text` is rendered only by the WebUI (`WCP:9595`, `17883`).

### What "activated modes" are today (confirmed)

The WebUI card **"Activated sensor modes"** (`WCP:6009`, text at `WCP:9411-9425`: "Activate the ones you want on the
ladder"). It lists the sensor probe's pool; pressing a mode's button puts it into `modeLadder_.rungs`. So **an
activated mode is a rung**; the saved list is `resolutions=` in `mode_ladder.conf`. Favourites (`Quick Access`,
`WCP:6055`) and presets are different things and not involved. The pool is built from `sensorModes()` and the family
tables (`CC:11955-11985`, `Imx585Modes.hpp`). Nothing marks a mode as allowed other than this list, so the smallest
Apertar-shaped design is to keep it: the list stays, loses everything but "which modes" (see "Enabled resolutions").

### The rate evidence (all IMX585 on a CM5 Lite, Core clip-split, exFAT, split 5000 unless said)

Storage types in Core: `MediaClass` {pi-nvme, usb-uas, usb-storage, sd-card, other, unknown} and `MediaFilesystem`
(`src/util/MediaProfile.hpp:26-27`); published as `media_class`, `media_fstype` (`App:10263-10264`). The CFexpress
hat is an I2C card detector, the card behind it is NVMe, so it classifies as `pi-nvme`. Board: `/proc/device-tree/model`
is read (`App:6185-6221`, `pi_model` in the state `App:10419`).

| Storage | Drive measured | Facts | Source and date |
| --- | --- | --- | --- |
| pi-nvme | Corsair MP600 Mini 1 TB on the CFE hat | 60 GB direct write 780 MB/s, slowest 10 s 596-627 MB/s (**measured**); in takes ~560 MB/s cold, ~465 warm; pauses of ~2 s once warm (**measured**) | `nvme-campaign/findings.md` S1, 2c-0; PA 2c-1, 2026-11-10/11 |
| pi-nvme, long takes | same | 15-min 4K takes: HDR16 unc 27 failed at 708 s (316 GB), 26 at 621 s (265 GB), 25 buffer full at 758 s, **P6 (warm start, 2026-11-21): 27 failed at 426 s after 190 GB, 38 SDR12 buffer full at 269 s after 108 GB**; 4K SDR12 unc 37 passed 15 min (S4); no 4K take has run 30 min (**measured**) | `estimator-campaign/findings.md` P6; `nvme-campaign/findings.md` S4 |
| pi-nvme, 60-s capacity | same | 4K SDR12 lossless 40, SDR10 lossless 45, HDR16 unc 27, HDR12 unc 25, 2880x2160 crop lossless 56, every 2K mode 57-60 (HDR 29-30) (**measured**, cold) | `estimator-campaign/findings.md` capacity table |
| usb-uas | Samsung T7 over USB | ~100-105 MB/s in takes (**measured**); 2K only: SDR12 lossless 48 passed 30 min, SDR12 unc 32 with split passed 30 min 4 of 4, HDR16 lossless 27 passed, HDR16 unc 18 (meter); 4K never run, derived 6-20 | `tests-2026-11/findings-longtakes-ssd-2026-11-07.md`; PA section 1 |
| usb-storage, sd-card, other | none | no number in the KB (`grep -i "sd card\|sd-card"` in the hardware log finds no sustained figure) | **unconfirmed** |
| other boards | Pi 4, CM4, Zero, Pi 3 | no take; estimator plan excludes them (`estimator-campaign/plan.md:26`) | **unconfirmed** |

Levers (PA 2, 2a, 2b, 2c-1; all NVMe, **measured**, small n): TDN on lost frames in every 4K take (0 of 24 clean against
16 of 24 off; +288 gaps/min on the back-end anchor; 2K clean 5 of 5). Phase lock costs ~0.5 fps, WebUI client 0.4-0.6,
audio 0.2-1.2, all only within ~1 fps of a back-end edge (4K HDR16, HDR12, Log). Aids on gave fewer gaps (sign
**unconfirmed**). Log costs 2-3 fps at 4K HDR16 and is not applied in SDR. Split: a flat exFAT folder slows file
creation as `0.32 us x files`, so a flat take holds while `t < 1.9e6 / fps^2` seconds (**derived**, measured on T7 and an
NVMe probe): 50 min at 25 fps, 35 at 30, 31 at 32, 14 at 48.

Not in Core today: no table of sustained limits (`grep -rli sustained src` finds nothing); the ceilings in Core are the
sensor's (probe, table, `FpsCeiling.hpp`) and two back-end caps. Core cannot see connected WebUI clients (no counter
found in `ApertarCoreApp.cpp` or `web/`; **probable**, grep only).

## Dynamic resolution

### The rule

Inputs: requested fps F; storage kind S (from `media_class`, `media_fstype`); board B; the enabled-modes list A; the
recording format; the levers L (below). Everything else is the sanitiser's.

1. **Candidates**: modes in A that the sanitiser keeps in the current format (`ladderStatesLocked` `valid`/`usable`
   stays), same aspect ratio as the running mode (a ladder step never changes the frame shape; owner question 5).
2. **Order** (best first), a lexicographic key: Clear HDR before SDR, then deeper bit depth, then more pixels, with the
   crop-in modes of a class after its non-crop modes. This is "keep HDR longest, bit depth next, resolution goes
   first" (R3). On the IMX585 the default list gives: 4K HDR16, 2K HDR16, 4K HDR12, 4K SDR12, 2K SDR12, 4K SDR10, 2K SDR10.
3. **Cap** of a mode = `step_down(min(sensor ceiling, limit(S, B, mode, L)))` where `limit` is the table's 30-minute
   number after the lever shifts, and `step_down` rounds to the largest step <= the number (below 25 the number itself,
   floored; 24 is a cinema rate and must stay usable).
4. **Choice**: the first mode in the order whose cap >= F (with 0.0005 slack, as `chooseRung` `ModeLadder.hpp:114`).
   If none: the mode with the highest cap, and fps is clamped to that cap (the message says so), as `chooseRung` and
   `CC:11802` do today.
5. **Compression** (cDNG only) comes from the table cell: Clear HDR uncompressed, SDR lossless JPEG on NVMe (the DB-46
   defaults, and what the numbers were measured with); the T7 column lists HDR lossless where it holds more
   (owner question 6). Lossy DNG and MLV keep the operator's setting; ProRes and H.264 are not covered (as today,
   `CC:11779`).
6. `fps_max` = the highest cap among candidates; `fps_take_max` = the running mode's cap (unchanged meaning, so the
   UIs cut their fps lists where they do now).

Because the order is lexicographic, the choice is not monotonic in resolution: giving up HDR can bring 4K back (4K SDR12 at 33 after 2K HDR16 at 30). That is the literal reading of R3
("HDR/SDR kept as long as possible"); the monotonic alternative is owner question 3.

### The known-limits table (the single place)

One header, `src/camera/SustainedFps.hpp`, pure (std only, no libcamera, no MediaProfile include), host-tested like
`FpsCeiling.hpp` (`tools/fps_ceiling_test.cpp`). One row per cell; to update the analysis, edit rows and nothing else.

```
struct Cell {
    Kind storage;           // Nvme, UsbSsd   (mapped from MediaClass in CameraController)
    Board board;            // Pi5 (CM5 and Pi 5; only the CM5 Lite is measured)
    unsigned width;         // resolution class: the picture's long side as the pool names it (3840, 1920, ...)
    bool hdr; unsigned bits;
    const char *compression;       // "none" or "lossless_jpeg"
    double fps30;           // sustained for a 30-minute take on a hot drive, split on, reference levers
    double fpsShort;        // takes up to ~8 min, information only (0 = none known)
    Label label;            // Measured, Derived, Probable, Unconfirmed
    Group group;            // BackEnd, Encoder, Drive, Sensor: which wall limits it, picks the lever rules
    const char *source;     // "EST-05fb8f1-a 2026-11-21"
};
```

Reference levers of every cell (PA section 1): TDN off, phase lock off, audio on, WebUI client connected, aids on, split
on, exFAT, drive hot. A mode with no cell takes the cell of the **nearest larger** mode of the same (HDR, bits) class
(safe: fewer pixels never hold fewer fps; label "derived from <cell>"); SDR 12-bit lossless also has a pixel-rate row
(`330 Mpx/s` on NVMe, derived from 4K 40-42 fps and 2880x2160 56 fps, PA 2c-1) so crops get a number. No row at all for
the class: the sensor ceiling only, label "no measurement". Resolution class means the pool's picture size, never the
sensor name (R5).

#### Table A: the cells (IMX585, 16:9, cDNG). `fps30` is the number, "cap" the step it rounds to

| Mode | NVMe (MP600 Mini, Pi 5 / CM5) | USB SSD (T7) | Wall | Source and reasoning |
| --- | --- | --- | --- | --- |
| 4K HDR16, unc (NVMe) / lossless (T7) | **20** (cap 20) **unconfirmed** | **9** (cap 9) derived | back end, then warm drive | NVMe: 25, 26, 27 failed 15-min takes at 12.6, 10.3, 7.1 min (190-316 GB), nothing below 25 was run; 20 is a placeholder under the evidence, replace after the first 30-min hot take at 24, 22, 20 (PA 2c-2: "nothing in 4K has run 30 min"). T7: ~10 MB/frame, 105 MB/s |
| 2K HDR16, unc (NVMe) / lossless (T7) | **30** (cap 30) probable | **27** (cap 25) measured | sensor (30) | NVMe: 60-s clean at 30, flow 125 MB/s, drive stays <= 64 C; 30 min not run. T7: lossless 27 passed 30 min (older build) |
| 4K HDR12, unc | **20** (cap 20) unconfirmed | **12** (cap 12) derived (lossless) | back end | gaps at every fps 25-30 (S2); 22-23 never run |
| 4K SDR12, lossless | **40** (cap 33) derived | **18** (cap 18) derived | encoder, ~200 % CPU | 40-42 at 60 s; 43 held 5 min on an older build; P6 lossless takes not run yet; unc 37 held 15 min, 38 failed at 4.5 min warm |
| 2K SDR12, lossless | **60** (cap 60) probable | **48** (cap 33) measured | sensor (60) / drive on T7 | 60-s and 5-min clean; T7 passed 30 min at 48 |
| 4K SDR10, lossless | **45** (cap 33) derived | **20** (cap 20) derived | encoder | 45-47 at 60 s; same cap as SDR12 4K after rounding |
| 2K SDR10, lossless | **60** (cap 60) probable | **48** (cap 33) probable | sensor | follows 2K SDR12 |
| 4K HDR16 + Log (a lever, replaces the HDR16 row) | **24** (cap 24) derived | **8** derived | back end | 25 held 3 and 5 min, 307 MB/s, drive <= 66 C, never paused; Log costs the back end 2-3 fps; 28 and 30 dropped |
| 2880x2160 crop SDR12, lossless | **56** (cap 50) derived | **24** (cap 24) derived | encoder | 59 at 60 s |

`fpsShort` (information line only, **measured** unless noted): NVMe 4K HDR16 unc 27 (3 and 5 min clean, 11 of 12),
4K SDR12 unc 38 (3 and 5 min), 4K SDR12 unc 37 for 15 min; others 0.

Tables B (levers) and C (outcome) follow; ProRes, H.264, MLV and lossy rows of PA section 1 go into the same struct
when those formats get covered (not v1).

#### Table B: lever effects, applied to `fps30` before rounding (same header, one row per lever)

| Lever | Read from | Applies to (group) | Effect | Label |
| --- | --- | --- | --- | --- |
| TDN on (`preview_tdn`) | `CaptureSettings.previewTdn` (`CC:233`) | every unbinned mode (4K, crops); binned 2K unaffected | cap 0: the mode is not used (0 of 24 4K takes clean, lowest fps tried 23); with the TDN switch of Dynamic resolution on, Core turns TDN off instead | measured |
| Phase lock on | `fpsPhaseLock` (`App:376`) | BackEnd cells | -1 fps (measured -0.5, 2 SE) | measured, small n |
| Aids off (peaking and zebra both off) | UI snapshot `zebraEnabled`, peaking (`App:1882`) | BackEnd cells | -1 fps (aids on lost fewer frames) | unconfirmed sign; remove if P5 contradicts |
| Log on | `cdngLog`, `cdngLogApplied` (`CC:210`) | 4K HDR16 only: row swaps to the "+ Log" row; no effect in SDR or at 2K | see table A | measured |
| Split off | `framesPerFolder` / the new split setting | per-frame formats on exFAT/FAT: `fps30 <= sqrt(1.9e6 / 1800) = 32` | derived |
| Audio on/off | `recordAudioEnabled` (`App:1930`) | none: the table is for audio on | gain of 0.2-1.2 fps when off is not used | measured |
| WebUI client | not readable in Core | none: the table is for a connected client | the info line says "close it at the limit" | measured |
| Card fill > 94 % (NVMe) | `media_free_bytes` (`App:10296`) | warning only | the card stalled at 96-97 % in 4K HDR16 | measured |

#### Table C: what the default list does (steps 25, 30, 33, 50, 60), no crops, TDN off, Log off

| Requested fps | NVMe | USB SSD |
| --- | --- | --- |
| up to 20 | 4K HDR16 unc (up to 20) | 4K HDR16 lossless up to 9; then 2K HDR16 up to 25 |
| 21-25 | 2K HDR16 unc | 2K HDR16 lossless |
| 26-30 | 2K HDR16 unc (30) | 2K SDR12 lossless (cap 33) |
| 31-33 | 4K SDR12 lossless (cap 33) | 2K SDR12 lossless |
| 34-60 | 2K SDR12 lossless (cap 60) | none: fps clamped to 33 |
| above 60 | none unless a crop is enabled (`fps_max` 60) | none |

With the table's `fpsShort` numbers the pane says, for a 25 fps request on NVMe: "2K Clear HDR 16-bit. 4K Clear HDR
16-bit holds 27 fps for takes up to 8 minutes (measured) but only 20 for 30 minutes (unconfirmed)."

### Storage, board, take length

- **Storage** comes from the media profile Core already keeps (`ApertarCoreApp::mediaProfile()`, `App:12176`; the change
  hook is at `App:11700-11716`). It is pushed into the camera with one setter (below). `usb-storage`, `sd-card`, `other`,
  `unknown` and "nothing mounted" have no column: the limit is the USB SSD column (the slowest measured) with the label
  **unconfirmed** and the text "Storage type not measured". Owner question 8.
- **Board** from `pi_model`. Only `pi5` (Pi 5, CM5) has cells (measured on a CM5 Lite; the Pi 5 is the same SoC:
  **probable**). On any other board the table gives no limit: only the sensor ceilings apply, and the line says
  "Limits are not measured on this Raspberry Pi". The board is part of the key now so Pi 4 rows can be added later.
- **Take length** is fixed at 30 minutes (R6). The short-take numbers are information.
- **Drive heat** is assumed hot (R6). A drive-model guard is an option: for drive-limited cells, `min(fps30,
  0.75 x speed-test MB/s / MB per frame)` when a `run_media_speed_test` result exists (`App:16064`); 0.75 is warm
  465 MB/s over the cold 620 (derived). Only lowers a limit. Commit D8, optional.

### Levers: how Core reads them, and when a change applies

One struct `ladder::Context { Kind storage; Board board; bool tdn, lock, log, aidsOn, audioOn, splitOn; MediaFilesystem fs;
double fillFraction; }`. The camera owns tdn, lock and log already. App owns the rest (audio and aids in the UI snapshot
`App:1882`, `1930`; split in `bufferbudget::framesPerFolderRequest()` `BufferBudget.hpp:319`; media in `mediaProfile_`).
App builds the struct and calls `camera_.setLadderContext(ctx)` from the places that already change those values: the
media change hook (`App:11704-11713`), the UI.conf reload, `set_frames_per_folder`, and each `set_*` that touches a
lever. `setLadderContext` takes `mutex_`, stores it, and calls the same single path as every other change:

```
ladderReapplyLocked():  next = settings_; changed = ladderRewriteLocked(next); if (changed) applySettingsLocked(next, true);
                        if recording_: ladderStale_ = true   // evaluated again in the take's stop path
```

Nothing changes during a take; the pane shows "applies after this take". The steps themselves are never stored: they
are a pure function `buildSteps(enabledModes, ctx, sensorStates)` computed on every read (`get_mode_ladder`, state build),
so a lever change is visible on the next read with no stale copy. That is "recomputes when a lever changes": the
function is cheap (under 10 modes x one table lookup).

### Enabled resolutions: where the list lives and how an edit reaches the ladder (R7)

- **Where**: one camera-wide key, `dynres_modes=3840x2160:16:hdr,1920x1080:16:hdr,...` (the same `WxH:bits:hdr|sdr` text
  `parseRungs` reads today, without the fields after the third). It sits in `camera_settings.conf` with the other
  camera-wide keys (the `tuning_file` shape, `camera-modes.md` commit 10). Until that commit lands the key lives in
  `mode_ladder.conf` and moves with it. The old `resolutions=` line is read once as the list (thresholds, compression and
  log fields dropped); the old `enabled=` becomes the switch.
- **Default**: when the key is absent, all non-crop modes of the sensor's native aspect that the probe offers (IMX585:
  the seven in the rule above). Crop-ins and other aspects are opt-in. Stock rule: on by default is the owner's call (R1).
- **Edit**: `set_mode_ladder enable_mode=WxH:bits:hdr|sdr` / `disable_mode=...` (one tile click, atomic) or
  `modes=<list>` (whole list). Same command name and the "resolution" wording (DB-47), so no new API. In `setModeLadder`
  (`CC:11995`) under `mutex_`: refuse in a take ("Stop recording before changing the enabled resolutions", as `CC:12026`),
  validate each mode against the pool, refuse an empty list ("Enable at least one resolution"), store, save, then
  `ladderReapplyLocked()` so the running mode follows at once, and return the rebuilt `steps` in the reply and emit the
  settings event (`emitSettingsEventLocked`). The WebUI redraws the pane from that reply. The touch UI gets the new
  `ladder_text` / `limit_*` fields from the event.
- **Pool changes** (sensor probe result, driver change): modes absent from the pool are dropped from the list at load
  (`followDriverCropSizes`, `CC:536`, still maps 2076/2072 sizes).
- A mode enabled that no storage cell reaches still counts: its cap is the sensor ceiling or "no measurement".

### What the screens show

State fields (flat, scalars, filled **always**, also with the switch off):

| Field | Example |
| --- | --- |
| `limit_fps` | 20 (cap of the running mode at the current storage and levers; 0 = unknown) |
| `limit_short_fps` | 27 |
| `limit_basis` | `measured` / `derived` / `probable` / `unconfirmed` / `sensor` (no measurement) |
| `limit_by` | `back end` / `encoder` / `drive` / `sensor` / `TDN` |
| `limit_why` | one sentence, below |
| `ladder_enabled`, `ladder_active` | the switch; the switch and a covered format |
| `ladder_text` | "4K Clear HDR 16-bit - Uncompressed - up to 20 fps" (kept) |

`get_mode_ladder` replies with `steps` (per enabled mode in order: label, cap, fps30, basis, wall, why, `from` fps) and the
lever info strings (flat keys `info_tdn`, `info_lock`, `info_audio`, `info_aids`, `info_log`, `info_split`,
`info_webui`), so the UIs show the table's own wording. `ladder_tops` and `ladder_resolution` go; the WebUI's
`ladderResolutionForFps` (`WCP:9094`) reads `steps` instead.

"Why" texts (exact wording, one sentence each, Core builds them from the cell):

| Case | Text |
| --- | --- |
| mode holds F | `4K Clear HDR 16-bit holds 20 fps for 30-minute takes on this NVMe card (unconfirmed). 27 fps holds up to 8 minutes (measured).` |
| stepped down | `At 25 fps the camera records 2K Clear HDR 16-bit: 4K Clear HDR 16-bit holds 20 fps for 30 minutes on this NVMe card (unconfirmed).` |
| HDR given up | `At 33 fps the camera records 4K SDR 12-bit: 2K Clear HDR 16-bit holds 30 fps (probable).` |
| drive | `This USB SSD writes about 105 MB/s: 4K SDR 12-bit holds 18 fps (derived). At 25 fps the camera records 2K Clear HDR 16-bit.` |
| nothing holds F | `No enabled resolution holds 60 fps here. Highest: 2K SDR 12-bit, 60 fps. FPS set to 60.` |
| TDN | `Preview temporal denoise is on: 4K drops frames at every rate tried (from 23 fps). 2K is used. Turn it off to use 4K.` |
| phase lock | `Phase lock is on: 4K Clear HDR 16-bit + Log holds 23 fps instead of 24.` |
| split off | `Split long takes is off: takes over 30 minutes slow down above 32 fps. Turn it on.` |
| storage | `Storage type not measured (SD card): limits are the USB SSD's. Run the speed test.` |
| board | `Limits are not measured on a Raspberry Pi 4.` |
| pending | `Storage changed: the camera switches to 2K Clear HDR 16-bit after this take.` |
| off | pane greyed: `Dynamic resolution is off. The camera keeps your mode. Known limit: ...` |

Places: WebUI Settings > Modes, pane "Mode Ladder" (becomes "Dynamic resolution", the card keeps `WCP:6017`): On/Off
buttons (DB-49), "Running now" box (exists, `WCP:6032-6039`), read-only steps list (mode, fps range, cap, label chip, wall,
why), the take-length line "30-minute takes, hot drive" and a footer with storage and board. Greyed (class `off`,
buttons inactive, text still shown) while off; active while on. Under the FPS pills the existing `fpsLadderLine`
(`WCP:5366`) shows `limit_why`; the quick pill `quickLadderPill` (`WCP:5359`) reads "Dynamic resolution". Touch UI: one
switch "Dynamic resolution" in Settings > Recording format beside Compression (`SettingsPage.qml:3428`, which already
reads `ladderActive`), and the limit line under the FPS picker (the picker already cuts at `fps_max`,
`ApertarControlBridge.cpp:1811`). The touch UI never edits the enabled list (DB-53 stands for the editor).

### Information and behaviour

| Part | With the switch off (information only) | With the switch on (changes behaviour) |
| --- | --- | --- |
| `limit_*` fields, `limit_why`, `steps` in `get_mode_ladder` | filled | filled |
| Limit line under FPS (WebUI, touch UI), pane text, lever info lines | shown (pane greyed) | shown (pane active) |
| `fps_max`, `fps_take_max` | the sensor's, as today | the ladder's caps |
| Mode, bit depth, Clear HDR, compression follow the fps | no | yes, between takes |
| Manual `set_resolution` / `set_raw_bit_depth` / `set_clear_hdr` | free | blocked (DB-45) or pinned (owner question 1) |
| fps clamp when above the best cap | no | yes |
| Split automatic, TDN control | only if chosen | only if chosen |
| Storage, lever or list change | refreshes the line | re-evaluates and applies after the take |

Is information-only acceptable on a stock camera? It changes what is shown, not what the camera does, but the numbers
are one rig's drives. With R1 (on by default) the question is moot for the ladder itself; the info lines that appear with
the switch off are the pane (greyed) and the lever info lines, both static or table-fed text. The 1.6.0 touch UI has none of
this, so the touch UI line and switch are the one visible change the original developer will see: they are small and
named (commit U2).

### During a take

The mode never changes. The fps picker in a take is limited to `fps_take_max` (the running mode's cap), as
`CC:11634-11640` does now. Speed ramp (`fps_speed_ramp`) moves fps inside that cap (owner question 7). A storage
change in a take (card pulled) is the existing media fault path; the ladder only re-evaluates afterwards.

### Split: off / on / automatic, default on (R11)

Today `frames_per_folder` is a number, 0 = one folder, `[storage]` key and `set_frames_per_folder value=0|100..100000`
(`App:14118-14124`, `BufferBudget.hpp:319`, `requestedFramesPerFolder`). New: a mode `split=off|on|auto` beside the number
(`frames_per_folder` stays the part size, default 5000). `off` = today's 0. `on` = part size, always, for per-frame
formats (cDNG, lossy DNG). `auto` = on when a 30-minute take outlasts the flat-folder time, t* = 1.9e6 / F^2 < 1800 s, i.e. F > 32, for per-frame formats on
exFAT or FAT (PA 3b); off for MLV, ProRes, H.264 (one file per take) and on ext4
(no measurement: **unconfirmed**, the rule is exFAT's directory list). Evaluated at take start with the chosen fps and
format, by the code that already reads the request at each take ("the camera reads frames_per_folder again at each take",
`App:289`). The state publishes `split_mode` and `split_effective` so the line can say "Split: on (automatic, 33 fps)".
Default `on` is the owner's; it changes a stock camera (1.6.0 has no split) and so does the clip-merge after the take:
flagged in "For the owner" 10.

### Optional TDN control (R9)

`dynres_tdn=keep|off_in_4k`, default `keep`. With `off_in_4k`, when the chosen mode is unbinned (4K, crops) and `preview_tdn`
is on, Core calls the existing `setPreviewTdn(false)` (`CC:12940-12953`, a pipeline restart, so between takes only), stores
`tdn_user=true` and says so in the line; when the chosen mode becomes binned and `tdn_user` is set, it sets TDN back on.
`keep` never touches TDN: a 4K mode then has cap 0 while TDN is on (table B) and the line says why.

## What goes, what stays

| Goes | Where | Why |
| --- | --- | --- |
| Thresholds, per-rung compression and Log, Ramp-ready | `Rung::threshold`, `compression`, `cdngLog` (`ModeLadder.hpp:17-27`), `Ladder::rampReady`, `parseRungs` fields 4-6, `rungsText`, `ramp_ready` | the table decides; DB-46 had already dropped Ramp-ready |
| The validator | `validate` `ModeLadder.hpp:250-300`; rules about rising thresholds, repeats | no user order or thresholds left. "Never used" becomes a note on a step |
| The editor | `WCP` rows, ordering, thresholds, Max boxes, `createLadderRow`, `ladderArranged`, `ladderOrderProblem`, `ladderDraftProblem`, `saveModeLadder` (roughly 700 of the 1,100 lines between `WCP:8615` and `9728`, and most of the CSS `WCP:1629-2137`; the pool tiles and `imx585LadderGroups` stay) | **probable** counts, by function names |
| `resolutions=` text with fields, `mode_ladder.conf` as its own file | `CC:408-430`, `11421`, `11858-11892` | one key in `camera_settings.conf` |
| `ladder_tops`, `ladder_resolution`, `ladder_count` | `CC:182-189`, `App:336-343`, `10193-10200` | replaced by `limit_*` and `steps` |
| The take-over of an old file | an old `mode_ladder.conf` is read once, converted, then ignored | the owner's DB-55 ladder (4K HDR16 lossless up to 25, 4K SDR12 lossless 25-30) becomes the enabled list; his lossless HDR16 becomes uncompressed (lossless HDR16 overflowed the queue, 14 fps encoder limit) |

| Stays | Where |
| --- | --- |
| Sanitiser as the source of what a mode can do | `ladderStatesLocked` (reduced to valid, usable, sensor ceiling) |
| Rewrite before the one apply, never in a take | `ladderRewriteLocked` and its five callers |
| The block on manual mode changes (or the pin, question 1) | `CC:11563`, `12563` |
| `ladderOverride_` for an explicit `set_clear_hdr` | `CC:12608-12649` |
| The aspect filter as a display filter | `ModeLadder.hpp:211-247` |
| `Activated sensor modes` card, now "Enabled resolutions" | `WCP:6009` |
| CAM1 follows the closest enabled mode, ladder runs on CAM0 only | `WCP:8744` |
| `get_mode_ladder` / `set_mode_ladder` names, the cam1 relay | `App:13497-13540`, `15482` |

Dual recording: the table is for one sensor; two cameras share the drive and the CPU. The line says "Dual recording is not
measured: limits are for one sensor" and the caps are not lowered (the dual case is to be computed, `estimator-campaign/plan.md`).

## Lever info lines (exact texts, taken from table B and PA 2b / 5a)

Core holds the strings in `SustainedFps.hpp`; the WebUI shows them from `get_mode_ladder`. Numbers come from the same rows.

| Switch | Text (one or two lines) |
| --- | --- |
| Preview temporal denoise | Costs about 5 fps and drops frames in every 4K mode; leave it off while recording 4K. No cost at 2K. |
| Frame-rate phase lock | Costs about 1 fps at the limit of 4K Clear HDR and Log; no cost at 2K or in lossless modes. Use it only when you sync to something. |
| Record audio | Costs under 1 fps, only at the limit of 4K Clear HDR. Record sound as you like; at the limit, turning it off gains about 1 fps. |
| Focus peaking / zebra | No measured cost. At the limit of 4K Clear HDR the camera lost fewer frames with them on. Leave them on. |
| Log | Makes Clear HDR 16-bit files a quarter smaller but costs 2 to 3 fps in 4K. No effect in SDR, no cost at 2K. |
| Split long takes | Needed for long cDNG takes: a folder with many files slows file creation. Automatic turns it on above 32 fps. No effect on MLV, ProRes and H.264. |
| WebUI client (note under Live preview) | A connected WebUI costs about 0.5 fps, only at the limit of 4K Clear HDR. Close it on the shoot day. |

Where they sit: WebUI `WCP:6680` (Preview temporal denoise note, replaces the long text), `6694` (phase lock), `6385` (Record
audio), `6220` and `6239` (peaking, zebra), `5793-5797` (Log, `settingsCdngLogNote` keeps its "Linear storage" state line),
`6590` (split). Touch UI: `Record Audio` (`SettingsPage.qml:4171`, the `description:` line), `Focus Peaking` (`2751`) and
`Zebra` (`2787`) cards, `Log` (`3448`), `Split Long Takes` (`5435`). The touch UI has **no** TDN or phase-lock switch
(only `cameraFpsPhaseLock` in presets, `ApertarControlBridge.cpp:1294`, `1787`), so those two texts are WebUI only; no
switch is added (owner question 9).

## Commit plan

Dependencies: after `camera-modes.md` commit 3 (`min(table, probe)` ceiling) and commit 10 (ladder in
`camera_settings.conf`). If commit 10 is not in, D3 writes the keys into `mode_ladder.conf`. Small commits, Core, then
WebUI, then touch UI. Checks "here" run on this x86 machine; Pi checks are for the owner's rig (CM5, IMX585, MP600 Mini,
HDMI, no touch screen) and are command blocks he runs.

| # | Commit | Files | Checks here | Pi checks |
| --- | --- | --- | --- | --- |
| D1 | `camera: known-limits table` (information only, no caller) | new `src/camera/SustainedFps.hpp`, `tools/sustained_fps_test.cpp` | `g++ -std=c++20 tools/sustained_fps_test.cpp`: step rounding, lookup order, nearest-larger rule, lever shifts, TDN cap 0, split formula (32), table A values pinned | none |
| D2 | `camera: Core reads the storage and lever context` and publishes the known limit | `CameraController.{hpp,cpp}` (`setLadderContext`, `fillLimitFieldsLocked`), `ApertarCoreApp.cpp` (context builder at `App:11704`, UI.conf reload, `set_frames_per_folder`, state fields), state JSON | core-port build with libcamera OFF; `fps_ceiling_test`, `mode_ladder_test`, new test still pass; state fields present, behaviour byte-identical with the switch off | `get_state` on NVMe: `limit_fps` 20 at 4K HDR16, `limit_basis` unconfirmed; pull the card, mount the T7: fields change, camera does not |
| D3 | `camera: Dynamic resolution picks the mode from the table` | `CameraController.cpp` (new chooser, `buildSteps`, enabled list, `ladderReapplyLocked`, `fps_max` / `fps_take_max`), `ModeLadder.hpp` (new `Mode` list + chooser; old code stays until D4), keys `dynres_enabled` (default true), `dynres_modes`, old-file take-over, `set_mode_ladder enable_mode / disable_mode / modes / enabled` | host test of the order (table C reproduced), take-over test (DB-55 file), refusal in a take | `set_fps` 25 / 30 / 33 / 50 on NVMe lands on table C; `get_mode_ladder` before and after; one blocked `set_resolution`; enable and disable a tile: running mode follows at once; nothing changes in a take |
| D4 | `camera: remove the user ladder's thresholds, per-resolution compression and Log, Ramp-ready, validator` | `ModeLadder.hpp`, `CameraController.cpp`, `App` state, `tools/mode_ladder_test.cpp` | host test, build | an old `mode_ladder.conf` still loads |
| D5 | `storage: clip split off / on / automatic` | `BufferBudget.hpp` (`requestedSplitMode`), `App` (`set_frames_per_folder mode=`, state `split_mode`, `split_effective`), the camera's take-start read, `config` template | `buffer_budget` host test: auto turns on above 32 for cDNG on exFAT only | a 33 fps take writes `part_001`; a 25 fps take on auto does not; MLV never |
| D6 | `camera: optional TDN control` | `CameraController.cpp` (`dynres_tdn`, `tdn_user`), command field | host test of the decision | 4K with TDN on and the option on: TDN goes off between takes, back on at 2K |
| D7 | held for owner question 1: `camera: a manual mode pick pins until the next fps change` | `CameraController.cpp` (`ladderOverride_` generalised) | host test | manual `set_resolution` at 25 fps holds, the line says the limit |
| D8 | optional: `camera: drive-speed guard on drive-limited cells` | `SustainedFps.hpp`, `App` (speed-test result) | host test | after `run_media_speed_test` the limit follows the measured MB/s |
| D9 | `docs: how to update the known-limits table` | Core `README.md` or `docs/`, KB `estimator-campaign` link | none | none |
| W1 | `web: lever info lines` | `WCP` (the seven places above) | `node --check` of the page script; the page loads in headless Chromium against a mocked state | read on the rig's WebUI |
| W2 | `web: Dynamic resolution pane` (steps, why, On/Off, greyed when off; tiles enable / disable; split off/on/auto; TDN control switch; limit line under the FPS pills) | `WCP` | node check; Chromium with mocked `get_mode_ladder` for on, off, take, T7 | pane on the rig, tile click rebuilds the steps |
| W3 | `web: remove the ladder editor` | `WCP` JS and CSS | node check; no reference to deleted functions (`grep`) | none |
| U1 | `ui: lever info lines` (Record Audio, Peaking, Zebra, Log, Split Long Takes) | `qml/SettingsPage.qml` | `/home/user/build/ui-port` builds | not run on his rig (no touch screen, DA-77); the original developer or the HDMI build |
| U2 | `ui: Dynamic resolution switch and limit line` | `ApertarControlBridge.{hpp,cpp}` (`limit_*`, `ladder_enabled`, `set_mode_ladder enabled`), `qml/SettingsPage.qml`, `qml/CameraPage.qml` (line under the FPS picker), split Off/On/Auto in the existing dropdown | build | as U1 |

Existing tests to keep green: `tools/mode_ladder_test.cpp`, `fps_ceiling_test.cpp`.

## For the owner

Questions only he can answer; each has a recommendation.

1. **Manual changes while Dynamic resolution is on by default.** DB-45 blocks manual resolution, bit depth and Clear HDR
   while the ladder runs. Combined with "on by default" a fresh camera cannot hold 4K Clear HDR 16-bit by hand.
   Recommendation: a manual pick **pins** until the next fps change or until the switch is turned off (D7); the line then
   shows the known limit and says it is the operator's choice. Without this the on-by-default switch is a stock-behaviour
   change for every user.
2. **4K Clear HDR 16-bit at 24 and 25 fps.** The 30-minute caps give 2K Clear HDR 16-bit there, because 25, 26 and 27 all
   failed a 15-minute take (P6: 27 failed after 190 GB). The cell for 30 minutes (20) is a placeholder. Recommendation:
   keep 30 minutes as asked, show "holds 27 fps for 8 minutes" in the line, and run the three 30-minute hot takes
   (4K HDR16 at 24, 22, 20) before the table is final. Or add a take-length choice (8 / 30 minutes); the table already
   carries both numbers.
3. **Order, literal reading.** Resolution, then bit depth, then HDR to SDR, with HDR/SDR kept longest, lets giving up HDR bring
   4K back (33 fps: 4K SDR 12-bit). The alternative never raises resolution again as fps goes up (33 fps: 2K SDR 12-bit).
   Recommendation: the literal reading (more picture at the same fps); the conservative caps make both land on 2K for
   most steps anyway.
4. **Bit depth 16 to 12 in Clear HDR on this rig.** 4K HDR12 holds less than 4K HDR16 (back end drops frames at every fps
   25-30), so the HDR12 step is never used on NVMe and shows "never used here". Recommendation: keep it listed.
5. **Aspect ratio.** The ladder keeps the running mode's aspect ratio. Recommendation: yes.
6. **Compression.** The table names it per cell (HDR uncompressed, SDR lossless on NVMe; the DB-46 defaults), and the T7
   column uses lossless HDR where it holds more. Recommendation: yes; the operator's compression is owned by Dynamic
   resolution in cDNG, as DB-46 says for the ladder.
7. **Speed ramp inside a take.** Cap at the running mode's 30-minute cap. Recommendation: yes, revisit with P4.
8. **Unmeasured storage and boards** (SD, USB HDD, Pi 4 and others). Recommendation: USB SSD column with the label
   "unconfirmed" for storage; sensor-only limits for other boards; add the speed-test guard (D8).
9. **TDN and phase lock switches in the touch UI.** None exist; the two info lines are WebUI only. Recommendation: no
   new switches.
10. **Split default on** changes a stock 1.6.0 camera (it has no split; the merge after the take follows). Recommendation:
    keep his default, document it in `APERTAR.md` for the original developer.
11. **Crop-ins.** Opt-in, after the non-crop modes of a class, caps from the pixel rule (derived). Recommendation: yes;
    nothing above 60 fps is measured, so 70 and 80 exist only for enabled crops.
12. **TDN control default** `keep`. Recommendation: yes.

## Where the pre-analysis numbers go

All in `SustainedFps.hpp`, table A, B and the pixel-rate row; nowhere else (the UIs show Core's strings). The note says the
full analysis (P4, P6, P5) will replace some numbers; the update steps:

1. Edit the `fps30`, `fpsShort`, `label` and `source` of the cells and rerun `tools/sustained_fps_test.cpp` (the pinned
   values fail on purpose so a change is deliberate).
2. Cells waiting for data: 4K HDR16 and HDR12 NVMe (20, placeholders; 30-minute hot takes), the P6 lossless and lossy
   takes (4K SDR12 40, SDR10 45, crop 56), 2K HDR16 and SDR12 at 30 minutes, the aids sign (table B), TDN-on numbers
   below 23 fps, the T7 in 4K, MLV / lossy / ProRes rows, a second NVMe model, the Pi 4.
3. KB pages that restate numbers (`estimator-campaign/pre-analysis.md` section 1, `drop-frames/README.md`) link to the header
   instead of copying; the header's `source` strings name the KB file and date.
