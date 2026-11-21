# Sweep X6: text that must not reach the original developer

Scope: lines added by the port (`git diff -U0 --minimal origin/main cinemate-port`) in Apertar-Core (107 files), Apertar-UI (30 files), imx585 driver (9 files vs `origin/apertar`), imx283 driver (8 files vs `origin/master`). Method: per-line scan of added lines with regexes for each kind, then reading context for the worst cases. Counts are of matching comment/README lines, so one multi-line comment counts once per matching line. Labels: **confirmed** = read in code.

## Result in six lines

| Kind | Count (added comment/doc lines) | Verdict |
| --- | --- | --- |
| (a) internal refs: T##, Q##, R#, O#, WP-, "request N", "critic", "design §", "kb working/" | 272 (Core 179, UI 14, imx585 62, imx283 17) | Main problem. Meaningless to the original developer. |
| (a) names, dates, clip numbers, test nights ("Patrik", "(User, 2026-11-03)", "C0106", "test night", "campaign") | 79 (Core 43, UI 5, drivers 31) | Remove. |
| (a) "Cinemate"/"cinepi" as source or justification | 126 hits (many are fine as a provenance line in a file header; about 60 are justifications mid-code) | Keep at most one provenance line per ported file; drop commit hashes and "as Cinemate does". |
| (b) history narration | 78 | Rewrite to what the code does now. |
| (c) AI residue (Claude, Sonnet, Opus, Codex, "as an AI", apology, promo, emoji) | 0 confirmed | None found. Regex `let.s` matched "deletes"; discarded. Emoji: none. |
| (d) leftovers | 0 in port code | No TODO/FIXME/HACK, no commented-out code, no debug prints in port-authored code. Only `third_party/liblj92/lj92.c` (vendored, keep as is: 1 TODO at :300, 5 commented lines at :254 :455 :493 :984-986). `-Wunused` warnings: none from the port (see below). |
| (e) operator-facing strings | no mismatch of tone; 2 items | See section E. |

Second finding class, not in the brief's list but the largest by volume: **comment density**. The port comments 3 to 10 times more than upstream (section D).

## A. Table: file | kind | count | three examples

Kinds: ID = internal reference; NAME = name/date/clip number/test night; CIN = Cinemate or cinepi mention; HIST = history narration. Sorted by count. Caveat: in `qml/ClipNameCard.qml` and `qml/ClipNamePill.qml` "owner" means the QML parent component (matches 3 NAME lines): false positive, ignore.

| repo | file | kind | count | three examples (line: text) |
| --- | --- | --- | --- | --- |
| d585 | imx585.c | ID | 53 | `606: * crop family (WP-585-6) needs neither instantiation: its entries set` ; `709: * deliberately absent: WP-585-8 (2026-09-21) found every windowed 2x2` ; `769: * Mode array layout (WP-585-5: one entry per (table, advertised size) --` |
| core | src/ApertarCoreApp.cpp | ID | 52 | `92: // WebUI-open drops (kb working/dng-chain, V/H4).` ; `1272: // T33 (request 24): a list works on any sensor. The values up to the mode's cei` ; `1308: // Free stepping (T33): move by the increment between the list's ends instead of` |
| core | src/web/WebControlPage.cpp | ID | 32 | `1398: /* Value lists (T33): one chip per value, x removes it. */` ; `1979: /* Playback (T49): the touch UI's Clip Browser, in the WebUI's shell. */` ; `2505: /* Playback (T50): the Clip Viewer. */` |
| core | src/camera/CameraController.cpp | ID | 27 | `403: // T34: the mode ladder lives beside camera_settings.conf (same XDG rule), one l` ; `3034: // T34: a ladder resolution names its own raw format (Patrik, 2026-10-28): uncom` ; `3430: // are lost under load (KB working/research-30fps-answer.md, working/drop-frames` |
| core | src/camera/CameraController.cpp | CIN | 16 | `441: // The imx585 driver's 1.85:1 crops are 3840x2072 and the binned 1920x1036 (cine` ; `442: // cinemate-port driver branch). The Apertar-Beta 1.6.0 driver had 3840x2076 and` ; `1462: // get two more buffers of cushion, as Cinemate's profiles do (8 ext4 /` |
| d283 | imx283.c | HIST | 16 | `364: * stale explicit value behind. This field only carries an explicit` ; `369: * be used to guess at those.` ; `428: * byte-identical between the two files, which proved they were stale` |
| core | src/camera/CameraController.cpp | HIST | 13 | `444: // Settings, presets, ladder rungs and clients (the touch UI) that still say the` ; `699: // A template that no longer parses (hand-edited file) falls back to the origina` ; `3025: // Patrik's rule (2026-10-28, after the temp build): Clear HDR records uncompres` |
| core | src/camera/CameraController.cpp | NAME | 13 | `3025: // Patrik's rule (2026-10-28, after the temp build): Clear HDR records uncompres` ; `3034: // T34: a ladder resolution names its own raw format (Patrik, 2026-10-28): uncom` ; `3070: // and Patrik's rule keeps both depths alike) and with its ISO cap. Whatever tur` |
| d283 | imx283.c | ID | 12 | `26: * Read-only mode-geometry controls (WP-283-5). Named, not identified: the` ; `394: * This distinction is critical: advertising active-only dimensions while` ; `924: * veff is mainline's value for 2x2 binning (WP-283-3), the` |
| d283 | imx283.c | NAME | 12 | `265: * get_mode_table()) until they clear hardware validation; a module owner` ; `439: * 2736 columns: measured 2026-09-26 on 2784x1828, optical black 0-47,` ; `765: * horizontal optical black in its expected place -- measured 2026-09-22 on a` |
| core | include/apertar/core/Types.hpp | ID | 9 | `141: // Speed ramping (T31): FPS may change during a cDNG/MLV take. Frames are then` ; `181: double fpsTakeMax = 0.0;  // Runtime (T34): the highest FPS a take in the curren` ; `182: bool ladderActive = false;     // Runtime (T34): the mode ladder picks the senso` |
| d585 | README.md | CIN | 9 | `37: git clone -b cinemate-port https://github.com/Tiramisioux/imx585-v4l2-driver.git` ; `148: ## CineMate branch (`cinemate-7modes`)` ; `152: the CineMate stack. It takes `innomaker-v1.0`'s clean WINMODE` |
| core | src/web/WebControlPage.cpp | CIN | 8 | `4912: <div class="settings-field-grid" id="settingsCdngLogField" data-search="log cine` ; `7566: // The first step above it stays and lands on the ceiling, as in Cinemate; no Au` ; `7900: // The mode's window inside the sensor's readout area (Cinemate's cropDiagram), ` |
| d585 | imx585.c | NAME | 8 | `709: * deliberately absent: WP-585-8 (2026-09-21) found every windowed 2x2` ; `794: *       table. WP-585-8 (2026-09-21): the family's 2x2-binned RAW16` ; `820: * WP-585-10 (2026-09-27): a second, narrower pair of sensor windows -- 1920` |
| d585 | tools/clearhdr-gate/README.md | ID | 8 | `1: # WP-585-9 hardware gate: windowed 2x2 crops in 12-bit Clear HDR` ; `9: WP-585-8 (2026-09-21) settled the RAW16 half on hardware: every windowed 2x2` ; `71: verdict (`PEDESTAL`, `REAL`, `UNCLEAR`). The criteria are WP-585-8's:` |
| core | src/ApertarCoreApp.cpp | CIN | 7 | `1293: // 50 Hz: 90, 180, 270, 360. (Cinemate's two versions use 1 / mains or hz / (fps` ; `4387: // "change" event can make it remount the drive (Cinemate f01b6cd).` ; `5052: # sized from the free memory at the start of a take (CineMate style). ram refuse` |
| core | src/playback/DngTags.hpp | ID | 7 | `3: // Apertar playback, design sketch v2 (not in any repository).` ; `5: // liblj92, so T47 compiles before liblj92 is copied in T48 (critic B2).` ; `9: // Part 2 (DngFrameReader.hpp, T48) reads the samples.` |
| core | src/web/WebControlPage.cpp | HIST | 7 | `9078: // What Core reports, with the old driver's 1.85:1 sizes (3840x2076, 1920x1038) ` ; `10181: // heading or data-search matches. All words of the query must be found in the u` ; `12343: // Outcomes of a frame request: ok, hold (409), busy (503 or a failed fetch), go` |
| core | src/ApertarCoreApp.cpp | HIST | 6 | `5585: // the old model assumed 12-bit packed for every raw format (T21).` ; `11395: // helper the camera runs exactly as before, with one journal line saying so.` ; `11834: // The clip list was read before this pause, and the worker's 2-s take check doe` |
| core | src/playback/ClipProbe.hpp | ID | 6 | `3: // Apertar playback, T47 part B1 (reference for the tutorial; not in any reposit` ; `6: // The texts follow the touch UI's rules so both screens say one thing (design §` ; `11: // and swapped in (critic m14).` |
| d585 | APERTAR.md | CIN | 6 | `11: Use **`cinemate-port`**. It is `cinemate-modes` (the IMX585 modes of the` ; `12: CineMate stack) brought onto the Apertar history: the mode tables, the overlay` ; `13: and the tools are the same as on `cinemate-modes`. It replaces the older` |
| core | src/playback/ClipFrames.hpp | ID | 5 | `3: // Apertar playback, design sketch v2 (not in any repository).` ; `4: // The frame list of one clip folder, and the map from time to frame (critics M1` ; `14: // What stays as on the touch screen (parity, operator P15): the list is every *` |
| core | src/playback/DngFrameReader.hpp | ID | 5 | `3: // Apertar playback, design sketch v2 (not in any repository).` ; `4: // Part 2 of the reader (T48): the samples. Uncompressed 16-bit LE or 12/10-bit ` ; `8: // v2 (critics M4, M8, m2): before each chunk or tile the caller's stop() is ask` |
| core | src/util/MediaProfile.hpp | CIN | 5 | `17: // The recording medium, classified two ways, as Cinemate does it: the` ; `25: // measurement in T29, not Cinemate's numbers copied.` ; `80: // A fallback that cannot say no is not a fallback (Cinemate 888093c): nothing` |
| d283 | EXPERIMENTAL_CROPS.md | ID | 5 | `23: >   Those floors are unmeasured. The WP-283-3 table below records the code as` ; `99: ### `experimental_modes` module parameter (WP-283-4)` ; `130: ## WP-283-3: vertical-crop mechanism verified against mainline` |
| d585 | tools/clearhdr-gate/README.md | CIN | 5 | `25: - CineMate `dev` with `image_capture.hdr.imx585_clear_hdr_12bit` set to `true`` ; `28: - The Clear HDR blend at menu 5, which CineMate sets when a Clear HDR mode is` ; `48: and `cinepi-raw --list-cameras` lists 1920x960 and 1080x1080 under` |
| core | README.md | NAME | 4 | `319: At 4K Clear HDR 16-bit the ISP back end's job drops from about 37 ms to about 6 ` ; `329: On exFAT every new file walks all entries of its folder under the filesystem's l` ; `339: Most of these knobs can also be set in a media tuning file, so a test night need` |
| core | src/ApertarCoreApp.hpp | ID | 4 | `173: std::atomic<bool> mediaDeleteActive_{false};   // T50, Q23: a media delete is ru` ; `174: std::atomic<size_t> controlsErrors_{0};        // T37: what the validator found ` ; `177: // T39: the controls worker applies a saved hardware file by restarting only the` |
| core | src/camera/CameraController.hpp | ID | 4 | `102: // T34: the mode ladder. Any of rungs / enabled / rampReady; dryRun only validat` ; `180: // T34: what the ladder knows of each rung in base's format, the active test, th` ; `243: // Speed ramping (T31): the exposure the operator set, kept across clamps while` |
| core | src/cdng/LogCurve.hpp | CIN | 4 | `13: // CineMate Log: mu-law companding of the signal above black plus a short linear` ; `18: // Same curve as cinepi-raw (cinepi/log_lut.hpp), so files from both cameras sha` ; `48: return "CineMate Log " + std::to_string(sourceBits) + "->" + std::to_string(targ` |
| core | src/hardware/BootConfigText.hpp | CIN | 4 | `4: // Ported from Cinemate's settings-editor config.txt tab (cinemate src/module/ap` ; `8: // What differs is the file. Cinemate's installer writes a fenced block (# >>> c` ; `152: // Link-frequency values are Cinemate's resources/sensors.json: the will127534 I` |
| core | src/playback/ClipProbe.hpp | NAME | 4 | `3: // Apertar playback, T47 part B1 (reference for the tutorial; not in any reposit` ; `8: // ClipFactsCache: an unchanged folder costs ONE stat (its modification time). O` ; `9: // folder's mtime moves with its newest entry (checked 2026-10-29), and a readdi` |
| core | src/util/MediaProbe.hpp | CIN | 4 | `18: // Is the recording medium alive? Cinemate's two independent answers are "is the` ; `23: // yank (Cinemate 58fc7c2).` ; `107: // (Cinemate's cinepi-raw used a substring test and a standby drive kept it true` |
| core | src/util/MediaProfile.hpp | ID | 4 | `21: // Core knew about its drive was a volume label (s2 §1).` ; `25: // measurement in T29, not Cinemate's numbers copied.` ; `133: bool directIo = false;   // for T24's direct I/O, which this fork does not carry` |
| d283 | APERTAR.md | CIN | 4 | `12: Use **`cinemate-port`**. It is `cinemate-modes` (the IMX283 modes of the` ; `13: CineMate stack) plus the fixes made for Apertar since: the mode tables, the` ; `14: overlay and the module parameters are the ones of `cinemate-modes`. What` |
| d283 | EXPERIMENTAL_CROPS.md | CIN | 4 | `27: This branch is an experimental extension of `cinemate-dev`.` ; `64: The original `cinemate-dev` branch is not modified.` ; `97: Modes 1S, 4, 5 and 6 are newly exposed on this branch. Their timing values are d` |
| core | README.md | HIST | 3 | `323: Core does not edit your tuning files. With the switch off it resolves the tuning` ; `347: / `APERTAR_RAW_POOL_WARM=0` / on / Restores the old raw-copy pool: no copies all` ; `348: / `APERTAR_DNG_DONTNEED=writer` or `off` / sync / When a written DNG's pages lea` |
| core | scripts/apertar-media-tune | CIN | 3 | `8: # override the recorder's settings (Cinemate c8f06c9).` ; `10: # Per connection class, starting points taken from Cinemate's storage-automount` ; `93: # NVMe autonomous power states: an exit latency mid-take is a stall (Cinemate se` |
| core | src/ApertarCoreApp.cpp | NAME | 3 | `11398: // Opt-in (APERTAR_MEDIA_TUNE=1). 16-bit 4K25 ran clean without it (2026-10-27` ; `11399: // C0002), and its dirty-page limits would undo the once-a-second sync's bound` ; `11627: // leaves clips split (the NVMe campaign does, for its A/B).` |
| core | src/audio/AudioRecordingSession.cpp | NAME | 3 | `210: // a 30 s and a 3 min take (2026-10-26); the writer thread already keeps disk st` ; `590: // (2026-10-26/27) because each end stamp can be a period off.` ; `752: // otherwise kept audio_capture.raw at 0 bytes (C0011, 2026-10-26). It is` |
| core | src/camera/ModeLadder.hpp | CIN | 3 | `26: CdngLog cdngLog = CdngLog::Off;  // CineMate Log for this resolution: off, or on` ; `34: // The depth this resolution stores through CineMate Log, 0 = linear.` ; `122: // log = CineMate Log on (one step down); log10 and log8 are old spellings that ` |
| core | src/hardware/GpioInput.cpp | CIN | 3 | `623: // Like Cinemate: a button that already reads pressed at start is wired the othe` ; `662: // Like Cinemate: the position a switch is in when Core starts is applied once.` ; `735: // Edge events first, so the thread sleeps until a pin changes, the way Cinemate` |
| core | src/hardware/HardwareConfigStore.hpp | HIST | 3 | `3: // WebUI and core.py saves, and the IMU code. It serialises the writers, refuses` ; `30: std::string code;           // refusals: locked, being_written, stale, conflict,` ; `88: // The net for "mv" instead of "cp", an old touch UI binary or a test: the file ` |
| core | src/playback/DecodeSlots.hpp | ID | 3 | `3: // Apertar playback, design sketch v2 (not in any repository).` ; `4: // Decode slots that own their buffers (critic M5).` ; `9: // (critic A.3). Here the buffers belong to the slot; a request borrows a slot w` |
| core | src/playback/PlaybackFrames.cpp | ID | 3 | `1: // Apertar playback, T48: see PlaybackFrames.hpp.` ; `37: // A byte-limited LRU: thumbnails (w <= 480) 8 MB, play and paused pictures 24 M` ; `173: // those black itself, R2; thumbnails and the touch screen's rule hold the last ` |
| core | src/playback/PlaybackHold.hpp | ID | 3 | `3: // Apertar playback, design sketch v2 (not in any repository).` ; `5: // any lock (critic M8).` ; `23: // after the hold ends. A clear-on-next-request flag (the critic's sketch) would` |
| core | src/util/MediaTune.hpp | NAME | 3 | `5: // test night needs no systemd drop-in. Pure std, no Linux-only includes, so too` ; `9: // /run/apertar-media/media-tune.override.conf (tmpfs: gone at reboot, for test ` ; `11: // user's last session ends, 2026-11-03). Per key the first hit` |
| d283 | imx283.c | CIN | 3 | `262: * Modes 4 and 5 also produce frames shorter than CineMate's 720-line` ; `770: *  - Verified (cb925e5) on a live ISP preview frame pulled off cinepi-raw's` ; `2518: * CM5 with kernel 6.12.93, Comm: cinepi-raw). The ACTIVE crop` |
| d585 | APERTAR.md | NAME | 3 | `23: git clone https://github.com/Tiramisioux/imx585-v4l2-driver.git ~/drivers/imx585` ; `166: - `README.md`: a hardware pass on 2026-08-31 (CM5, kernel 6.12.93, colour` ; `169: - Commit `fdd767a`: hardware takes on 2026-09-21 showing that 1x1 RAW16 crops` |
| d585 | README.md | NAME | 3 | `37: git clone -b cinemate-port https://github.com/Tiramisioux/imx585-v4l2-driver.git` ; `206: CineMate ships. Confirmed on the colour rig on 2026-08-31: it clears the` ; `250: Verified, 2026-08-31: `link-frequency=891000000` (1782 Mbps/lane) with` |
| ui | qml/CameraPage.qml | ID | 3 | `518: // T33: the lists come from UI.conf (Core's set_value_steps); empty = these buil` ; `858: // Request 24: a list works on any sensor. Every value stays; values above the m` ; `4339: // Recording frame (request 25): a red border at the screen's edges during a cam` |
| core | README.md | ID | 2 | `329: On exFAT every new file walks all entries of its folder under the filesystem's l` ; `341: Environment variables of the Core service (a systemd drop-in with `Environment=`` |
| core | README.md | CIN | 2 | `346: / `APERTAR_DNG_WRITE_ROWS=N` / 64 / Rows per `write()` when the payload goes thr` ; `354: / `APERTAR_RT=1` / off / The start script runs the whole Core process under `SCH` |
| core | config/apertar-core-capture-priority.conf | CIN | 2 | `5: # or APERTAR_RT=1 (the start script runs the whole process under chrt -f 70, as ` ; `6: # cinepi-raw) in the unit's environment. Without either the limit is unused.` |
| core | include/apertar/core/Types.hpp | CIN | 2 | `59: // CineMate Log: store the sensor data at a lower depth through a log curve. Run` ; `355: // CineMate Log works in cDNG and Lossy DNG; H.264, ProRes and (for now) MLV can` |
| core | src/camera/FpsCeiling.hpp | HIST | 2 | `13: // table: Core's hard-coded ceiling. tableOnly: APERTAR_FPS_LIMIT=table, the old` ; `41: // min(override, modeMax) when APERTAR_LOSSLESS_FPS_LIMIT is set. 30 restores th` |
| core | src/camera/Imx283Modes.hpp | CIN | 2 | `1: // The IMX283 sensor modes Core offers: the 57 non-experimental modes of the cin` ; `2: // (Tiramisioux/imx283-v4l2-driver, branch cinemate-port, experimental_modes=0).` |
| core | src/camera/Imx585Modes.hpp | CIN | 2 | `3: // The IMX585 modes the cinemate-port driver advertises, per class, and the size` ; `16: // as in cinemate: find() and nearest() do not see them.` |
| core | src/cdng/CdngEncoder.hpp | ID | 2 | `15: // (the kernel reclaims them). See the kb, working/dng-chain: after a write the ` ; `44: // Speed ramping (T31): wall clock the FreeRun timecode counts from (first` |
| core | src/hardware/BootConfigText.hpp | HIST | 2 | `657: size_t after = 0;         // for an added line: the old line it follows (0 = the` ; `1187: size_t before = head;             // 1-based number of the old line the run foll` |
| core | src/hardware/ButtonGesture.hpp | CIN | 2 | `2: // Press, single, double and triple click, and hold for one button, the way Cine` ; `3: // (cinemate src/module/gpio_input.py): Press fires on every press, at once. Rel` |
| core | src/hardware/HardwareConfigText.hpp | NAME | 2 | `856: // GPIO lines: one owner each.` ; `1082: // The commands the I2C card shows for Patrik to run. They name the overlays, no` |
| core | src/hardware/HardwareConfigText.hpp | HIST | 2 | `1103: // A text-mode save whose base is stale. If base -> mine changes only key values` ; `1105: // current file like easy mode. nullopt: refuse as before.` |
| core | src/playback/PlaybackFrames.hpp | ID | 2 | `3: // Apertar playback, T48: one frame of a cDNG clip as a JPEG (design §4.4, §4.7)` ; `4: // the host test is working/tools/playback/frames_test.cpp.` |
| core | src/playback/RawRender.hpp | ID | 2 | `3: // Apertar playback, design sketch (not in any repository).` ; `9: // Named copy (KB rule M5): change one, change the other; playback_bench checks ` |
| core | src/web/WebControlPage.cpp | NAME | 2 | `17305: // One dropdown entry: [value, text, owner]. Held by another control: greyed, wi` ; `17345: // A pin dropdown: dark, unlike the other Controls dropdowns. options: [[value, ` |
| d283 | EXPERIMENTAL_CROPS.md | HIST | 2 | `11: >   crops" no longer exist. Each parent mode now carries a centred` ; `33: **Historical: these 18 crops no longer exist.** None of these sizes is offered` |
| d283 | EXPERIMENTAL_CROPS.md | NAME | 2 | `24: >   it was around 2026-09-20.` ; `134: `experimental-crop-modes` planning tree, fetched 2026-09-20). Summary: the verti` |
| d585 | README.md | HIST | 2 | `234: the old `HMAX_table_4lane_4K` entry of 440, which is too aggressive for` ; `254: blend default, not the D-PHY — `EXP_BK` menu 5 fixes them, and that is a` |
| d585 | imx585.c | HIST | 2 | `795: *       crops that used to follow it here -- all twelve ratios plus the` ; `2067: * The aspect-ratio family's 2x2-binned RAW16 crops that used to` |
| d585 | imx585.c | CIN | 2 | `4460: * CineMate's dual-imx585 rigs two probes are not mutually exclusive in` ; `4668: * arrays shared by every imx585 instance the module binds. CineMate` |
| ui | qml/CameraPage.qml | NAME | 2 | `544: // pixel numbers: "3840x2160 · 16-bit · Clear HDR" (Patrik, 2026-10-28).` ; `710: // third too long (HDMI 50 min, Core 37 min, 2026-10-27). The IMX477 frame-rate` |
| ui | qml/ClipNameCard.qml | NAME | 2 | `13: // Asks the owner to open the text keyboard; `current` is the existing text when` ; `213: // Called by the owner with the text the user typed.` |
| ui | qml/TopDropdownStat.qml | ID | 2 | `11: property bool valueItalic: false     // set by the camera, not the operator (T33` ; `100: // mode cannot take it, green when the camera added it (T33).` |
| ui | src/ApertarControlBridge.cpp | ID | 2 | `275: // A ramp step in a camera take (T31): Core applies the shutter policy (angle or` ; `2666: // Core's flat JSON delivers scalars as strings (KB trap 7); accept numbers too.` |
| ui | src/ApertarControlBridge.hpp | ID | 2 | `82: // T45: what Core's validator finds in ~/apertar-hardware.conf (get_state, and t` ; `435: bool m_fpsSpeedRamp = false; // Core's fps_speed_ramp (T31): FPS may change duri` |
| core | config/apertar-boot-config.sudoers | HIST | 1 | `3: # The rule pins the path and no arguments (""); the script fixes the destination` |
| core | config/apertar-media-tune.conf | NAME | 1 | `8: #      it lives in RAM and is gone at reboot, for test nights)` |
| core | scripts/apertar-boot-config | HIST | 1 | `13: # over it, so a power cut leaves the old file or the new one, never half of one.` |
| core | scripts/apertar-boot-config | NAME | 1 | `60: # /boot/firmware is FAT: owner and mode come from the mount, so these may do not` |
| core | scripts/apertar-media-tune | ID | 1 | `11: # table; T29 measures them on this rig before they are trusted:` |
| core | scripts/start-apertar-core.sh | CIN | 1 | `22: # cinemate starts cinepi-raw (src/module/cinepi_multi.py run()). The unit needs ` |
| core | scripts/start-apertar-core.sh | HIST | 1 | `23: # (config/apertar-core-capture-priority.conf). When chrt is refused Core starts ` |
| core | scripts/start-apertar-core.sh | ID | 1 | `24: # Off by default: the A/B in the kb (working/dng-chain) decides whether it stays` |
| core | src/ApertarCoreApp.hpp | CIN | 1 | `116: // Storage pre-roll (CineMate's warm-up): requestStoragePreroll only requests; t` |
| core | src/ApertarCoreApp.hpp | HIST | 1 | `174: std::atomic<size_t> controlsErrors_{0};        // T37: what the validator found ` |
| core | src/audio/AudioRecordingSession.cpp | HIST | 1 | `211: // off the capture, so the old ring is the default again.` |
| core | src/audio/AudioRecordingSession.cpp | ID | 1 | `382: // A ramping take (T31) has no single nominal period: end the WAV at the last` |
| core | src/audio/AudioRecordingSession.hpp | CIN | 1 | `75: // writer thread drains them into rawStream_ (Cinemate ffb61fd: an exFAT` |
| core | src/audio/TimestampedAudioCapture.cpp | CIN | 1 | `197: // (Cinemate 5021ba3: hundreds of ms under 4K writes), the period keeps the` |
| core | src/camera/CameraController.hpp | CIN | 1 | `132: // True when CineMate Log is on and the CURRENT configured raw stream can really` |
| core | src/camera/FramePhaseLock.hpp | CIN | 1 | `18: // as Cinemate's libcamera does), so the integer requests alternate between two` |
| core | src/camera/Imx283Modes.hpp | NAME | 1 | `2: // (Tiramisioux/imx283-v4l2-driver, branch cinemate-port, experimental_modes=0).` |
| core | src/camera/ModeLadder.hpp | ID | 1 | `1: // Mode ladder (T34): pure logic, no libcamera, so it compiles and is tested on ` |
| core | src/cdng/CdngEncoder.cpp | HIST | 1 | `132: // APERTAR_DNG_PAYLOAD_COPY=1 keeps the old path for every frame: rows copied in` |
| core | src/cdng/CdngEncoder.cpp | CIN | 1 | `1987: // Rows that need no repacking are written from the frame itself (cinepi-raw's o` |
| core | src/cdng/CdngEncoder.hpp | NAME | 1 | `14: // after the file's fsync, when the pages are clean; "writer" right after the wr` |
| core | src/cdng/CdngEncoder.hpp | HIST | 1 | `14: // after the file's fsync, when the pages are clean; "writer" right after the wr` |
| core | src/cdng/FramePath.hpp | HIST | 1 | `6: // root, as always. N > 0: frame number f goes to <clip>/part_<k>/<the unchanged` |
| core | src/cdng/FramePath.hpp | ID | 1 | `11: // working/drop-frames/nvme-campaign/probe-exfat-dir.md).` |
| core | src/cdng/FramePath.hpp | NAME | 1 | `11: // working/drop-frames/nvme-campaign/probe-exfat-dir.md).` |
| core | src/hardware/ActionCatalog.hpp | HIST | 1 | `25: std::string_view aliases; // comma separated, every spelling the old normalizers` |
| core | src/hardware/ControlsModel.hpp | CIN | 1 | `32: // The clicks and hold a GPIO button can carry next to Press (counted like Cinem` |
| core | src/hardware/GpioInput.hpp | CIN | 1 | `37: std::string single;       // dN_single, dN_double, dN_triple, dN_hold: counted l` |
| core | src/hardware/HardwareConfigStore.cpp | HIST | 1 | `62: // The first two lines of the text the touch UI used to write when the file was ` |
| core | src/hardware/HardwareConfigStore.hpp | NAME | 1 | `44: std::string savedAt;    // "2026-10-30 00:25", "" for the adopted one` |
| core | src/hardware/HardwareConfigText.hpp | ID | 1 | `116: // Gesture suffixes (T44): written by Core as <control>_hold / <control>_double.` |
| core | src/hardware/NeoRotary4Input.hpp | CIN | 1 | `34: std::string single;       // encoderN_single, _double, _triple, _hold: the push ` |
| core | src/hardware/Pcf8574Input.cpp | CIN | 1 | `425: // Like the GPIO buttons (Cinemate): a mapped pin that reads pressed at start is` |
| core | src/hardware/Pcf8574Input.hpp | CIN | 1 | `39: // pinN_single, _double, _triple, _hold, in that order: counted like Cinemate (B` |
| core | src/ipc/ControlServer.cpp | HIST | 1 | `15: // One command line. A set_controls text is the whole file; 64 KiB used to drop ` |
| core | src/lossydng/LossyDngEncoder.cpp | CIN | 1 | `51: // CineMate Log in place of the square root: the same working domain (0..kWorkin` |
| core | src/lossydng/LossyDngEncoder.hpp | CIN | 1 | `24: // CineMate Log for this take: replaces the square-root companding. Both pointer` |
| core | src/playback/ClipFrames.hpp | CIN | 1 | `11: // and Cinemate use the position (playbackcontroller.cpp:849-851; cinemate playb` |
| core | src/playback/DecodeSlots.hpp | CIN | 1 | `10: // answers 503 when none is free (Cinemate's "refuse rather than queue", playbac` |
| core | src/playback/DngTags.hpp | HIST | 1 | `321: // (v1 checked it after samples.resize(), critic M9: 512 MB for a 16384 x 16384 ` |
| core | src/util/BufferBudget.hpp | CIN | 1 | `7: // system's own needs) follow cinepi-raw's DNG encoder (cinepi/dng_encoder.cpp: ` |
| core | src/util/MediaFault.hpp | CIN | 1 | `13: // problem is a configuration error. Logic follows Cinemate's yank errno set` |
| core | src/util/MediaIntent.hpp | CIN | 1 | `14: // second (Cinemate f01b6cd). Core touches` |
| core | src/util/MediaProbe.hpp | ID | 1 | `179: // keep "answering" (critic Y1). Two device-level facts settle it the way` |
| core | src/util/MediaProfile.hpp | NAME | 1 | `141: // 16-bit 4K25 on the CFE NVMe (C0106, 2026-10-26); 4/12 held 10 min (C0101).` |
| core | tools/black_level_test.cpp | HIST | 1 | `2: // container (MLV used to scale the black only for 8 and 10 bit, so 16-bit Clear` |
| core | tools/black_level_test.cpp | CIN | 1 | `35: // Values already on the container scale (CCMP codes12 table, CineMate Log) are ` |
| core | tools/boot_config_test.cpp | NAME | 1 | `18: // The dev Pi's /boot/firmware/config.txt on 2026-11-01 (Apertar-Beta 1.6.0, DPI` |
| core | tools/clip_name_test.cpp | NAME | 1 | `64: // The owner's examples.` |
| core | tools/gen_log_curve.py | CIN | 1 | `2: """CineMate Log curve in plain Python (stdlib only): prints the per-pair constan` |
| d283 | APERTAR.md | HIST | 1 | `23: - An unsupported media-bus code no longer reads past the end of the code table.` |
| d283 | APERTAR.md | NAME | 1 | `31: git clone https://github.com/Tiramisioux/imx283-v4l2-driver.git ~/drivers/imx283` |
| d283 | README.md | NAME | 1 | `32: git clone -b cinemate-port https://github.com/Tiramisioux/imx283-v4l2-driver.git` |
| d283 | README.md | CIN | 1 | `32: git clone -b cinemate-port https://github.com/Tiramisioux/imx283-v4l2-driver.git` |
| d283 | imx283-overlay.dts | HIST | 1 | `115: * setting, even though the driver has always taken both.` |
| d585 | tools/clearhdr-gate/README.md | NAME | 1 | `9: WP-585-8 (2026-09-21) settled the RAW16 half on hardware: every windowed 2x2` |
| d585 | tools/clearhdr-gate/pedestal_check.py | ID | 1 | `2: """WP-585-9 hardware gate: does a Clear HDR take hold a picture or the OB pedest` |
| d585 | tools/clearhdr-gate/pedestal_check.py | CIN | 1 | `88: offset, nbytes = offsets[0], sum(counts)   # cinepi-raw writes one strip; tolera` |
| ui | qml/CameraPage.qml | HIST | 1 | `711: // tables treat anything above 10 as their 12-bit table, as before.` |
| ui | qml/ClipNamePill.qml | NAME | 1 | `5: // pill-local mouse coordinates, the owner moves the ghost and decides what a dr` |
| ui | qml/ControlsWarning.qml | ID | 1 | `3: // T45: a chip on the camera page when Core's check of ~/apertar-hardware.conf f` |
| ui | qml/ExternalMonitorWindow.qml | ID | 1 | `1427: // Recording frame (request 25): a red border at the monitor's edges during a ta` |
| ui | qml/SettingsPage.qml | ID | 1 | `6455: // T45: read-only. What Core's check of the hardware file says; buttons, knobs a` |
| ui | src/ApertarControlBridge.hpp | CIN | 1 | `424: // CineMate Log (Core: cdng_log_bits, cdng_log_available, cdng_log_applied); act` |
| ui | src/ApertarPreviewSocketClient.cpp | HIST | 1 | `27: // runs, 0 = keep the last frame until the take ends. Unset = every frame, as be` |
| ui | src/CfeAutomounter.cpp | HIST | 1 | `727: // until its PCIe device is removed and rescanned, and the stale mount would` |
| ui | src/SettingsBridge.cpp | ID | 1 | `1767: // T33: read only here; Core's set_value_steps writes these keys and this bridge` |
| ui | src/SettingsBridge.hpp | ID | 1 | `95: // T33: the value lists Core's set_value_steps writes to UI.conf (empty = the bu` |
Not in the table (zero comment hits but still on the list):

| File | Kind | Detail |
| --- | --- | --- |
| `src/web/WebControlPage.cpp:4912` | CIN in a string | `data-search="log cinemate encode bit depth"`: hidden search keywords. Drop "cinemate". |
| `src/camera/CameraController.cpp:3985, 4008`, `src/cdng/LogCurve.hpp:48`, `src/camera/CameraController.cpp:11350`, `src/camera/ModeLadder.hpp:26` | CIN in strings that reach the journal and clip metadata | "ApertarCore CineMate Log: ..." and `describe()` = "CineMate Log 16->12 ...". The WebUI/UI label of the same feature is just "Log" (`WebControlPage.cpp:4915`). Rename to "Log" in all five (confirmed). |
| `src/ApertarCoreApp.cpp:5052, 5068` | CIN in the written `camera_settings.conf` template | "(CineMate style)", "(CineMate's warm-up)". The operator reads these in the file. Rewrite. |
| `src/web/WebControlPage.cpp:3485` | CIN in CSS comment | "like CineMate's web GUI". Rewrite. |
| `README.md:339, 356, 329` | NAME in README | "test night", "NVMe campaign's A/B and collect step", "(measured 2026-11-04, probable)". |
| `config/apertar-media-tune.conf:8` | "test nights" | See replacement 55. |
| banners | decoration | 40 added banner lines (`// ---- X ----`, `/* ==== */`). Upstream Core `src/*.cpp` has 0 outside prores/lossydng vendor-like code. Upstream `CameraPage.qml` has 19, so banners are accepted in QML only. Port: `BootConfigText.hpp` 8, `tools/boot_config_test.cpp` 8, `WebControlPage.cpp` 7, `HardwareConfigText.hpp` 4, `CameraController.cpp` 4 (:1108, :9742, :10823, :12039), `ApertarCoreApp.cpp` 4, `ClipProbe.hpp` 3. Remove in Core; QML ones may stay. |
| 12 header banner lines | tutorial residue | `ClipProbe.hpp:3`, `ClipFrames.hpp:3`, `DecodeSlots.hpp:3`, `DngFrameReader.hpp:3`, `DngTags.hpp:3`, `PlaybackHold.hpp:3`, `RawRender.hpp:3`, `PlaybackFrames.hpp:3-4`: "design sketch v2 (not in any repository)", "reference for the tutorial; not in any repository until you type it", "the host test is working/tools/playback/frames_test.cpp" (a path that is not in the repo). |

## B. Build log and unused code

`/home/user/build/core-port-build.log` (no libcamera) and `core-port-lc-build.log` (libcamera): confirmed 5 warnings, none from port code.

| Warning | Verdict |
| --- | --- |
| `ApertarCoreApp.cpp:4742 convertPlanarYuv420ToRgb` unused | Upstream function (`core-upstream ApertarCoreApp.cpp:4069`), used only under `#if APERTARCORE_HAS_TURBOJPEG` (:4780). Build-config artefact. |
| `CameraController.cpp:1235 allocatePhotoBasePath` unused | Upstream function (`core-upstream CameraController.cpp:924`), used only in the libcamera build (:7969). Not the port. |
| `CameraController.cpp:7763 mediumGone`, `:7916 basePathOverride` unused params | Used inside `#if APERTARCORE_HAS_LIBCAMERA`. Build-config artefact. |
| `StandbyPowerButtonInput.cpp:26 write()` result | Upstream file, unchanged by the port. |

Real leftover found by reading: `src/util/MediaProfile.hpp:133` `bool directIo = false; // for T24's direct I/O, which this fork does not carry; unused`. A field that says it is unused. Remove field and its comment (replacement 48). Test hook in a production path: none beyond the existing `simulateCamera_` (upstream). `APERTAR_BOOT_CONFIG` (`ApertarCoreApp.cpp:3504`, "a dev machine, a test") is an env override for a path; it belongs to the knobs sweep.

## C. Per-kind notes

* **(a) IDs by area.** Core `ApertarCoreApp.cpp` 52, `WebControlPage.cpp` 32, `CameraController.cpp` 27, `Types.hpp` 9 (T34 on nine lines :181-189), `ClipProbe.hpp` 6, `DngTags.hpp` 7, `DngFrameReader.hpp` 5, `ClipFrames.hpp` 5. imx585.c: 53 lines with "WP-585-N", plus `tools/clearhdr-gate/README.md` 8. The same WP ids are the vocabulary of `APERTAR.md`. The ids have no meaning without the KB.
* **(a) names and dates by area.** `CameraController.cpp` 13 (":3025 Patrik's rule (2026-10-28, after the temp build)", ":3428 (User, 2026-11-03)", ":3099 (temp 753f181, 2026-10-27 ... C0013 peak 2/24)", ":4357 (C0005, 2026-10-26)", ":4714 (C0001, 2026-10-26)", ":4734 (C0010 ...)"), `AudioRecordingSession.cpp` 3 (:210, :590, :752), `MediaProfile.hpp:141` (C0106, C0101), `ClipProbe.hpp:8` ("On Patrik's exFAT card"), `HardwareConfigText.hpp:1082` ("for Patrik to run"), `qml/CameraPage.qml:544, :710`, `imx283.c` 12, `imx585.c` 8.
* **(b) history.** Typical forms: "as before", "as always", "the old model assumed", "used to drop the client", "v1 checked it after samples.resize()", "the first two lines of the text the touch UI used to write", "HISTORY, kept so nobody repeats it" (`imx283.c:780`), "Historical: these 18 crops no longer exist" (`EXPERIMENTAL_CROPS.md:33`). Bug-story comments with measurements: `AudioRecordingSession.cpp:209-211`, `CameraController.cpp:4356, 4713, 4733, 9065`.
* **Pointers to the KB or other private paths** (a separate subset of ID, 20 lines): `ApertarCoreApp.cpp:92, 10897`, `CameraController.cpp:3430, 4888, 9112`, `CdngEncoder.hpp:15`, `FramePath.hpp:11`, `ClipProbe.hpp`, `scripts/start-apertar-core.sh:24`, `ui src/ApertarControlBridge.cpp:2666` ("KB trap 7"). The original developer has no `apertar-kb`.
* **Commit hashes of another project in comments:** `Cinemate f01b6cd` (`ApertarCoreApp.cpp:4387`, `MediaIntent.hpp:14`), `ffb61fd`, `5021ba3`, `58fc7c2`, `888093c`, `ff59dd8`, `c8f06c9`. Useless to the reader. Remove.

## D. Comment density (comment lines per 1000 lines; full-line comments plus trailing `//`)

Counter: lines starting `//`, `/*`, `#` (not preprocessor) or inside `/* */`, plus trailing `// ` comments. Read at `cinemate-port` and `upstream-1.6.0`. Confirmed (script run in this sweep).

| File (kind) | Port | Upstream 1.6.0 | Ratio |
| --- | --- | --- | --- |
| `src/camera/CameraController.cpp` (big .cpp) | 54 (12 932 lines) | 9 (8 835 lines) | 6x |
| `src/ApertarCoreApp.cpp` (big .cpp) | 28 (15 084) | 5 (11 026) | 6x |
| `src/web/WebControlPage.cpp` (WebUI string) | 21 (20 964) | 0 (11 619; 3 comment lines) | new habit |
| `src/camera/CameraController.hpp` (header) | 185 (254) | 7 (136) | 26x |
| `src/hardware/GpioInput.cpp` (driver class) | 21 (863) | 3 (747) | 7x |
| `qml/CameraPage.qml` | 15 (4 350) | 8 (4 161) | 2x |
| `qml/ExternalMonitorWindow.qml` | 7 (1 437) | 0 (1 348) | new |
| `src/ApertarControlBridge.cpp` (UI) | 10 (2 863) | 3 (2 461) | 3x |
| `src/cdng/CdngEncoder.cpp` | 22 (2 036) | 14 (1 902) | 1.6x |
| `src/SettingsBridge.cpp`, `qml/SettingsPage.qml` | 2 / 0 | 2 / 0 | equal |
| All 65 handwritten upstream Core src files (without prores, lossydng, mlv) | - | 7 | baseline |
| The 38 files the port added under `src/` (headers and cpp) | 117 | - | 16x of upstream mean |
| Highest new files | `PlaybackHold.hpp` 359, `PlaybackFrames.hpp` 341, `HardwareConfigStore.hpp` 326, `GpioChipInfo.hpp` 306, `FramePhaseLock.hpp` 289, `ClipFrames.hpp` 254 | | |
| imx585.c (driver) | 198 | 133 baseline (`origin/apertar`) | 1.5x |
| imx283.c (driver) | 333 | 109 baseline (`origin/master`) | 3x |

Reading: upstream Core comments about one line in 140. The port writes one in 9 to 20 in the big files and one in 8 in new files. Upstream's comments are one short line above a function or a field; the port's are 3 to 7 line paragraphs with measurements, dates and test-run ids. Rewriting to upstream shape would remove roughly 1 500 comment lines in Core.

## E. Operator-facing strings

Sampled: 57 WebUI card hints (`settings-card-copy`, `settings-hint`) in the port against 45 upstream; 345 `errorReply` texts against 266.

| Measure | Upstream 1.6.0 | Port |
| --- | --- | --- |
| mean hint length | 60 chars (max 140, none over 160) | 80 chars (max 305, 5 over 160) |
| mean `errorReply` length | 33 chars | 33 chars (the 79 new ones: 34) |
| non-ASCII in WebUI string | `•` `°` | adds `·` (32), `×` (16), `…` (15), `→` (6) |
| tone | imperative, one sentence | same, plus 5 paragraphs |

Longest hints to cut to two sentences (confirmed, `WebControlPage.cpp`): the boot-config card (305 chars, "What the Pi loads at power-on ... A change takes effect after a re..."), the clip-name card (247), FPS ramp Stay/Return (193), Hardware devices card (176), Controls card (162). Error replies follow the upstream shape ("X needs ..."), with one exception class: refusals that name a UI path ("Settings > Config > Hardware", `scan_i2c`), which upstream does not do. The refusal texts have no internal ids.

String leaks: the five "CineMate Log" strings above, the `camera_settings.conf` template comments (5052, 5068), `README.md`. `qml/SettingsPage.qml:5652` and `WebControlPage.cpp:5771` pre-roll hint text is clean.

## F. The replacement text (60 worst cases)

Written the way the original developer writes: one short line, what the code does now, no ids, no dates, no names. Line numbers are at `cinemate-port` (Core `01f170c`, UI `7ea9afc`, drivers as in the brief). "-" = delete the comment line. Where only a tag is removed, the rest of the sentence stays and is shown in full.

### Core, `include/apertar/core/Types.hpp`

| # | Where | Replace with |
| --- | --- | --- |
| 1 | :141-142 | `// Speed ramp: FPS may change during a cDNG/MLV take. Frames are then numbered by count and the clip keeps the FPS it started with as its timeline rate.` |
| 2 | :181-189 (nine lines) | Drop `Runtime (T34): ` from each. Example :182 `bool ladderActive = false; // the mode ladder picks the sensor mode from the FPS` ; :189 `std::string ladderText; // the running line, e.g. "Resolution 1 · 3840×2160 · ClearHDR16 · ≤25 · Uncompressed"` |

### Core, `src/ApertarCoreApp.cpp`

| # | Line | Replace with |
| --- | --- | --- |
| 3 | 1272-1273 | `// A list works on any sensor. Values up to the mode's ceiling are selectable; the ceiling is added when a value lies above it (cap 0 = none).` |
| 4 | 1308 | `// Free stepping: move by the increment between the list's ends instead of through the list.` |
| 5 | 1929-1930 | `// The operator's value lists (empty = built-in list), free stepping on the hardware controls, and flicker-free shutter angles for the local mains frequency.` |
| 6 | 1961 | `// Value-list fields of the state's ui object (also the set_value_steps reply): each list as set, or the built-in list, with free stepping and flicker-free settings.` |
| 7 | 5584-5585 | `// The raw frame follows rawBitDepth, 16 included (Clear HDR).` (history sentence removed) |
| 8 | 6335 | `// Playback state shared by the routes, the media watcher and handleCommand. File scope, so the header does not pull in the readers.` |
| 9 | 6378 | `// What the clip's own files say (a cDNG folder with a readable first frame).` |
| 10 | 6390 | `std::string timecodeStart; // recorded start timecode of the first frame` |
| 11 | 6454 | `// A delete in progress is visible to handleCommand, which refuses a take until it is done.` |
| 12 | 6764 | `// The format of a WAV (one RIFF parser for the length and for the SOUND row).` |
| 13 | 7208, 7336 | `if (stop && stop()) // a take is starting; give the card back within one chunk` (7336: `...; stop the archive within one chunk`) |
| 14 | 7219 | `// Bytes [first, last] of a file, read through our own descriptor (O_CLOEXEC, so a forked zip or sudo helper never holds it), 64 KiB at a time. ...` (rest unchanged) |
| 15 | 7354 | `// GET /api/media/clip: one clip's facts, in the touch UI's words.` |
| 16 | 7442 | `// A cDNG take answers from its own files first. The cache is keyed on the folder's time, so an unchanged take costs one stat. In a hold only what the cache already knows is listed.` |
| 17 | 8032 | `// Publish [storage] clip_merge before the first scan: the atomic starts as true, and the hardware-file block below runs after this.` |
| 18 | 8117-8118 | `// what the drivers below start from` ; `// Listen` |
| 19 | 8136 | `// Validate the hardware file once, say what it holds, and pin the version Core found. Nothing is changed.` |
| 20 | 9318 | `// for a take that cannot reach a card.` |
| 21 | 10482 | `// Auto sits below the first value of the list, wherever auto ISO runs: not in Clear HDR (lossless on the IMX585 keeps auto, under its cap).` |
| 22 | 10897 | `// deletes already request theirs; repeated requests coalesce.` |
| 23 | 10926-10927 | `// Only now the profile and the root helper: a sudo round-trip must not delay the abort above.` |
| 24 | 11339 | `// May playback read the card now? One rule for every playback route. The yield window is what a command that starts a take opens before it touches the camera.` |
| 25 | 11376-11377 | `// One second of 16-bit 4K at 25 fps is ~415 MB; the floor is a last line, not a time-left estimate.` |
| 26 | 11398-11400 | `// Opt-in (APERTAR_MEDIA_TUNE=1): its dirty-page limits would undo the once-a-second sync's bound on what a pulled card loses.` |
| 27 | 12125 | `// The tally LED and the trigger output on the Hardware card: their settings, whether Core drives them, and a Test button (test_output).` |
| 28 | 12168 | `// The driver group a hardware section belongs to. A group stops as a whole before any of it starts again: its members share GPIO lines or a chip.` |
| 29 | 12459 | `// The saved versions, newest first; name= returns one version's text.` |
| 30 | 14529 | `// A preset that names a mode must be the one the ladder picks for its FPS; one that names none follows the ladder.` |
| 31 | 5052, 5068 (template text written to the file) | `# ... sized from the free memory at the start of a take.` and `# Storage pre-roll: a short test take at the sensor's maximum fps through the real write path, deleted at once.` |

### Core, `src/camera/CameraController.cpp`

| # | Line | Replace with |
| --- | --- | --- |
| 32 | 403 | `// The mode ladder lives beside camera_settings.conf (same XDG rule), one ladder per camera.` |
| 33 | 3025-3027 | `// Clear HDR records uncompressed cDNG and SDR lossless, however the mode is switched: lossless overflows the write queue in Clear HDR 16-bit. Called wherever clearHdr changes, with the previous value.` |
| 34 | 3034-3036 | `// A ladder resolution names its own raw format: uncompressed or lossless cDNG, or lossy DNG at 3:1 or 5:1. Unnamed means the default: Clear HDR uncompressed, SDR lossless. MLV has no compression to choose.` |
| 35 | 3098-3099 | `// Lossless JPEG slows down as noise grows, so ISO is capped at 1600 in Clear HDR 16-bit lossless.` (check the cap's scope when editing; the original text says 1600 for 12-bit lossless 4K25) |
| 36 | 3154 | `// ... below the cap, so auto ISO stays. Other sensors are unchecked.` |
| 37 | 3428-3430 | `// No cap here: the driver's maximum applies (4K 30, the height crops up to 42). At 30 in 4K the ISP back end is the limit and frames are lost under load.` |
| 38 | 4356-4357 | `// ... here waited for every page in flight and stalled the writers.` |
| 39 | 4713-4714 | `// ... entries instead of a second's worth of frames in one burst. APERTAR_DNG_WRITEBACK=0 turns it off.` |
| 40 | 4733-4734 | `// ... puts on the card: the folder fsync alone leaves file names at 0 bytes after a pull.` |
| 41 | 4888 | `// ... (hasCapacityForFrame), and a 16.6 MB zero-fill under it holds that thread up.` |
| 42 | 5206 | `// The template decides the name (default {format}_{date}_{clip} = cDNG_26-10-28_C0001);` |
| 43 | 9065-9068 | `// ... 5-8 % line-length jumps and one-frame exposure steps. A range takes libcamera's default blanking: HMAX stays at the mode minimum and the frame rounds down to whole lines, so the servo dithers adjacent line counts.` |
| 44 | 9933, 10418 | `// Experimental: Rubber Band writes <clip>_stretched.wav, ...` and `// Experimental audio stretch: queued by writeFpsRampLog(), ...` |
| 45 | 10729 | `// A ramp step is take-scoped: the UI hears it, the settings file does not.` |
| 46 | 10736, 10748 | Drop "Cinemate's shutter_a_sync_mode:" -> `// Shutter sync mode: 0 keeps the angle (the rescale below), 1 keeps ...` |

### Core, other files

| # | Where | Replace with |
| --- | --- | --- |
| 47 | `util/MediaProfile.hpp:24-25` | `// which reads two sysfs files; the tables are starting points that need measuring on the rig.` |
| 48 | `util/MediaProfile.hpp:133` | delete the `directIo` field and its comment |
| 49 | `util/MediaProfile.hpp:140-141` | `// exFAT: Core's pre-profile values.` |
| 50 | `playback/ClipProbe.hpp:3-11` | `// What Core knows about one cDNG clip folder, from the files themselves: its own FPS, frame numbers and holes, span duration, recorded timecode, format text, shot date. The texts follow the touch UI's rules so both screens say one thing.` and `// ClipFactsCache: an unchanged folder costs one stat (its modification time). A readdir of 100 000 entries costs seconds, so entries are not counted. A changed folder is probed outside the lock and swapped in.` |
| 51 | `playback/DngTags.hpp:3-10`, `ClipFrames.hpp:3-4`, `DecodeSlots.hpp:3`, `DngFrameReader.hpp:3`, `PlaybackHold.hpp:3`, `RawRender.hpp:3`, `PlaybackFrames.hpp:3-4` | delete the "design sketch v2 (not in any repository)" / "critic" / "T47" / "T48" lines; keep one line each, e.g. `// The tags of a DNG written by CdngEncoder, read without Qt, libtiff or liblj92.` ; `// The frame list of one clip folder, and the map from time to frame.` |
| 52 | `camera/ModeLadder.hpp:1, 319` | `// Mode ladder: pure logic, no libcamera, so it compiles and is tested on any host.` ; file header `"# Apertar mode ladder. Core writes this file; edit it in the WebUI (Settings > Record > Mode Ladder).\n"` |
| 53 | `camera/Imx283Modes.hpp:1-2`, `Imx585Modes.hpp:3, 16` | `// The IMX283 sensor modes Core offers: the 57 non-experimental modes of the driver (experimental_modes=0). Pure, std only; host-tested by tools/imx283_modes_test.cpp.` and `// Modes narrower than minModeWidth() (1280 px; APERTAR_IMX585_MIN_MODE_WIDTH overrides) are hidden: find() and nearest() do not see them.` |
| 54 | `audio/AudioRecordingSession.cpp:209-211` | `// A 1 s ring makes the drift figure swing between takes; the writer thread already keeps disk stalls off the capture, so the old ring is the default.` ; :590 `// ... because each end stamp can be a period off.` ; :752 `// Once a second the raw capture goes to the card with its size, so a pulled card keeps it.` |
| 55 | `scripts/apertar-media-tune:8-11`, `config/apertar-media-tune.conf:8`, `util/MediaTune.hpp:5, 9-11`, `README.md:339, 356` | `# override the recorder's settings.` ; `# Per connection class, starting points to be measured on the rig:` ; `// ... so a change needs no systemd drop-in.` ; `/run/apertar-media/media-tune.override.conf (tmpfs: gone at reboot; ...). Not /dev/shm: logind's RemoveIPC deletes a user's files there when the user's last session ends.` ; README: `so a trial needs no systemd drop-in` ; `The merge worker leaves split clips split (needed for A/B recordings of the split files).` |
| 56 | `util/MediaIntent.hpp:14`, `ApertarCoreApp.cpp:4387`, `AudioRecordingSession.hpp:75`, `TimestampedAudioCapture.cpp:197`, `MediaProbe.hpp:23` | delete the `(Cinemate <hash>)` parenthesis; the reason before it stays |
| 57 | `hardware/HardwareConfigText.hpp:1082` | `// The commands the I2C card shows. They name the overlays, not line numbers (which shift when the file is edited), back up to a timestamped copy, and are safe to run twice.` |
| 58 | `playback/ClipProbe.hpp:8` and `FramePath.hpp:10-11` | `... why: an exFAT create walks every entry of its folder (5 per frame file) under the filesystem lock, so a 30-minute take in one folder pays a create that grows with the take.` (drop the kb path) |
| 59 | `web/WebControlPage.cpp:7576, 12151-12155, 12332, 12706, 10123, 8482` | `// A list works on any sensor. Every value stays; values above the mode's ceiling are greyed out, and the ceiling is added (camera-set, green) when it is not one of them.` ; `// ---- Playback: the Clip Viewer` becomes `// The touch UI's Clip Viewer in the WebUI. Core draws every picture (/api/media/frame); the page keeps the clock. The clock counts frame numbers, so sound and picture stay together on a take with drops, and a missing or 0-byte frame is drawn black.` (drop "(R2)", "sketch's playclock.js (node-tested, 16 checks). Sound is T51."); `// An honest rate while the player cannot keep up (under 95 % of the clip's rate).` ; `// One frame at a time, by number (a number inside a hole shows black).` ; `// Opens on Stills in photo mode (filter only), else Clips; ...` |
| 60 | `web/WebControlPage.cpp:3485`, `4912` | `/* The GPIO and hardware dropdowns ... are white and dark-texted, so they are easy to see. ... */` ; `data-search="log encode bit depth"` |
| 61 | `camera/CameraController.cpp:3985, 4008`, `cdng/LogCurve.hpp:48`, `CameraController.cpp:11350`, `ModeLadder.hpp:26` | `"ApertarCore Log: "`, `"Log " + sourceBits + "->" + ...`, `// Log is one switch for the camera too`, `// Log for this resolution: off, or on (one step below the source depth)` |

### UI (`Apertar-UI`)

| # | Where | Replace with |
| --- | --- | --- |
| 62 | `qml/CameraPage.qml:543-544` | `// Raw takes say what the sensor delivers on the resolution line itself, same size as the pixel numbers: "3840x2160 · 16-bit · Clear HDR".` |
| 63 | `qml/CameraPage.qml:709-711` | `// 16-bit Clear HDR: 2 bytes a pixel, so the time-left estimate must not read it as 12. The IMX477 frame-rate tables treat anything above 10 as their 12-bit table.` |
| 64 | `qml/CameraPage.qml:858`, `:4339`, `qml/ExternalMonitorWindow.qml:1427` | `// A list works on any sensor. ...` ; `// Recording frame: a red border at the screen's edges during a camera take, next to the REC indicator; a switch in Settings -> Monitoring.` ; `// Recording frame: a red border at the monitor's edges during a take.` |
| 65 | `src/ApertarControlBridge.cpp:2666` | `// Core's flat JSON delivers scalars as strings; accept numbers too.` |

### Drivers

| # | Where | Replace with |
| --- | --- | --- |
| 66 | `imx585.c:706-710` | `/* mode_window_16bit_2x2_regs (ADDMODE binning + windowed RAW16) is deliberately absent: every windowed 2x2 RAW16 crop returns the OB pedestal on hardware, so no table entry selects it. See the comment above IMX585_MODE_1080P_16BIT_HDR. */` |
| 67 | `imx585.c:1008-1012`, `4449-4450` | `/* get_mode_table() hands out the 12-bit Clear HDR list as the contiguous range [...] ... */` (drop "WP-585-9:") ; `... against the invariants of the mode tables.` (drop "WP-585-1 through WP-585-8 established. This table has broken in four independent ways in one day of history") |
| 68 | `imx283.c:776-784`, `:842`, `:678-690` | Replace each "HISTORY" / "REBUILD" paragraph by one statement of what the value or macro is now (read the paragraph first; the facts are in it: which window offset is used, which timing value the family carries, that the macro takes the crop family). Remove the `CINEPI_26-09-27_...` clip name, "(operator, 2026-09-27)", commit hashes and "development/imx283-active-size/REBUILD.md". Text not written here because the right values must be confirmed against the driver. |
| 69 | `APERTAR.md` (both drivers), `README.md` (imx585 :148-159, imx283 :32), `EXPERIMENTAL_CROPS.md` | Describe the branch by what it holds; replace "`cinemate-modes`", "`cinemate-7modes`", "CineMate's sensor detection", the dated hardware-pass entries (`2026-08-31`, `2026-09-21`) with the measured result without the date and the work-package id. |

## G. Findings summary

See the structured result. Clean-up order: (1) the 20 KB/critic/design pointers and the 5 "CineMate Log" strings, since they leak into the journal and into files the operator reads; (2) ids and names in Core headers and big .cpp files; (3) the 12 "not in any repository" header banners; (4) density: rewrite new files to one line per function; (5) drivers.

Commands used: `git -C <repo> diff -U0 --minimal <base> cinemate-port` parsed to `file<TAB>line<TAB>text`, then regex per kind; densities from `git show <ref>:<path>`.
