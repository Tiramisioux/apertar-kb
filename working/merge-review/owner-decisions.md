# Owner decisions for the cinemate-port merge

Every question only Patrik can answer. Rows are ordered by how much work waits on the answer. Item ids are from
`fix-list.md` and the domain files `fix-list-<domain>.md`, where each question has its full cost text. A recommendation
is the review's, not a decision. The work behind each row stays parked until the row is answered. Everything else can
start now.

Rows 1-5 hold back about 55 fix items between them. Rows 1-10 are the ones to answer before any lane starts milestone 1
work in that area.

## Decisions that block the most work

| # | Question | Options and cost | Recommendation | Waits on it |
| --- | --- | --- | --- | --- |
| 1 | Where do buffer mode, frames per folder, clip merge and pre-roll live? | A: `apertar-hardware.conf [storage]`. About 1 day. Has precedent (set_imu_* write the hardware file through the section owner). Buffer stays next to buffer_ram_*. B: `camera_settings.conf`. Several days: CC load/save, profiles, presets, both UIs, a migration. Presets could carry the switches. Either way CameraController stops opening the file (REC-1, rule CAM-19) | A | APP-11, HW-36, REC-1, APP-10, REC-2, APP-12, REC-10, CAM-6, APP-28, APP-21, APP-30, APP-31, WEB-18, WEB-4, REC-40, REC-38, UI-13 (17) |
| 2 | Keep 'Edit file', the free-text config.txt editor on the Boot Config card? | A: drop it. Only lines built from checked fields reach config.txt, as with fan mode. About 800 lines of rework, 300 fewer lines in the end. Hand edits of config.txt go back to ssh, as in 1.6.0. B: keep it with a boot-chain deny-list (kernel, cmdline, os_prefix, initramfs, start_file, fixup_file, device_tree, overlay_prefix, boot_*) and no install fallback. The 1355-line engine and a root write of LAN text stay. The original developer would likely refuse it | A | HW-1 (also APP-1, WEB-1), HW-4, HW-5, HW-11, HW-24, HW-39, WEB-5, WEB-31, APP-13 helper part (9) |
| 3 | IMX585 1.85:1 crop sizes: which names ship? | A: put the driver back to 3840x2076 / 1920x1038. Core and driver merge independently and the 1.6.0 UIs stay valid. Costs one take at each size on the Pi (VST-52 window). B: keep 2072/1036. Core carries a permanent size alias and the README names the driver it needs. Both answers delete Core's rewrite and restore the auto-config fallback | A | CAM-1, CAM-22, CAM-23, CAM-32, CAM-33, CAM-38, UI-5, WEB-6, WEB-29, TXT-8 (10) |
| 4 | FPS ceilings and lossless cDNG policy | A: restore 1.6.0: ceilings min(table, probe), IMX585 lossless capped at 30 fps, lossless ISO 800, manual ISO in lossless. The IMX585 rig loses 1600 / auto / 60 unless it sets a knob. B: keep the IMX585 relaxation behind a per-sensor switch, with the measurement in its own commit. The original developer must accept a product-policy change based on one rig's numbers | A for the ceilings in any case. B for IMX585 lossless only with the measurement | CAM-2, CAM-14 (also REC-4), CAM-6, CAM-9, CAM-30, CAM-45, UI-14, UI-15, WEB-14, WEB-32, TXT-4 (11) |
| 5 | The second tuning file (`apertar-media-tune.conf`, `/run` override, 487-line `apertar-tune`), asked for on 2026-11-02 | A: replace it with upstream's `.apertar-tuning`. Per-medium override sections and the editor script go. The per-medium defaults stay in code. B: keep it, trimmed and documented. The original developer must learn a second tuning dialect, read from inside an encoder | A | APP-14 (also REC-11), APP-15, APP-18, APP-42, REC-13, REC-14, REC-21, REC-37, TXT-10 (9) |
| 6 | Who writes the first-run `apertar-hardware.conf`? The editors disagree | A: Core, the file's single writer, through HardwareConfigStore (APP-16, UI-4). New ground. 578 lines of UI template go. The store's replaced-file check keeps working. B: restore the UI writer as in 1.6.0 (HW-9). Upstream shape, but two writers for one file again. Core's replaced-file check then flags every fresh install unless changed | A, with one handoff line. Fold upstream's [gpio_buttons] chip/tuning and [mpu6050] sections into Core's template either way | APP-16 (also HW-9, UI-4) (3, with the template steps) |
| 7 | Mode Ladder persistence | A: fold it into `camera_settings.conf`. One camera settings file. Costs a one-time migration read of the existing `mode_ladder.conf`. B: keep the separate file. The original developer learns a second camera settings file with its own writer | A | CAM-8, CAM-16, CAM-31, CAM-41, CAM-44 (5) |
| 8 | Mode Ladder rules: in Core or in the page? | A: move the rules into Core and show its dry-run answer. Size L: ModeLadder.hpp and about 250 page lines, and the approved editor must be tested again. B: keep the JS rules as documented new ground. Two rule sets that must change together, and they differ already | A | WEB-7, WEB-19, CAM-17, CAM-19 (4) |
| 9 | Timecode: keep a separate file timecode, and the new labels? | A: restore 1.6.0. One mode for screens and files, labels Free Run / Rec Run. Propose the split and the rename later in their own PR. B: keep `target=`, the second dropdown (default "Same as Mode") and Time of Day / Clip. Needs a handoff paragraph on the exception to CMD-26 | A | UI-1, WEB-13, APP-45 (3) |
| 10 | Clip-name composer: drag-and-drop or typed? | A: a text field with a token palette in both UIs. No drag. About 1170 lines of drag code go. B: keep drag as documented new ground: z-index <= 100, a rebuild of the touch card on the reorder pattern (M), and a hand test on the panel. A middle way: keep drag in the WebUI, tap-only on touch (UI-8) | A (both UIs). Tap-only on touch is the minimum | WEB-8, UI-8, WEB-26, UI-10 (4) |

## Architecture: keep as documented new ground, or rework

The editors already chose rework for the foreign mechanisms (APP-5 reply builder, APP-7 dispatcher, REC-2 statics,
CAM-4 TDN JSON parser, CAM-5 request callback, HW-12 ActionCatalog, HW-13 page store, WEB-2 to WEB-5 page layers).
Confirm that list, or name one to keep. The rows below are new ground the editors propose to keep.

| # | Question | Options and cost | Recommendation | Waits on it |
| --- | --- | --- | --- | --- |
| 11 | Keep the big new features at all: storage pre-roll, Mode Ladder, RAM write buffer with safety stop, split takes with merge, speed ramp, Clip Browser and Viewer, Controls page, Boot Config card | Keep: each needs its rework item and a "New in this fork" note (TXT-9). Drop one: its code and items go, the PR shrinks | Keep all; each that touches stock behaviour stays off by default | TXT-9, the handoff |
| 12 | Hardware-file engines: HardwareConfigStore (one writer, revision, history, Undo), hwconf (a table-driven model of every reader, 1141 lines), Boot Config engine (1355 lines) | Keep and document: the original developer maintains three header-only engines. Rework: per-reader checks in each hardware class, as upstream does | Keep the store (APP-43). Keep hwconf after its drift is fixed (HW-10). Boot Config engine size follows row 2 | APP-43, HW-10, HW-11 |
| 13 | Edge events instead of GPIO polling (HW-31), frame-rate phase lock (CAM-28), per-file writeback and 1 s fsync sweep (REC-22), safety stop (REC-32) | Keep: fix the listed defects and add a handoff paragraph each. Drop: back to upstream's poll loop and static fps pin. The measured gains go | Keep all four | HW-31, HW-32, CAM-28, REC-22, REC-32 |
| 14 | Host tests in `tools/` (20 tests outside CMake) | Keep outside CMake with one build line each: the least foreign shape for a code base without tests. Wire into CMake: new ground in the build. Delete: the evidence goes | Keep outside CMake, one documented build line | APP-42, CAM-30, HW-39, REC-37 |
| 15 | 2100-line structured hardware editor: chip box, pin-claim cascade, review re-derivation | Cut the three: multi-action lines are edited as text, a used pin is freed by hand. Keep all: about 2100 lines of page code for the original developer | Cut | HW-15 |
| 16 | Script paths from the browser (your earlier answer Q2: ssh only) | A: restore 1.6.0, the browser edits [run_script] paths. A LAN client can point a button at any readable file, but it runs only on a press (test_input refusal done, `d1dcdee`). B: keep Q2. Then Undo and restore must be exempt from the path check, and Q2 goes into the README | A | HW-3, HW-33 |
| 17 | Playback overlay: phone Back through the History API | Keep: about 30 lines, the one router-like hook in the page, documented. Drop: Back leaves the page | Keep | WEB-3 |
| 18 | Speed-ramp stretched WAV (rubberband) | Keep in Core with a waited argv launch and an install check, default on as chosen in `ca7b7c2`. Move to an offline script: Core loses an undeclared dependency | Keep in Core, fixed | CAM-25 |
| 19 | Fan mode only through Core's writer | Keep the single writer: no fan change while Core is stopped. Restore the UI writer: a fan change can overwrite a Boot Config save | Keep while Boot Config exists | HW-37 (also UI-27) |

## Defaults and stock behaviour

Restored already, owner to confirm: preview TDN on (`3650027`), pre-roll off (`0977dd6`), 720x720 display
(`7dc6f7a`, `6a59d83`), audio outline off (`2d9cf94`, `ff4c7c5`), HDMI timecode white (`ac1fc28`), imx283 crop_vmax off
(`36d484b`), lossy DNG page drop (`615b48c`). The review restores these defaults without asking (fix-now): media trim
off (REC-3), upstream writer table on vfat/NTFS (REC-13), raw pool freed between takes (REC-14). `DONTNEED=sync` stays,
because it is the measured cDNG default.

| # | Question | Options and cost | Recommendation | Waits on it |
| --- | --- | --- | --- | --- |
| 20 | Raw request count in SDR takes | A: upstream's 3 requests of 4 buffers in SDR, 8 of 8 in Clear HDR. B: one request per buffer everywhere, measured only in 4K Clear HDR 16-bit on a CM5 | A | CAM-7 |
| 21 | Pre-roll frame rate | Recordable maximum (maximumFpsForSettings, what a take can reach). Or the sensor maximum, past the lossless and ladder caps | Recordable maximum | CAM-6 |
| 22 | A button that reads pressed at start (1-0-1 inversion) | Drop the guess: a normally-closed button sets active_low. Keep it as new ground: held buttons are inverted at every save of the GPIO group | Drop | HW-8, HW-31 |
| 23 | set_resolution with an IMX585 size the class lacks | Take the nearest row silently, like every other limit: a wrong size comes back as another size. Or keep the refusal: an IMX585-only exception to rule CAM-21 | Nearest row | CAM-26 |
| 24 | imx585 960/1024-wide families and the Clear HDR test parameter | Drop them from the Apertar driver: no hidden modes, no Core filter. Cinemate use needs its own branch. Offer them: 42 unvalidated modes on the menus | Drop | CAM-27, CAM-38 |
| 25 | Remote controls: hold-to-repeat on the knob arrows | Drop: one tap per step. Keep: a widget behaviour no other control has, to be documented | Drop | HW-14, HW-33 |
| 26 | ISO and WB badges: the word Auto | Add Auto back in front of the live value: a slightly longer badge. Keep value-only: auto and manual look the same | Add Auto back | WEB-12 |
| 27 | White dropdowns on the Controls panel | Remove: they look like every other select. Keep: propose a page-wide `.settings-select` change to the original developer | Remove | WEB-9 |
| 28 | Presets restore preview denoise and media trim? | No: they are camera-wide switches, one comment line. Yes: two preset keys | No | APP-47 |
| 29 | Socket fields sensor_binning, sensor_binning_source, sensor_crop | Keep only if a tool you use (the KB test rig) reads them. Delete: the rig script changes | Delete unless a tool reads them | APP-34 |

## History and shipping

| # | Question | Options and cost | Recommendation | Waits on it |
| --- | --- | --- | --- | --- |
| 30 | AI attribution in merged commits | A: one line `Co-Authored-By: Claude <noreply@anthropic.com>`, author Patrik on every commit, no model name, no session URL. Honest and uniform, but it differs from upstream's trailer-free history. B: drop all trailers to match upstream exactly. Attribution then lives only in the handoff. Today 11 + 14 commits are authored "Claude", with three model names and session URLs | A | TXT-6, UI-9, TXT-1 to TXT-5, CAM-38 |
| 31 | Which driver branch ships to Apertar | A: merge the clean driver series into the branches the Apertar image already builds (`apertar` for imx585, `master` for imx283). The image needs no change. Cinemate keeps `cinemate-modes`, and the two branches are kept in step by hand. B: make `cinemate-port` the Apertar branch. The image build script changes | A | TXT-8, CAM-38, CAM-23 |
