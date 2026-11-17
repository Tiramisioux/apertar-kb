# Sweep X2: Raspberry Pi model compatibility of the cinemate port

| | |
| --- | --- |
| Refs | Core `cinemate-port` `01f170c` against `origin/main` `f60e301` and `upstream-1.6.0` `35dbe67`. UI `cinemate-port` `7ea9afc` against `origin/main` `4415a55` and `upstream-1.6.0` `43888e5`. imx585 driver `cd548ef` against `origin/apertar` `e5b74d3`. imx283 driver `68b7dc9` against `origin/master` |
| Method | Every added line of the four diffs was indexed with its file and line (34 618 Core, 2 414 UI, 5 628 driver lines) and searched per class (section 5). Each hit was read in the file. Two scratch programs ran the port's pure headers on this host (output in section 6, sources in section 8) |
| Labels | **(r)** read in code. **(h)** the pure function was run on this host. **(b)** needs a board: there is no Pi here. "owner" = the owner's CM5 rig, as the task states; not verified here |
| Short names | `App`, `CC`, `WCP` as in the brief. `Caps` = `include/apertar/core/RecordingCapabilities.hpp`. `BCT` = `src/hardware/BootConfigText.hpp`. `HCT` = `src/hardware/HardwareConfigText.hpp`. `CM` = `src/hardware/ControlsModel.hpp`. Rule numbers (S14, S15, N7, N8) are from `raw/conv-core-camera.md` |
| Not reachable | `www.raspberrypi.com` is outside this session's network. Statements about the firmware's `[pi3]` / `[pi02]` filters are from the Raspberry Pi config.txt documentation as remembered, and are marked |

## Result in five lines

1. Code that names a Pi model is small in the port: one board detector for the Boot Config card and one config.txt filter. Recording formats still go through upstream's gate. The risks are of three kinds: models that only fit the 40-pin header and the display of the owner's rig, that detector, and write-path defaults measured on one CM5 with NVMe.
2. The Controls page lost the GPIO chip (`chip=`) and its checks treat every line as a header pin. A hardware file upstream accepts is refused, on every board. `work/improve` `04fe197` puts it back; it is not on `cinemate-port` yet and not run on a Pi.
3. The Boot Config card brings a third board detector. It reads an unknown board as a Pi 5, gets the Zero 2 W's filters wrong, offers Pi 5 link rates on a Pi 3, and does not see `include camera-selection.txt`.
4. A missing `[display]` section or hardware file now means HDMI 1080p external-only. On a rig with the DPI touch panel the touch UI window is hidden.
5. Pi 4 and CM4: every raw take now runs a changed write path that nobody ran there. This is "unknown", with a test list in section 4.

## 1. Baseline: what original Apertar supports and how it tells boards apart

### 1.1 Supported boards (upstream's own words)

| Board family | Clip recording | Ref @upstream-1.6.0 |
| --- | --- | --- |
| Pi 5 / CM5-class | cDNG uncompressed, lossless, lossy; MLV; H.264 (software); ProRes | Core `README.md:64`, UI `README.md:61` |
| Pi 4 / Pi 400 / CM4-class | uncompressed cDNG, MLV, H.264 (hardware, 1080p30) | Core `README.md:65`, `:70` |
| Pi 3 / Pi 3A+ / Zero 2 W "and other supported USB 2.0-only boards" | H.264 only. RAW clips and ProRes disabled. Stills are separate | Core `README.md:66-68` |
| Tuning | `defaults-pisp` (target `pisp`) on Pi 5-class, `defaults-vc4` (target `bcm2835`) on Pi 3/4-class | Core `README.md:138-143` |

"Available settings depend on your board, sensor, camera driver and tuning file. A selectable frame rate is not a promise that every recording format or storage device can sustain it." (Core `README.md:20`)

### 1.2 How upstream gates (the measuring stick)

| # | Mechanism | Where @upstream-1.6.0 | Decides |
| --- | --- | --- | --- |
| G1 | SoC from the device tree `compatible`, exact strings `brcm,bcm2712` / `bcm2711` / `bcm2837` / `bcm2836` / `bcm2835`, read once into a function-local static | `Caps:18-35`, `Caps:37-50` | `rawCompression`, `prores`, `hardwareH264`, `rawRecording` |
| G2 | The same flags as JSON `recording_capabilities` for both UIs | `Caps:52-62`; UI `src/ApertarControlBridge.cpp:1286-1299`; `WCP:9524-9529` (options hidden and disabled) | What the UIs offer |
| G3 | Enforced in the setter, first in the sanitise chain, and at record start (rules S14, S15) | `Caps:64-77`, `Caps:79-106`; `CC:2709`, `CC:7923`, `CC:8234` | What can be recorded. The refusal is a sentence that names the hardware (N8) |
| G4 | ISP pipeline from the same SoC list | `src/camera/DefaultTuningSelection.hpp:18-49` | Tuning folder and target check |
| G5 | Unknown platform: do not guess | `DefaultTuningSelection.hpp:67` "Do not guess a Pi pipeline on another platform."; `Caps:47` returns the empty capability set | Conservative default |
| G6 | Model string for UI-only notes | `App:4939` (`device.pi_model`), `WCP:4815-4821`, UI `qml/SettingsPage.qml:97` ("Fan mode is unavailable on Raspberry Pi 4.") | A note, a disabled control |
| G7 | Model string in a helper that fails safe | UI `src/StandbyUsbPower.cpp:59-60` ("supported only on Raspberry Pi 5"), `:80` ("Unexpected Pi 5 USB topology; keeping USB powered"); UI `src/PreviewWindowRenderer.cpp:33-40` (Pi 3 planar path) | A feature stays off unless the board is proven |
| G8 | Per-family defaults inside one function | `CC:1126` `recordingCapabilities().hardwareH264 ? 4u : 6u`; `CC:6001-6004` "must not silently add large RAW buffers on memory-constrained VC4 boards" | Buffer counts |
| G9 | Probe and score, with a config key for the wiring | `src/hardware/GpioInput.cpp:238-263` (score `rp1` 100, `pinctrl_bcm` / `bcm2711` / `bcm2835` 90), `:431-432` (`chip` / `gpiochip` / `gpio_chip`), `:507-535`; lines 0 to 63 (`:233`); `TriggerOutput.cpp:311`; `RecordingIndicatorOutput.cpp:319`, `:347`; `src/video/H264Hardware.hpp:19` | Which GPIO chip, which encoder |
| G10 | Wiring that differs per rig is a key in `apertar-hardware.conf` | template `App:4291-4400`: `bus=4` (INA219), `gpiochip=auto`, `[cfexpress_hat] bus=10 address=0x34`, `[storage] pcie_controller=1000110000.pcie`; UI `src/Ina219Bridge.cpp:180`, `:191` (`chip=auto` in `[gpio_buttons]` and `[gpio_encoders]`) | Bus numbers, chip, PCIe controller |

### 1.3 Gates the port added

| Gate | Where @cinemate-port | Same as upstream? |
| --- | --- | --- |
| Calls to G3 in new code | `CC:10842` (ladder), `CC:12070` (pre-roll), `CC:8703` (cached raw buffers, kept from fork main) | yes |
| `tuning::nativePipeline()` for the tdn copy | `CC:7300`, `CC:7311-7313`; `src/camera/TuningTdnStrip.hpp:417` | yes (G4) |
| `bootconf::Board` from `compatible` and `model` | `BCT:76-98`, `App:3653-3657` | no: a third detector, substring match, another SoC list, unknown = Pi 5 (finding 4) |
| config.txt filter in the Controls validator | `HCT:1037-1051` | no: `[pi5]` and `[all]` only (finding 5) |
| `recording_capabilities` in new WebUI cards | none in added lines (`WCP:11156` is an upstream line with one more condition) | missing (finding 9) |

The added lines never call `recordingCapabilities()` for a new decision of their own. They rely on the sanitiser, which is correct for formats and leaves everything else ungated.

## 2. Matrix

Cells: `ok`, `degrades` (works with less, or safely does nothing), `breaks` (wrong result or a refused valid input), `unknown`, `n/a` (hardware or upstream's gate rules it out). "Pi 3 / Z2W" = Pi 3, Pi 3A+, Zero 2 W.

| # | Feature or code path of the port | Pi 5 | CM5 | Pi 4 | CM4 | Pi 3 / Z2W | Basis | Finding |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A1 | GPIO buttons, encoders, switches on the 40-pin header (`chip=auto`) | ok | ok (owner) | ok | ok | ok | r | - |
| A2 | GPIO lines on another chip (`chip=/dev/gpiochipN`: expander, microcontroller), lines above 27 | breaks | breaks | breaks | breaks | breaks | h | 1 (fixed on `work/improve`) |
| A3 | Edge events with the `poll_ms` fallback | ok | ok | ok | ok | ok | r; a chip without interrupts: b | - |
| A4 | Controls check "a DPI display holds GPIO 0 to 27" (reads config.txt) | ok | degrades | breaks | breaks | breaks | h | 5 |
| A5 | I2C bus list, scan, device probes | ok | ok | ok | ok | ok | r | - |
| A6 | CFexpress hat slot byte in the media watcher (bus 10, 0x34 from upstream's template) | ok | ok (owner) | ok | ok | ok | r | - |
| B1 | Boot Config: board family and the section it edits | ok | ok | ok | ok | Pi 3 ok, Z2W breaks | h, docs | 4 |
| B2 | Boot Config: link-frequency menu | ok | ok | degrades | degrades | breaks | h | 6 |
| B3 | Boot Config: RP1 overclock switch | ok | ok | ok (hidden) | ok (hidden) | ok (hidden) | h | 4 (boards read as Pi 5) |
| B4 | Boot Config: sensor loaded through `include camera-selection.txt` | breaks | breaks | breaks | breaks | breaks | h; file content probable | 3 |
| B5 | Boot Config and fan mode through the root helper | ok | ok | ok | ok | degrades | r | 11 |
| C1 | Recording-format gates (sanitiser, setters, record start) | ok | ok | ok | ok | ok | r | - |
| C2 | Raw takes: one request per raw buffer, copy worker, two requests held | ok | ok (owner) | unknown | unknown | n/a | b | 7 |
| C3 | Per-DNG writeback, 1 s fsync, page-cache drop (default on) | ok | ok (owner, NVMe) | unknown | unknown | n/a | b | 7 |
| C4 | Storage pre-roll (default on) | ok | ok (owner) | unknown | unknown | degrades (skipped) | r, b | 7 |
| C5 | Raw copy pool kept between takes | ok | ok | degrades | degrades | n/a | r | 8 |
| C6 | Writer count, queue depth, media profile | ok | ok | ok | ok | n/a | r | - |
| C7 | RAM write buffer (`buffer=ram`, opt-in) | ok | ok | degrades | degrades | n/a | r | - |
| C8 | Drive trim (default on) | ok | ok | ok | ok | ok | r | - |
| C9 | Kernel media tuning (`kernel_tune`, opt-in) | ok | ok | unknown | unknown | unknown | r | 10 |
| C10 | Split clips, merge worker | ok | ok | ok | ok | n/a | r | - |
| C11 | Mode Ladder | ok | ok | degrades | degrades | degrades (inactive) | r | 9 |
| C12 | "Clear HDR uncompressed, SDR lossless" rule | ok | ok | degrades | degrades | n/a | r | 9 |
| C13 | Speed ramp | ok | ok | ok | ok | degrades (refused with a sentence) | r | - |
| C14 | Frame-rate phase lock (off by default) | ok | ok (owner) | unknown | unknown | unknown | b | 14 |
| C15 | Preview temporal denoise switch (default: stripped) | changes the ISP outputs | same | no-op | no-op | no-op | r | 15 |
| C16 | CineMate Log (off by default) | ok | ok | degrades | degrades | n/a | r | - |
| C17 | Clear HDR: 8 raw buffers, CPU-cached heap behind `rawCompression` | ok | ok (owner) | unknown | unknown | degrades (cleared for H.264) | r, b | 14 |
| C18 | IMX585 mode tables, exact-mode check, cinemate-port driver | ok | ok (owner) | unknown | unknown | unknown | b | 14 |
| C19 | IMX283 family (overlay is 4-lane only) | ok | ok (owner) | n/a | unknown | n/a | r, b | 14, 16 |
| C20 | Sensor probe at start-up | ok | ok | unknown | unknown | unknown | b | 14 |
| C21 | Real-time scheduling knobs (opt-in) | ok | ok | ok | ok | ok | r | 12 |
| D1 | Clip browser and viewer (Core decodes the DNG) | ok | ok | ok | ok | unknown | r, b | - |
| D2 | Viewer on an 8-bit DNG clip (IMX477 8-bit modes) | breaks | breaks | breaks | breaks | n/a | r | 13 |
| E1 | Display defaults when the file or its `[display]` keys are missing | breaks on a DPI-panel rig | same | same | same | same | r | 2 |
| E2 | Fan mode asked of Core by the UI | ok | ok | ok | ok | ok | r | - |
| E3 | CFexpress automounter: card pulled while mounted | ok | ok (owner) | n/a | n/a | n/a | r | - |
| F1 | Driver overlays (`ccmp`, IMX283 `link-frequency`), kernel 6.12 headers | ok | ok | ok | ok | ok | r | 16 |

Notes on single cells:

| Cell | What happens | Ref @cinemate-port |
| --- | --- | --- |
| A4, CM5 | DPI overlays under `[cm5]` are not counted, so the warning is missing. Under `[all]` (the stock layout) they are counted | `HCT:1051` |
| A6, any board without the hat | Nothing answers: two failed reads give `Unknown`, and the node and statvfs checks decide as before. An address a kernel driver holds is not read (`I2C_SLAVE` fails) | `src/util/CfeHat.hpp:36-46`, `:55-59`; `src/util/MediaProbe.hpp:203-208` |
| C7 | A small board keeps the frames queue: the plan refuses itself when the RAM budget is below the frames queue | `src/util/BufferBudget.hpp:352-367` |
| C8, any board | No helper: one log line, no trim. A drive without discard (many USB bridges, SD cards): logged once per mount. Three failures: back-off | `App:11505-11517`, `:11572-11577`; `scripts/apertar-media-trim:67-70` |
| C11, C12 on Pi 4 / CM4 | The rung's or the rule's lossless and lossy choice is clamped to uncompressed by `supportedRecordingSettings`, as upstream does for a saved setting | `CC:3028-3032`, `CC:3037-3050`, `CC:3505`; `Caps:84-87` |
| C13, Pi 3 | "FPS ramping works in cDNG and MLV takes only." | `CC:10694-10697` |
| C15, VC4 | The VC4 tuning has no `tdn` member: "the tuning file has no tdn member: using it unchanged". Checked in the libcamera fork: 0 of 44 files in `src/ipa/rpi/vc4/data` have one, 41 of 45 in `pisp/data` do | `src/camera/TuningTdnStrip.hpp:427-430`; `tiramisioux/libcamera` `6b0b49f` |
| C16, VC4 | Packed raw streams cannot carry the curve: "raw stream cannot be mapped on the copy worker, recording linear" | `CC:3983-3987` |
| C17, Pi 3 | H.264 is forced, and the sanitiser clears Clear HDR for processed formats | `Caps:82-83`; `CC:3510-3513` |

## 3. Findings

### X-board-support-1: the Controls page models only the 40-pin header; `chip=` is gone from the card

| | |
| --- | --- |
| Severity | major. Category: removed-upstream-behaviour. Deliberate: yes for the card (commit `c140c4f`: "The GPIO card's settings drop poll and chip (edge events need neither)"), not for the checks |
| Status | Fixed on `work/improve` by `04fe197` "hw, web: the GPIO chip is a setting again, for pins on another chip" (read; the probe of section 6 run against it gives no false error). Not on `cinemate-port`. Not run on a Pi: needs a second gpiochip |
| Upstream | `chip` / `gpiochip` / `gpio_chip` is a key of `[gpio_buttons]`, `[gpio_encoders]`, `[trigger_output]`, `[recording_indicator]`; default `auto`; an explicit path is used as given; lines 0 to 63. `GpioInput.cpp:233`, `:431-432`, `:507-508`; `TriggerOutput.cpp:311-312`; `RecordingIndicatorOutput.cpp:319-320`, `:347-348`; UI template `Ina219Bridge.cpp:180`, `:191` @upstream-1.6.0. The Config page saved any text (`App:5323-5368`, `:7175-7195` @upstream-1.6.0) |

| What the port does | Ref @cinemate-port | Consequence |
| --- | --- | --- |
| The GPIO card offers `enabled`, `active_low`, `pull`, `debounce_ms`. Comment: "poll_ms (chips without edge events) and chip stay text-only: the Pi 5's header needs neither". The card had both in `166cc4d` | `CM:258-263` | The chip can only be typed in the text editor |
| Tally and trigger cards: no `chip`, `line` capped at 27 | `CM:264-271` | Same |
| Free pins are 4 to 27 whatever the chip | `CM:381` | The dropdown lists header pins for an expander |
| A switch's pins are 0 to 27; the reader takes 0 to 63 | `HCT:694-700`; `GpioInput.cpp:326` | `switch0_pins=40` is an error |
| One owner per line number, not per chip; "GPIO 2/3 is SDA/SCL of I2C bus 1"; "held by the DPI overlay" for every line up to 27 | `HCT:858-872` | False errors `gpio_twice`, `gpio_i2c1`, `gpio_dpi` for lines of another chip (h) |
| A save that adds an error is refused; the WebUI sends no `force` | `src/hardware/HardwareConfigStore.cpp:336-341`; `App:8644-8660` | A valid file is "Not saved: N new errors", from the card and from the text editor (h: 5 new errors) |
| The chip status reads `[gpio_buttons]` only and 28 lines; the reader lets `[gpio_encoders]` override the chip | `App:11987-11989`; `GpioInput.cpp:343-344` | The page can name another chip than Core uses |
| The page greys GPIO 0 to 27 for a DPI display whatever the chip | `WCP:17197-17200`, `WCP:17260-17264` | No pin can be picked |
| The touch UI shows "Controls: N errors" from the same checks | UI `qml/ControlsWarning.qml`, `qml/CameraPage.qml:2718` | A working rig with another chip shows a warning |

Who is hit: a rig whose DPI panel holds the header (upstream's default display) has no other way to GPIO buttons than a second chip. Also a CM3 carrier that uses GPIO 28 to 45.

Fix (the shape `04fe197` has; listed so the merge keeps all of it):

1. `CM:258-263`: `{"chip", "GPIO chip", "text", "auto", "", 0, 0}` and `{"poll_ms", "Poll every (ms)", "number", "12", "", 2, 1000}` back, as in `166cc4d` / `0c49601`. The same `chip` row for the trigger and the tally.
2. `HCT:858-872`: key the claims by chip and line; apply `gpio_i2c1` and `gpio_dpi` only when the section's chip is `auto` or the header chip.
3. `HCT:700`: 0 to 63, the reader's bound.
4. `CM:381`: 4 to 27 only for the header chip; for a named chip its own line count.
5. `App:11987-11989`: the chip the reader ends up with, and the chip's line count instead of 28.
6. Still open after `04fe197`: finding 5 (config.txt filter). `[gpio_encoders]` keeps no `chip` key of its own by decision of that commit (it warns).

### X-board-support-2: display defaults are the owner's HDMI rig

| | |
| --- | --- |
| Severity | major. Category: stock-behaviour-change. Deliberate: yes (`7af9f13`: "the old Hyperpixel screen, which is not what this camera uses"; UI `7c41a27`, `c9d841f`) |
| Upstream | Fallback 720x720, layout `square`, `hdmi_external_only=false`; the UI writes a default file when none exists. UI `src/DisplayConfigBridge.cpp:14-15`, `:577-584`, `:646-649`; template `Ina219Bridge.cpp:323-339`; Core template `App:4312-4330` @upstream-1.6.0 |
| Port | Fallback 1920x1080, `landscape_large`, `hdmi_external_only=true`; the UI no longer writes a file. UI `src/DisplayConfigBridge.cpp:11-12`, `:287-294`, `:354-357`; `DisplayConfigBridge.hpp:52-59`; Core template `App:5081-5098` @cinemate-port |
| Consequence (r) | `if (hdmiExternalOnly) { window->hide(); }` (UI `src/main.cpp:432-433`). On a rig with the DPI touch panel and no hardware file, or a file without `hdmi_external_only`, the touch UI is hidden and the layout is for 1080p. Any board |
| Fix | Restore upstream's four defaults in the bridge, the header and Core's template. The owner's values belong in his `apertar-hardware.conf` |
| Effort | S |

### X-board-support-3: the Boot Config card does not see `include camera-selection.txt`

| | |
| --- | --- |
| Severity | major. Category: bug. Deliberate: unknown |
| Evidence | The card's own fixture is "The dev Pi's /boot/firmware/config.txt on 2026-11-01 (Apertar-Beta 1.6.0, DPI overlays commented out by hand)" and still carries the image's comment: `#IMPORTANT! If your camera module doesn't get detected by the script, remove the "include camera-selection.txt" line` (`tools/boot_config_test.cpp:18`, `:56` @cinemate-port). The include line itself is gone from that file. Upstream's UI reads the included file as the truth: "Apertar's camera-selection file is authoritative" (UI `src/DeviceInfoBridge.cpp:213-215` @upstream-1.6.0). **probable**: the stock image's config.txt is not in this container |
| Port | A line without `=` has no key and is ignored (`BCT:270-307`). Host run: a `[pi5]` section with `include camera-selection.txt` reads as cam0 = none, cam1 = none, no warning (h) |
| Consequence | On a stock image the card shows no sensor. Choosing a sensor adds a second `dtoverlay=` next to the included one; choosing another sensor loads two sensors on one connector; "None connected" changes nothing. The read-back agrees with the request because it reads the same way |
| Fix | In `readState`: an uncommented, applying `include` line sets a warning ("config.txt includes <file>: the sensor comes from that file") and makes the camera rows read-only, the way `state.editable` and `state.problem` already do for a file that is not the Apertar layout (`BCT:616-622`). Reading the included file is the larger option |
| Effort | S for the warning, M for reading the file |
| Settle it | `grep -n '^include' /boot/firmware/config.txt; cat /boot/firmware/camera-selection.txt` on a freshly flashed Apertar-Beta 1.6.0 image |

### X-board-support-4: a third board detector, with "unknown = Pi 5" and wrong Zero 2 W filters

| | |
| --- | --- |
| Severity | major. Category: mismatch. Deliberate: unknown (the substring test comes from Cinemate: `cinemate/src/module/app/boot_config.py:173-175`) |
| Upstream | One SoC list in one header (S14): `Caps:18-35`; the same list for the pipeline: `DefaultTuningSelection.hpp:18-31`. Unknown is not guessed (`DefaultTuningSelection.hpp:67`). BCM2836 and BCM2835 are known boards |
| Port | `BCT:84-98`: substring match on `bcm2712`, `bcm2711`, `bcm2837`, `bcm2710`; `if (!board.detected) board.family = "pi5";` (`BCT:95`); filters `BCT:102-119`; section = family (`BCT:122`) |

Host run of the port's functions (h):

| Board | family | detected | `[pi5]` | `[pi3]` | `[pi02]` | `[pi0]` | `[pi0w]` |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Pi 5 | pi5 | yes | applies | - | - | - | - |
| CM5 | pi5 | yes | applies | - | - | - | - |
| Pi 4, CM4 | pi4 | yes | - | - | - | - | - |
| Pi 3B+ | pi3 | yes | - | applies | - | - | - |
| Zero 2 W | pi3 | yes | - | applies | applies | - | - |
| Pi 2 (BCM2836) | pi5 | no | applies | - | - | - | - |
| Zero W (BCM2835) | pi5 | no | applies | - | - | - | - |

| Board | What happens | Basis |
| --- | --- | --- |
| Zero 2 W | The firmware applies `[pi0]`, `[pi0w]` and `[pi02]` to a Zero 2 W, not `[pi3]` (documentation, remembered). With a `[pi3]` section in the file the card uncomments `dtoverlay=imx477` there and reports success: the read-back uses the same rule. The firmware ignores the line: no camera after the reboot. Lines under `[pi0]` and `[pi0w]` are shown as not applying | h for the card; firmware rule needs a Zero 2 W |
| Pi 2, Zero W, any machine without a known SoC | Read as a Pi 5: two camera connectors, `[pi5]` lines count, and the RP1 switch shows when an `rp1-clk` overlay file exists (it does on an Apertar image, where the stock file loads it from `[all]`) | h |
| Stock layout on a Pi 3 or Zero 2 W | No `[pi3]` section, so the card edits `[all]`: ok | h |

Fix:

1. Build the family from upstream's exact SoC strings. Smallest: one `inline` helper beside `recordingCapabilitiesFromCompatible` in `Caps` that returns the first matching SoC, used by `Caps:18-35`, `DefaultTuningSelection.hpp:18-31` and `BCT:84-98`. BCM2836 and BCM2835 become their own family.
2. Unknown board: `state.editable = false` with a sentence, instead of `family = "pi5"`. Keep the Pi 5 reading only for `APERTAR_BOOT_CONFIG` (the test copy).
3. Zero 2 W: `[pi3]` does not apply; `[pi0]`, `[pi0w]`, `[pi02]` do; `boardSection` is `pi02` when the model says Zero 2. Confirm on a board first.
4. `scripts/apertar-boot-config:51-54` and `README.md:183` then name the same sections (finding 11).

Effort: S for 1 and 2, S for 3 after a board check.

### X-board-support-5: the Controls validator reads config.txt as a Pi 5 would

| | |
| --- | --- |
| Severity | minor. Category: pi-compat. Deliberate: unknown |
| Port | `HCT:1037` "Only [pi5]/[all] apply here."; `HCT:1051` `applies = filter == "[all]" \|\| filter == "[pi5]";`. Used for the DPI facts: `App:4976` |
| Beside it | The Boot Config card has a reader that knows the board: `BCT:102-119`, `BCT:551-554` (`state.displayLines`). Two readers of one file with two rules |
| Consequence (h) | DPI overlays under `[pi4]` or `[cm5]`: 0 lines seen. Under `[pi5]`: 1 line seen on every board. On a Pi 4 that means either no DPI warning, or every header pin greyed and `gpio_dpi` errors that refuse a save. Stock layout (DPI list in `[all]`): correct on every board |
| Fix | `hardwareConfigFacts()` takes the lines from the card's reader: `bootconf::readState(bootconf::parseDocument(text, facts.board), facts.board).displayLines`. Delete `parseConfigTxt`'s filter code, or the function if `dpiCommands` is its last user |
| Effort | S |

### X-board-support-6: the link-frequency cap exists for family "pi4" only

| | |
| --- | --- |
| Severity | minor. Category: pi-compat. Deliberate: unknown |
| Port | `BCT:186` `if (board.family != "pi4" \|\| !sensor.pi4MaxHz \|\| option.hz <= sensor.pi4MaxHz)`. Field comment: "options above this are left off on a Pi 4" (`BCT:147`) |
| Consequence (h) | Pi 3 and Zero 2 W get the Pi 5 list: IMX477 450 to 972 MHz, IMX585 297 to 1039.5 MHz, with the entries marked "over RP1 spec". **probable**: the stock imx477 driver checks the link frequency when it probes, so a value it does not know means no camera after the reboot (the kernel source is not here; `config.txt.apertar.bak` is the way back) |
| Also | Labels say "up to N fps at 4K" from the 4-lane table (`BCT:156-160`, `:198-202`) on a 2-lane connector, and "over RP1 spec" on boards without an RP1 (`BCT:205`). A new sensor line never gets `2lane`; an existing one keeps it (`BCT:909-916`) |
| Fix | `board.family == "pi5" \|\| ...`: the cap holds for every board that is not Pi 5-class. Rename `pi4MaxHz` to say so. Drop the fps text when the board is not Pi 5-class |
| Effort | S |

### X-board-support-7: the raw write path changed for every board and was run on one

| | |
| --- | --- |
| Severity | major. Category: pi-compat. Deliberate: yes (each change has a measurement on the CM5 in its commit) |
| Upstream | Three requests in flight for four raw buffers (`CC:1023-1024`, `CC:6461`); the frame is copied on libcamera's thread (`CC:6933`); no per-file sync, no pre-roll. Per-family defaults where memory matters (G8). All @upstream-1.6.0 |

| Change, on by default | Ref @cinemate-port | Why a Pi 4 or CM4 may differ | Knob |
| --- | --- | --- | --- |
| One request per raw buffer, 4 buffers (6 on FAT and NTFS, 8 in Clear HDR) | `CC:1338`, `CC:1458-1470`, `CC:8846-8852` | Unicam buffers come from CMA; the VC4 pipeline was never run with all buffers queued | `APERTAR_RAW_CAMERA_BUFFERS` |
| Copy worker; at most `buffers - 2` requests held, the rest dropped as `dropped_copy_slot` | `CC:8730-8736`, `CC:4386` | Reading an uncached CMA buffer is slow; a frame that waited at the driver is now a counted drop | `APERTAR_RAW_COPY_WORKERS` |
| `sync_file_range` per DNG, `fsync` of finished files and the folder every second, page-cache drop after it | `CC:4714-4727`, `CC:4365-4369`, `CC:4761-4764` | USB bridges and SD cards answer `fsync` far slower than NVMe | `APERTAR_DNG_WRITEBACK=0`, `APERTAR_MEDIA_SYNC_MS=0`, `APERTAR_DNG_DONTNEED` |
| Storage pre-roll: a 2 s raw take at the mode's maximum fps at Core start, card insert and after a format | `src/util/StoragePreroll.hpp:92-99`; `App:10943-10960`; `CC:12051-12104` | Hundreds of MB written and deleted at every start on whatever medium is mounted | `[media] preroll=off`, `APERTAR_STORAGE_PREROLL=0` |

What can be said without a board: the code is board-neutral, the format gate holds (C1), and each change has a switch back. What cannot: whether a Pi 4 with an IMX477 drops more or fewer frames than on 1.6.0.

Fix, in this order:

1. Run test T1 of section 4 on a Pi 4. If it matches 1.6.0, nothing to change.
2. If no board is at hand before the merge: follow G8. Where `recordingCapabilities().hardwareH264` is true, keep upstream's behaviour for the pre-roll (automatic off) and the per-file sync (off), in the functions that read the knobs (`App:11154`, `CC:4365`, `CC:4718`). One line each, the same shape as `CC:1126` @upstream-1.6.0.

Effort: M (a board session), or S for the fallback.

### X-board-support-8: the raw copy pool is kept between takes

| | |
| --- | --- |
| Severity | minor. Category: pi-compat. Deliberate: yes (`db17860`: "The raw copy pool now survives takes"; the same message says "Idle memory not re-measured; swap use was high during the runs") |
| Upstream | The pool is freed at every stop: `rawPool_.clear();` (`CC:3487` @upstream-1.6.0) |
| Port | After a take the pool keeps `min(queue, max(workers + 2, 4))` frames = 6 with four writers (`CC:5547-5550`, `CC:4935-4945`), until the session is configured again (`CC:8698`). It is filled before the first frame (`CC:4903-4931`) |
| Consequence (r) | Held while idle after the first take: 6 x 18.5 MB = 111 MB (IMX477 full frame, 12-bit packed), 6 x 16.9 MB = 101 MB (IMX585 4K 16-bit). On a 1 or 2 GB Pi 4 this memory no longer goes back to the system between takes. The peak during a take is as upstream |
| Fix | Free the idle pool when the camera has been idle for 30 s, the rule the port's own playback slots have (`src/playback/DecodeSlots.hpp:9-13`), or keep it only when `MemTotal` allows it, read the way `BufferBudget.hpp:83-95` reads it |
| Effort | S |

### X-board-support-9: the new cards do not follow `recording_capabilities`

| | |
| --- | --- |
| Severity | minor. Category: mismatch. Deliberate: unknown |
| Upstream | An option the board cannot do is hidden and disabled (`WCP:9524-9529` @upstream-1.6.0), and the refusal is a sentence (`Caps:64-77`, N8) |
| Port | The ladder editor offers Uncompressed, Lossless JPEG, Lossy 3:1 and 5:1 per resolution (`WCP:8155-8166`). Core reports a ceiling per compression (`CC:10949-10959`: "0 where the compression cannot run the mode"). On a board without `rawCompression` the probe goes through the sanitiser, which turns lossless and lossy into uncompressed, so every compression comes back usable with the uncompressed ceiling. The default of an unnamed SDR resolution is `lossless_jpeg` (`src/camera/ModeLadder.hpp:41-44`) |
| Consequence (r) | Pi 4 and CM4: the editor shows "Lossless JPEG, smaller files, N MB per frame" and Core records uncompressed. No sentence. Pi 3 and Zero 2 W: Mode Ladder, Speed Ramp, write buffer and pre-roll cards are shown for a board that records H.264 only |
| Fix | `CC:10949-10959`: `state.ceilingBy[i] = 0` for `i >= 1` when `!recordingCapabilities().rawCompression`; the editor then prints "(not available)" by its own rule (`WCP:7740-7746`). `ModeLadder.hpp:41-44` stays pure; the caller picks `none` as the default on such a board. In `WCP`, hide the raw-only cards when `recording_capabilities.raw_recording === false`, with the helper upstream has (`recordingFeatureSupported`, `WCP:9488` @cinemate-port) |
| Effort | S |

### X-board-support-10: the media tuning helper sets dirty-page limits in absolute bytes

| | |
| --- | --- |
| Severity | minor (opt-in: `APERTAR_MEDIA_TUNE=1` or `kernel_tune`, `App:11396-11408`). Category: pi-compat |
| Port | `scripts/apertar-media-tune:68-71`: `dirty_bytes` 1 GiB (NVMe), 512 MiB (USB UAS), 256 MiB (USB storage, SD); written at `:89-90` after the ratios are set to 0 |
| Consequence (r) | On a 512 MB Zero 2 W or a 1 GB Pi 3 / Pi 4 the limit is half of RAM or all of it. Buffered writers (MLV, H.264, audio, the DNG path of this fork) are then throttled late or not at all. Not measured |
| Fix | Cap both values by `MemTotal` in the script (`dirty_bytes` at a quarter, the background value at half of that), the way `BufferBudget.hpp:349-350` caps the RAM queue |
| Effort | S |

### X-board-support-11: the root helper wants `[pi5]`, `[pi4]` or `[all]`, and the fan mode now goes through it

| | |
| --- | --- |
| Severity | minor. Category: stock-behaviour-change |
| Upstream | The fan mode installs the new text with `sudo -n install`, no content rule (`App:3127-3165` @upstream-1.6.0) |
| Port | `scripts/apertar-boot-config:51-54` refuses text without one of the three headers. Core does not fall back when the helper said no (`App:3586-3592`). The fan mode uses the same writer (`App:3620-3649`). Core itself calls a file editable with the board's section or `[all]` (`BCT:616-622`) |
| Consequence (r) | A config.txt without those headers (hand-written, or `[pi3]` only): the fan mode and the card fail with "not the Apertar config.txt" once the helper is installed. On 1.6.0 the fan mode worked on such a file |
| Fix | The helper accepts any `[section]` header, or no header rule at all: Core's `textProblem` already checks size and NUL bytes (`BCT:1133-1139`) |
| Effort | S |

### X-board-support-12: `APERTAR_RT=1` pins to cores 1 to 3

| | |
| --- | --- |
| Severity | nit (opt-in). Category: pi-compat |
| Port | `scripts/start-apertar-core.sh:28` `RT_CPUS="${APERTAR_RT_CPUS-1-3}"`, `:34-36` `taskset -c "$RT_CPUS"`, then `exec` (`:44`) |
| Consequence (r) | Every supported board has four cores, so this holds today. With fewer CPUs online (`maxcpus=`, a single-core board) `taskset` fails and Core does not start; systemd restarts it in a loop |
| Fix | Test it the way the script tests `chrt` at `:29`: `taskset -c "$RT_CPUS" /bin/true 2>/dev/null` before adding it to the prefix |
| Effort | S |

### X-board-support-13: the clip viewer refuses 8-bit DNG

| | |
| --- | --- |
| Severity | minor. Category: bug |
| Upstream | "RAW storage precision can be 8, 10 or 12 bits" (Core `README.md:42`). The IMX477 has 8-bit modes up to 282 fps (`CC:3175-3220` @cinemate-port keeps the table) |
| Port | `src/playback/DngTags.hpp:307-312`: `info.bits != 10 && info.bits != 12 && info.bits != 16` gives "Unsupported DNG layout (size, bit depth or compression)." The reader has no 8-bit row either (`src/playback/DngFrameReader.hpp:67-82`). The port's own writer handles 8-bit ("write unpacked 16-bit and 8-bit payloads straight from the frame", `e55557d`) |
| Consequence (r) | An 8-bit IMX477 clip cannot be opened in the WebUI's browser and viewer. The IMX477 is the usual sensor on a Pi 4; the owner's IMX585 and IMX283 have no 8-bit mode |
| Fix | Accept `bits == 8`: one byte per sample in `dngRowBytes` and one more branch in the row loop |
| Effort | S |

### X-board-support-14: sensor paths that were run on a CM5 only

| | |
| --- | --- |
| Severity | minor. Category: pi-compat. Deliberate: yes for the scope (both drivers' `APERTAR.md:3-4`: "Raspberry Pi 5 or CM5") |
| Upstream | Lists the IMX585 for Pi 3/4 too: "Pi 3/4 needs the VC4 version, not a renamed PiSP file" (Core `README.md:143`). The old driver's README names the 2-lane option (`imx585-v4l2-driver/README.md:94-99`) |

| Path | Ref @cinemate-port | Unknown on | Why |
| --- | --- | --- | --- |
| IMX585: modes from tables, explicit sensor configuration only, a mode the driver adjusts is refused; the auto-configuration fallback for the 12-bit crops is gone | `src/camera/Imx585Modes.hpp:40-98`; `CC:8295-8296` (upstream `CC:5993-5996`); `CC:8485-8528` | Pi 4 (2 lanes), CM4, Pi 3 | The tables are the cinemate-port driver's. Its timings are set for "the Pi 5/RP1 path" (`imx585.c:298`, `:314`) and its hardware pass was on a CM5 (`imx585-v4l2-driver/README.md:250-251`). Unicam and 2 lanes were not run |
| Clear HDR: 8 buffers of 16.9 MB, cached heap only when `rawCompression` | `CC:1334-1338`, `CC:8700-8707` | CM4 | 135 MB of CMA from Unicam; the libcamera fork's 16-bit path is PiSP code (`tiramisioux/libcamera` `src/libcamera/pipeline/rpi/pisp/pisp.cpp`) |
| IMX283: 57 modes, 4-lane overlay | `src/camera/Imx283Modes.hpp`; `imx283-overlay.dts:68`, `:91` | CM4 | 1440 Mbps per lane at the default link; the port adds the `link-frequency` override for 360 MHz (`imx283-overlay.dts:110-117`). Pi 4B, Pi 3 and Zero 2 W have 2-lane connectors: not usable there |
| Sensor probe at start: one `configure()` per mode, per raw format, in both Clear HDR states | `CC:7119-7229` | Pi 4, Pi 3, Zero 2 W | Start-up time on a slower CPU. `APERTAR_SENSOR_PROBE=0` skips it (`CC:7239`) |
| Phase lock: needs `SensorTimestamp` on the clock the audio uses, and `FrameDurationLimits {d, d+1}` to hold the line length | `src/camera/FramePhaseLock.hpp:9-25`; `CC:8887-8975`, `CC:9062-9072` | every VC4 board | Off by default. The IPA behaviour was checked on PiSP |

Fix: no code. State the tested scope in Core's README the way upstream's table does (section 1.1), and run T3 to T6 of section 4 before claiming more. A per-pipeline frame-rate cap has a hook that is empty today: `backendMaximumFps` (`CC:3426-3434`).

### X-board-support-15: preview temporal denoise is off by default (seen in passing)

| | |
| --- | --- |
| Severity | minor for this sweep; it belongs to the camera review. Category: stock-behaviour-change. Deliberate: yes (`e625c68`, README "It is off by default") |
| Port | `Types.hpp:139` `bool previewTdn = false;`. The copy without `tdn` is loaded for every format (`CC:7308-7318`); the ProRes ISP tuning is derived from that copy (`CC:7412`) |
| Consequence | VC4 boards: nothing (matrix C15). Pi 5-class: H.264 and ProRes record the ISP output, so their picture loses temporal denoise by default, not only the preview. **probable**: follows from the code; no frame was compared |
| Fix | Keep upstream's picture by default (`previewTdn = true`), or strip only when a raw format records |
| Effort | S |

### X-board-support-16: drivers need kernel 6.12 and say "Pi 5 or CM5"

| | |
| --- | --- |
| Severity | nit. Category: pi-compat |
| Port | `imx283.c:10` `#include <linux/unaligned.h>` (first in 6.12; the base had `<asm/unaligned.h>`), README says 6.12 or newer. The Apertar imx585 base already includes it (`imx585.c:17`, `origin/apertar` `:16`) |
| Consequence | One kernel floor for both drivers and every board: a 6.6 image cannot build the imx283 module. Board-neutral otherwise: the overlays only add `ccmp` (`imx585-overlay.dts:138`) and `link-frequency` (`imx283-overlay.dts:117`) |
| Fix | None needed if 6.12 is the image's floor. Say it once in Core's README |
| Effort | S |

## 4. Unknown: what to run on which board

| # | Board and parts | Run | Read | Settles |
| --- | --- | --- | --- | --- |
| T1 | Pi 4 (2 GB or less if there is one), IMX477, USB 3 SSD, exFAT | Three 3-minute takes, 12-bit uncompressed cDNG at 24 fps, on 1.6.0 and on the port | `journalctl -u apertar-core -b \| grep -e 'recording stats' -e 'drop\[' -e 'dropped_copy_slot'`; `free -m` before the first take and a minute after the last | Findings 7 and 8 |
| T2 | Same | Start Core with a mounted drive | `journalctl -u apertar-core -b \| grep -i -e 'pre-roll' -e 'sensor probe'` | Pre-roll size and time, probe time (7, 14) |
| T3 | CM4, IMX585 on the 4-lane connector | Clear HDR 16-bit on, one 30 s take | Core's start log; `grep -i cma /proc/meminfo` | Matrix C17, C18 |
| T4 | Pi 4B, IMX585 with `dtoverlay=imx585,2lane` | Select 3840x2160 12-bit, then a crop | `journalctl ... \| grep -e 'adjusted by the driver' -e 'sensor mode:'` | Matrix C18 |
| T5 | Zero 2 W | Put `dtoverlay=disable-bt` under a `[pi3]` header, reboot | `sudo vclog --msg \| grep -i disable-bt` | Whether `[pi3]` applies (finding 4) |
| T6 | Pi 3 or Zero 2 W, IMX477 | Boot Config: pick 720 MHz, save, reboot | `dmesg \| grep -i imx477` | Finding 6 |
| T7 | Any Pi with a second gpiochip (MCP2221, or an MCP23017 with its overlay) | `work/improve` `04fe197`: choose the chip, add a button, save | The card; `journalctl ... \| grep 'GPIO input'` | Finding 1 on hardware |
| T8 | Any VC4 board | `set_fps_phase_lock enabled=true`, a 10-minute take | `grep 'phase-lock stats'` | Matrix C14 |
| T9 | Zero 2 W or Pi 3 | Open the WebUI clip browser on a card that holds cDNG clips | `ps -o rss= -C apertar-core` while it loads | Matrix D1 |
| T10 | Any board with the DPI touch panel | Start the UI with no `apertar-hardware.conf` | The panel | Finding 2 |

## 5. Classes swept

| Class from the task | Hits in added lines | Result |
| --- | --- | --- |
| gpiochip numbers, line counts 0-27 | `CM:263`, `:268`, `:381`; `HCT:700`, `:869`; `App:11989`; `WCP:17199`, `:17262`; scoring moved to `src/hardware/GpioChipInfo.cpp:31-55` unchanged | Finding 1 |
| `/dev/i2c-N` bus numbers | Defaults are upstream's (INA219 4, PCF8574 1, NeoRotary 1, Grove 1, hat 10: `HCT:49-65`). Buses are listed at run time (`App:4965-4978`, `:12147-12164`). "GPIO 2/3 = bus 1" is in finding 1 | No new assumption |
| RP1, rp1-cfe names | `rp1` in the chip score (upstream's) and in the Boot Config switch, gated to family pi5 (`BCT:648-653`, `:1023`). No `rp1-cfe` | ok, but see finding 4 for boards read as Pi 5 |
| PiSP-only formats and controls | `PISP_COMP1` is only tolerated (`CC:8499-8510`, `:8543-8551`). New libcamera names in added lines: `FrameDurationLimits`, `SensorTimestamp`, `FrameDuration`, `ScalerCropMaximum`, `PixelArraySize`, `PixelArrayActiveAreas`, `Model`: all exist on both pipelines | ok |
| `defaults-pisp` and vc4 tuning folders | Only through `tuning::nativePipeline()` (`CC:7300`); the tdn copy is checked with `compatibleFile(target, pipeline)` | ok |
| CPU counts, affinity, SCHED_FIFO, isolcpus | `hardware_concurrency` scaling kept from upstream (`CC:4315-4344`). Cores 1-3 and SCHED_FIFO only behind `APERTAR_RT=1` and `APERTAR_RT_CAPTURE_PRIORITY` | Finding 12 |
| RAM budgets, CMA, buffer counts | `BufferBudget.hpp` (run-time, refuses itself); raw pool; 8 Clear HDR buffers; decode slots 2 x 46 MiB at most (`src/playback/DecodeSlots.hpp:24-30`), freed after 30 s; JPEG caches 8 + 24 MB (`PlaybackFrames.cpp:37`) | Findings 7, 8, 10, 14 |
| PCIe, NVMe, the hat at 0x34 | The port reads `/sys/class/nvme` and block sysfs by class name (`App:12059-12080`, `MediaProbe.hpp:229-255`). The PCIe unbind and rescan helper is upstream's; the port adds `noatime,umask` (`App:4208-4212`). UI: `CfeAutomounter.cpp:549-550`, `:726-760` only with a hat | ok |
| Fan control, cooling device | The block is upstream's (`App:3042-3090` @upstream). The port reroutes the write | Finding 11 |
| config.txt keys and overlays | `BCT` whole file read | Findings 3, 4, 6 |
| DPI pin sets | "A DPI panel takes GPIO 0-27" in six texts (`README.md:197`, `App:3826`, `WCP:5900`, `:18209`, `:20185`, `:20277`) and three checks (`HCT:869`, `WCP:17199`, `:17262`) | Finding 1 (per chip), finding 5 (filter) |
| HDMI connector names | None added. `/sys/class/drm` is listed as it is (`App:3670-3688`) | ok |
| vcgencmd | None | ok |
| Kernel interfaces by version | GPIO v2 line events (v2 is already upstream's request API), `sync_file_range`, `posix_fadvise`, `DMA_BUF_IOCTL_SYNC`, `fstrim` through a helper, `ntfs3` in upstream's helper | ok; drivers: finding 16 |
| Page size (16 KiB against 4 KiB) | No `O_DIRECT`, no `mmap`, no page-size constant in added lines (the fork does not carry direct I/O: `MediaProfile.hpp:133`) | ok |
| 64-bit only | No architecture test or intrinsic added. Upstream ships aarch64 only (UI `mesa-minimal/lib/aarch64-linux-gnu`) | ok |
| 4-lane sensors, Pi 5-only link rates | Frame-rate ceilings come from the start-up probe, tables are the fallback (`src/camera/FpsCeiling.hpp:11-16`). The Boot Config menu is static | Findings 6, 14 |

## 6. Host probes

Two scratch programs, built with `g++ -std=c++20 -I Apertar-Core/src -I Apertar-Core/include`, call the port's header-only code. Nothing was written to a repository.

Probe 1: `boardFromDeviceTree`, `filterApplies`, `boardPorts`, `linkOptionsFor`, `applyRequest`, `readState` (@cinemate-port).

```text
board          family  det  ports      [pi5] [cm5] [pi4] [cm4] [pi3] [pi3+] [pi02] [pi0] [pi0w] [pi2] [all]
Pi 5           pi5     yes  cam0 cam1      y     -     -     -     -      -      -     -      -     -     y
CM5            pi5     yes  cam0 cam1      y     y     -     -     -      -      -     -      -     -     y
Pi 4           pi4     yes  cam1           -     -     y     -     -      -      -     -      -     -     y
CM4            pi4     yes  cam0 cam1      -     -     y     y     -      -      -     -      -     -     y
Pi 3B+         pi3     yes  cam1           -     -     -     -     y      y      -     -      -     -     y
Zero 2 W       pi3     yes  cam1           -     -     -     -     y      -      y     -      -     -     y
Pi 2 (2836)    pi5     NO   cam0 cam1      y     -     -     -     -      -      -     -      -     -     y
Zero W (2835)  pi5     NO   cam0 cam1      y     -     -     -     -      -      -     -      -     -     y
link options Pi 5      imx477: 450 720 750 891* 909* 918* 945* 972*    imx585: 297 360 445 594 720 891* 1039*
link options Pi 4/CM4  imx477: 450                                     imx585: 297 360 445 594 720 891*
link options Pi 3B+    imx477: 450 720 750 891* 909* 918* 945* 972*    imx585: 297 360 445 594 720 891* 1039*
link options Zero 2 W  imx477: 450 720 750 891* 909* 918* 945* 972*    imx585: 297 360 445 594 720 891* 1039*
(* = over the RP1 specification)

Zero 2 W, file "[pi3] #dtoverlay=imx477 / [pi02] dtparam=audio=on / [all] ...", request cam1 = imx477:
  ok=1, the line is uncommented under [pi3]

Pi 5, file "[pi5] include camera-selection.txt / #dtoverlay=imx585,cam0 / [all] camera_auto_detect=0":
  cam0=none cam1=none warnings=0
```

Probe 2: `hwconf::validate`, `newErrors`, `peripheralSettings`, `knownKey`, `modelJson`, `parseConfigTxt`. File: `[gpio_buttons] chip=/dev/gpiochip2`, `d2`, `d3`, `d5`; `[recording_indicator] gpiochip=/dev/gpiochip2 line=7`; `[trigger_output] gpiochip=auto line=7`.

```text
@cinemate-port
== expander chip, HDMI Pi (bus 1 exists)
  ERROR [gpio_i2c1] GPIO 2 is the SDA line of I2C bus 1; button d2 cannot use it while the bus exists.
  ERROR [gpio_i2c1] GPIO 3 is the SCL line of I2C bus 1; button d3 cannot use it while the bus exists.
  ERROR [gpio_twice] GPIO 7 is used by Trigger output (line 20) and Tally (line 14).
== expander chip, DPI Pi (header pins all taken)
  ERROR [gpio_dpi] GPIO 2 / 3 / 5 is held by the DPI overlay (config.txt line 70); button ... cannot use it.
  ERROR [gpio_twice] GPIO 7 is used by Trigger output (line 20) and Tally (line 14).
  ERROR [gpio_dpi] GPIO 7 is held by the DPI overlay (config.txt line 70); Trigger output cannot use it.
== new errors when saving it on the DPI Pi: 5 (a save with new errors is refused)
== switch on line 40
  ERROR [switch_pins] switch0_pins takes one pin (a two-way switch) or two (a three-way switch), such as 17 or 22,23.
== peripheralSettings(gpio_buttons): enabled active_low pull debounce_ms
== peripheralSettings(recording_indicator): enabled target line(max 27) pcf_pin active_high
== knownKey(gpio_encoders, chip)=0 knownKey(gpio_buttons, chip)=1 knownKey(trigger_output, chip)=1
== model "gpio_pins": free = 4 6 8 9 ... 27
== parseConfigTxt: DPI lines seen = 0 (file has one under [pi4], one under [cm5])
== parseConfigTxt: DPI lines seen = 1 (file has one under [pi5]; the same answer on a Pi 4)

@work/improve 04fe197 (same program)
== expander chip, HDMI Pi: no error
== expander chip, DPI Pi: 1 error, the trigger on header line 7 (correct)
== switch on line 40: no error
== peripheralSettings(gpio_buttons): enabled active_low pull debounce_ms chip poll_ms
== peripheralSettings(recording_indicator): enabled target chip line pcf_pin active_high
== parseConfigTxt: unchanged (0 and 1)
```

## 7. Seen in passing (not this sweep's kind)

| What | Ref @cinemate-port |
| --- | --- |
| `backendMaximumFps` returns `std::nullopt` for every input and voids both parameters | `CC:3426-3434` |
| The Boot Config sensor list has no IMX283, although Core has the family (the engine `f19b245` is older than `c48e693`) | `BCT:162-171` |
| The link-frequency select is disabled on a Pi 5 until the RP1 overclock is on, so a lower rate cannot be chosen either | `WCP:20112-20119` |
| A comment names the owner: "The commands the I2C card shows for Patrik to run." | `HCT:1082` |
| `gpioChipScore` still has two more copies | `src/hardware/TriggerOutput.cpp:195`, `RecordingIndicatorOutput.cpp:191` |
| The stock file loads `dtoverlay=rp1-clk-333mhz` from `[all]`, and the card adds a new one there too. A Pi 4 booting that card reads the line | `tools/boot_config_test.cpp:83`; `BCT:1039-1043` |

## 8. Appendix: the two probe sources

Build: `g++ -std=c++20 -O1 -I <Core>/src -I <Core>/include probe.cpp -o probe`. `<Core>` = `/home/user/Apertar-Core` for `cinemate-port`, `/home/user/wt/core-work` for `work/improve`.

Probe 1 (Boot Config):

```cpp
// Scratch probe (not part of any repo): runs the port's pure BootConfigText.hpp for other boards.
#include "hardware/BootConfigText.hpp"
#include <cstdio>
#include <string>
using namespace apertar::bootconf;

int main()
{
    struct B { const char *name; std::string compat; const char *model; };
    const B boards[] = {
        {"Pi 5", std::string("raspberrypi,5-model-b\0brcm,bcm2712\0", 35), "Raspberry Pi 5 Model B Rev 1.0"},
        {"CM5", std::string("raspberrypi,5-compute-module\0brcm,bcm2712\0", 42), "Raspberry Pi Compute Module 5 Rev 1.0"},
        {"Pi 4", std::string("raspberrypi,4-model-b\0brcm,bcm2711\0", 35), "Raspberry Pi 4 Model B Rev 1.4"},
        {"CM4", std::string("raspberrypi,4-compute-module\0brcm,bcm2711\0", 42), "Raspberry Pi Compute Module 4 Rev 1.1"},
        {"Pi 3B+", std::string("raspberrypi,3-model-b-plus\0brcm,bcm2837\0", 40), "Raspberry Pi 3 Model B Plus Rev 1.3"},
        {"Zero 2 W", std::string("raspberrypi,model-zero-2-w\0brcm,bcm2837\0", 40), "Raspberry Pi Zero 2 W Rev 1.0"},
        {"Pi 2 (2836)", std::string("raspberrypi,2-model-b\0brcm,bcm2836\0", 35), "Raspberry Pi 2 Model B Rev 1.1"},
        {"Zero W (2835)", std::string("raspberrypi,model-zero-w\0brcm,bcm2835\0", 38), "Raspberry Pi Zero W Rev 1.1"},
    };
    const char *filters[] = {"pi5", "cm5", "pi4", "cm4", "pi3", "pi3+", "pi02", "pi0", "pi0w", "pi2", "all"};
    std::printf("%-14s %-7s det  ports      ", "board", "family");
    for (const char *f : filters) std::printf("[%s] ", f);
    std::printf("\n");
    for (const auto &b : boards) {
        const Board board = boardFromDeviceTree(b.compat, b.model);
        std::string ports;
        for (const auto &p : boardPorts(board)) ports += p + " ";
        std::printf("%-14s %-7s %-4s %-10s ", b.name, board.family.c_str(), board.detected ? "yes" : "NO", ports.c_str());
        for (const char *f : filters) std::printf("%*s ", int(std::string(f).size()) + 2, filterApplies(f, board) ? "y" : "-");
        std::printf("\n");
    }
    // link options per family
    for (const auto &b : boards) {
        const Board board = boardFromDeviceTree(b.compat, b.model);
        for (const char *key : {"imx477", "imx585"}) {
            const Sensor *s = findSensor(key);
            std::string hz;
            for (const auto &o : linkOptionsFor(*s, board)) hz += std::to_string(o.hz / 1000000) + (o.overRp1Spec ? "*" : "") + " ";
            std::printf("link options %-14s %-7s: %s\n", b.name, key, hz.c_str());
        }
    }
    // Zero 2 W with a [pi3] section: where does the card put a new sensor line, and does read-back accept it?
    const std::string text =
        "[pi3]\n#dtoverlay=imx477\n\n[pi02]\ndtparam=audio=on\n\n[all]\ncamera_auto_detect=0\ndtoverlay=vc4-kms-v3d\n";
    const Board z2 = boardFromDeviceTree(std::string("raspberrypi,model-zero-2-w\0brcm,bcm2837\0", 40), "Raspberry Pi Zero 2 W Rev 1.0");
    Request r;
    r.sensors["cam1"] = "imx477";
    const ApplyResult res = applyRequest(text, r, Facts{z2, std::nullopt});
    std::printf("\nZero 2 W, file with [pi3]: ok=%d error='%s'\n--- text after ---\n%s--- end ---\n", res.ok, res.error.c_str(), res.text.c_str());
    // include line
    const std::string inc = "[pi5]\ninclude camera-selection.txt\n#dtoverlay=imx585,cam0\n\n[all]\ncamera_auto_detect=0\n";
    const Board p5 = boardFromDeviceTree(std::string("raspberrypi,5-model-b\0brcm,bcm2712\0", 35), "Raspberry Pi 5 Model B Rev 1.0");
    const State st = readState(parseDocument(inc, p5), p5);
    std::printf("\nPi 5, file with 'include camera-selection.txt': cam0=%s cam1=%s warnings=%zu managed=%zu\n",
                st.cameras.at("cam0").sensor.c_str(), st.cameras.at("cam1").sensor.c_str(), st.warnings.size(), st.managed.size());
    return 0;
}
```

Probe 2 (hardware file validator and Controls model):

```cpp
// Scratch probe (not part of any repo): the port's hardware-file validator and Controls model with chip= set.
#include "hardware/HardwareConfigText.hpp"
#include "hardware/ControlsModel.hpp"
#include <cstdio>
#include <string>
using namespace apertar::hwconf;

static void show(const char *title, const std::string &text, const Facts &facts)
{
    std::printf("== %s\n", title);
    for (const auto &issue : validate(text, facts))
        std::printf("  %s line %zu [%s] %s\n", issue.error ? "ERROR" : "warn ", issue.line, issue.rule.c_str(), issue.message.c_str());
}

int main()
{
    Facts header;            // a Pi with I2C bus 1, HDMI only
    header.known = true;
    header.buses = {1, 10};
    Facts dpi = header;      // the same Pi with a DPI panel (the upstream default display)
    dpi.buses = {10};
    dpi.dpiLines = {70};

    // Buttons on an I2C expander / microcontroller that the kernel shows as /dev/gpiochip2 (lines 0..15).
    const std::string expander =
        "[gpio_buttons]\nenabled=true\nchip=/dev/gpiochip2\nactive_low=true\npull=up\nd2=capture\nd3=eject\nd5=iso_up\n\n"
        "[recording_indicator]\nenabled=true\ntarget=gpio\ngpiochip=/dev/gpiochip2\nline=7\n\n"
        "[trigger_output]\nenabled=true\ntarget=gpio\ngpiochip=auto\nline=7\n";
    show("expander chip, HDMI Pi (bus 1 exists)", expander, header);
    show("expander chip, DPI Pi (header pins all taken)", expander, dpi);

    // What a save of that file would report as new errors against an empty [gpio_buttons].
    const std::string before = "[gpio_buttons]\nenabled=true\nchip=/dev/gpiochip2\n";
    const auto fresh = newErrors(validate(before, dpi), validate(expander, dpi));
    std::printf("== new errors when saving it on the DPI Pi: %zu (a save with new errors is refused)\n", fresh.size());

    // The reader takes switch pins 0..63, the model 0..27.
    show("switch on line 40", "[gpio_buttons]\nenabled=true\n\n[gpio_switches]\nenabled=true\nswitch0_pins=40\nswitch0_on=zebra\nswitch0_off=zebra\n", header);

    // What the card offers.
    const Document doc = parse(expander);
    std::printf("== peripheralSettings(gpio_buttons): ");
    for (const auto &spec : peripheralSettings("gpio_buttons")) std::printf("%s ", spec.key);
    std::printf("\n== peripheralSettings(recording_indicator): ");
    for (const auto &spec : peripheralSettings("recording_indicator")) std::printf("%s(max %d) ", spec.key, spec.max);
    std::printf("\n== knownKey(gpio_encoders, chip)=%d knownKey(gpio_buttons, chip)=%d knownKey(trigger_output, chip)=%d\n",
                knownKey("gpio_encoders", "chip"), knownKey("gpio_buttons", "chip"), knownKey("trigger_output", "chip"));
    const std::string model = modelJson(doc);
    const auto at = model.find("\"gpio_pins\"");
    std::printf("== model %s\n", model.substr(at).c_str());

    // config.txt filters as the Controls validator reads them.
    const std::string cfg = "[pi4]\ndtoverlay=vc4-kms-dpi-hyperpixel4sq\n[cm5]\ndtoverlay=vc4-kms-DPI-4inch\n[pi5]\n#x\n[all]\ndtparam=audio=on\n";
    std::printf("== parseConfigTxt: DPI lines seen = %zu (file has one under [pi4], one under [cm5])\n", parseConfigTxt(cfg).dpiLines.size());
    const std::string cfg5 = "[pi5]\ndtoverlay=vc4-kms-dpi-hyperpixel4sq\n[all]\ndtparam=audio=on\n";
    std::printf("== parseConfigTxt: DPI lines seen = %zu (file has one under [pi5]; the same answer on a Pi 4)\n", parseConfigTxt(cfg5).dpiLines.size());
    return 0;
}
```

## Skeptic

Re-read on both sides at Core `cinemate-port` `01f170c`, UI `7ea9afc`, `upstream-1.6.0`, imx283 `68b7dc9`. Every port line the findings cite was opened.

| Id | Verdict | Why |
| --- | --- | --- |
| 1 | holds, major | `CM:258-263` (no `chip`, comment "chip stay text-only"), `CM:268` (line max 27), `CM:381` (free 4..27), `HCT:697` (pins 0..27), `HCT:858-872` (claims keyed by line only, `gpio_dpi` for every line <= 27) all read. Upstream reader takes `chip`/`gpiochip`/`gpio_chip` and lines 0..63 (`GpioInput.cpp:233`, `:431`; `TriggerOutput.cpp:311` @upstream-1.6.0). WebUI save path passes no `force` (`App:8642-8644`), store refuses new errors (`HardwareConfigStore.cpp:337`). `04fe197` is not an ancestor of `cinemate-port` (checked with `merge-base --is-ancestor`); it sits on `origin/claude/awesome-pasteur-qzsiow` and `work/improve` |
| 2 | holds, major | UI `DisplayConfigBridge.cpp:11-12`, `:289-294`, `:354-357` and Core template `App:5089-5098` read. Upstream `720/720/square/false` and `ensureDefaultHardwareConfigFile()` (UI `DisplayConfigBridge.cpp:41`, `:587` @upstream-1.6.0); the port has no file writer. `window->hide()` at UI `main.cpp:432-433` |
| 3 | holds, major, **probable** | `lineFrom` returns a line without key when there is no `=` (`BCT:288-289`), so `include` is invisible. The stock image's `include` line is inferred from the fixture comment (`tools/boot_config_test.cpp:56`); no stock config.txt here. Upstream itself never writes `camera-selection.txt`; it only reads it (UI `DeviceInfoBridge.cpp:215`) |
| 4 | corrected: major -> minor | Pi 2 (BCM2836) and Zero W (BCM2835) rows dropped: those SoCs cannot run an aarch64 image and upstream ships aarch64 only (UI `mesa-minimal/lib/aarch64-linux-gnu`). "Unknown = Pi 5" then only hits a non-Pi dev host, where the code comment says so on purpose (`BCT:79`). Upstream is not "one list in one header": the exact-match list is copied in two headers (`RecordingCapabilities.hpp:18-35`, `DefaultTuningSelection.hpp:18-31` @upstream-1.6.0); the port adds a third, by substring. Zero 2 W: `[pi02]` applies in the port; `[pi3]` also applies (`BCT:114`), `[pi0]` does not. Which firmware filters match a Zero 2 W is **unconfirmed** here (`[pi0w]` claim removed: no source). Only bites with a `[pi3]` section in the file; the stock layout edits `[all]` |
| 5 | holds, minor | `HCT:1037`, `:1051` read; used at `App:4976`. Board-aware reader exists (`BCT:540-553`, `displayLines`). New ground (upstream has no validator) |
| 6 | holds, minor | `BCT:186` caps only `family == "pi4"`. Pi 3 / Zero 2 W get the full Pi 5 list. Driver behaviour at an unknown rate stays **probable** |
| 7 | corrected: major -> minor | Code read (`CC:1334-1338`, `CC:4365`, `CC:4718-4720`, `StoragePreroll.hpp:92-99`, `App:11150-11157`). No defect is shown on any board; the finding is an untested risk with a switch back for each part. It stays as the test plan T1/T2 |
| 8 | holds, minor | Upstream `rawPool_.clear()` at stop (`CC:3486` @upstream-1.6.0); port `trimRawPoolToIdle` keeps `idleRawPoolSize()` (`CC:4935-4945`, `:5547-5550`) |
| 9 | holds, minor | Probe `ladderStatesLocked` (`CC:10838-10843`) goes through `sanitizeSettingsForSensor` and compares fps, bits, Clear HDR, not compression, so a clamped compression reads usable. `fillRungExtrasLocked` `CC:10949-10958`. `ModeLadder.hpp:41-44` default `lossless_jpeg` |
| 10 | holds, minor (opt-in) | `scripts/apertar-media-tune:68-71`, `:87-90` |
| 11 | corrected: minor -> nit | Helper check `scripts/apertar-boot-config:51-54` and no fallback (`App:3589-3591`) read; fan block has no header (`App:3425-3440`). But the stock Raspberry Pi OS and Apertar files carry `[all]`, so only a hand-written file without any of the three headers is hit |
| 12 | holds, nit | `scripts/start-apertar-core.sh:28`, `:35-37` |
| 13 | holds, minor | `DngTags.hpp:307-312`, `DngFrameReader.hpp:67-82` read. The clip writer stores 8-bit as `BitsPerSample=8` (`src/cdng/CdngEncoder.cpp:149-152`, `:1206-1209`), so the viewer refuses a file Core wrote |
| 14 | holds, minor | `CC:8295-8296` drops upstream's IMX585 12-bit crop auto-config fallback (`CC:5993-5996` @upstream-1.6.0); `backendMaximumFps` empty (`CC:3426-3434`). Fix is docs and board runs |
| 15 | holds, minor (camera review owns it) | `Types.hpp:139` `previewTdn = false`; `CC:7306-7318`; ProRes ISP tuning from `activePath` (`CC:7412`). Effect on recorded H.264/ProRes stays **probable** |
| 16 | holds, nit | `imx283.c:10` `<linux/unaligned.h>` against `<asm/unaligned.h>` on `origin/master`; README states 6.12 |

Nothing new of this sweep's kind found.

## Final findings

### X-board-support-1: the Controls page models only the 40-pin header; `chip=` is gone from the card

- Category: removed-upstream-behaviour. Severity: major. Deliberate: yes for the card (`c140c4f`), no for the checks. Effort: S (cherry-pick `04fe197`).
- Where: `src/hardware/ControlsModel.hpp:258-271`, `:381`; `src/hardware/HardwareConfigText.hpp:694-700`, `:858-872`; `src/ApertarCoreApp.cpp:11987-11989`; `src/web/WebControlPage.cpp:17197-17200`, `:17260-17264`; UI `qml/ControlsWarning.qml`.
- Detail: upstream reads `chip`/`gpiochip`/`gpio_chip` in `[gpio_buttons]`, `[gpio_encoders]`, `[trigger_output]`, `[recording_indicator]`, default `auto`, lines 0..63 (`GpioInput.cpp:233`, `:431-432`; `TriggerOutput.cpp:311`; `RecordingIndicatorOutput.cpp:319` @upstream-1.6.0). The port's card offers no `chip`, caps lines at 27, lists free pins 4..27, keys line claims by number only and applies `gpio_i2c1`/`gpio_dpi` to every line <= 27 whatever the chip. The WebUI save sends no `force` (`App:8642-8644`), the store refuses new errors (`HardwareConfigStore.cpp:337`). A file upstream accepts (buttons on `/dev/gpiochip2`) is "Not saved: 5 new errors" on a DPI rig (host probe). The fix `04fe197` is on `work/improve` and `origin/claude/awesome-pasteur-qzsiow`, not on `cinemate-port`.
- Fix: merge `04fe197`: `chip` and `poll_ms` rows back in `peripheralSettings`, claims keyed by chip and line, `gpio_i2c1`/`gpio_dpi` only for the header chip, switch pins 0..63, free pins per chip, status reads the chip the reader uses.

### X-board-support-2: display defaults are the owner's HDMI rig

- Category: stock-behaviour-change. Severity: major. Deliberate: yes (`7af9f13`, UI `7c41a27`, `c9d841f`). Effort: S.
- Where: UI `src/DisplayConfigBridge.cpp:11-12`, `:289-294`, `:354-357`; UI `src/DisplayConfigBridge.hpp:52-59`; Core `src/ApertarCoreApp.cpp:5089-5098`.
- Detail: upstream falls back to 720x720, `square`, `hdmi_external_only=false` and writes a default file when none exists (UI `DisplayConfigBridge.cpp:14-15`, `:41`, `:577-587`, `:646-649`; Core template `App:4329` @upstream-1.6.0). The port falls back to 1920x1080, `landscape_large`, `true`, writes no file, and Core's template says `true`. UI `main.cpp:432-433` hides the window when true: a DPI-panel rig without the key has no touch UI.
- Fix: restore upstream's four defaults and the default-file writer; the owner's values go in his own `apertar-hardware.conf`.

### X-board-support-3: the Boot Config card does not see `include camera-selection.txt`

- Category: bug. Severity: major (**probable**: stock file not in this container). Deliberate: unknown. Effort: S warning, M reading the file.
- Where: `src/hardware/BootConfigText.hpp:270-307`, `:616-622`; `tools/boot_config_test.cpp:56`.
- Detail: a line without `=` has no key (`BCT:288-289`), so `include` is ignored. The fixture keeps the image's comment about the `include camera-selection.txt` line. Upstream UI treats that file as the sensor truth (UI `DeviceInfoBridge.cpp:213-215` @upstream-1.6.0). On such a file the card shows no sensor, adds a second `dtoverlay=` next to the included one, and "None connected" changes nothing.
- Fix: in `readState`, an applying uncommented `include` sets a warning and makes the camera rows read-only (same shape as `state.problem`/`editable`). Settle with `grep -n '^include' /boot/firmware/config.txt` on a fresh Apertar-Beta 1.6.0 image.

### X-board-support-4: a third board detector, by substring, with its own filter rules

- Category: mismatch. Severity: minor. Deliberate: unknown (from Cinemate `boot_config.py:173-175`). Effort: S.
- Where: `src/hardware/BootConfigText.hpp:76-122`; `src/ApertarCoreApp.cpp:3653-3657`.
- Detail: upstream tells SoCs apart by exact `brcm,bcm27xx` strings in `RecordingCapabilities.hpp:18-35` and `DefaultTuningSelection.hpp:18-31` and does not guess an unknown platform (`DefaultTuningSelection.hpp:67`). The port adds a substring detector with another list (adds `bcm2710`, lacks `bcm2836`/`bcm2835`) and reads "no match" as Pi 5. On real Apertar boards (aarch64 only) the unknown case is a dev host, which the comment intends. Zero 2 W: the port applies `[pi3]` and `[pi02]`, not `[pi0]`; if the firmware does not apply `[pi3]` to a Zero 2 W (**unconfirmed**, test T5), a file with a `[pi3]` section gets the sensor line where the firmware ignores it, and the read-back agrees. Stock layout (no `[pi3]`) edits `[all]` and is fine.
- Fix: derive `family` from upstream's exact SoC strings (one inline helper beside `recordingCapabilitiesFromCompatible`, used by the card). Keep the Pi 5 reading for a host without a device tree only. Fix the Zero 2 W filters after T5.

### X-board-support-5: the Controls validator reads config.txt as a Pi 5 would

- Category: pi-compat. Severity: minor. Effort: S.
- Where: `src/hardware/HardwareConfigText.hpp:1037-1051`; `src/ApertarCoreApp.cpp:4976`.
- Detail: `applies = filter == "[all]" || filter == "[pi5]"`. DPI overlays under `[pi4]` or `[cm5]` are not seen; under `[pi5]` they are seen on every board (h). On a Pi 4 that is a missing DPI warning or false `gpio_dpi` errors that refuse a save. The Boot Config reader already knows the board (`BCT:540-553`, `displayLines`). New ground (no upstream validator).
- Fix: `hardwareConfigFacts()` takes `bootconf::readState(bootconf::parseDocument(text, board), board).displayLines`; drop the filter code from `parseConfigTxt`.

### X-board-support-6: the link-frequency cap exists for family "pi4" only

- Category: pi-compat. Severity: minor. Effort: S.
- Where: `src/hardware/BootConfigText.hpp:147`, `:186`, `:198-205`.
- Detail: Pi 3 and Zero 2 W get the Pi 5 list (IMX477 up to 972 MHz) with "fps at 4K" and "over RP1 spec" labels on boards without RP1. **probable**: a rate the driver does not accept means no camera after reboot.
- Fix: cap for every family that is not `pi5`; rename `pi4MaxHz`; drop the fps and RP1 text off Pi 5.

### X-board-support-7: the raw write path changed for every board and was run on one

- Category: pi-compat. Severity: minor (untested risk, no defect shown). Deliberate: yes. Effort: M board session, S fallback.
- Where: `src/camera/CameraController.cpp:1334-1338`, `:1458-1470`, `:4365-4369`, `:4714-4727`, `:8730-8736`; `src/util/StoragePreroll.hpp:92-99`; `src/ApertarCoreApp.cpp:11150-11157`.
- Detail: one request per raw buffer, copy worker with `dropped_copy_slot`, per-DNG `sync_file_range` and 1 s fsync, and a storage pre-roll at start, all on by default. Upstream: three requests for four buffers, copy on libcamera's thread, no sync, no pre-roll, and per-family defaults where memory matters (`CC:1126`, `CC:6001-6004` @upstream-1.6.0). Each has an env or config switch. Nobody ran it on a Pi 4 or CM4.
- Fix: run T1/T2 on a Pi 4. Without a board before merge: where `recordingCapabilities().hardwareH264` is true, default pre-roll and per-file sync off, one line each in the functions that read the knobs, the shape of `CC:1126` @upstream-1.6.0.

### X-board-support-8: the raw copy pool is kept between takes

- Category: pi-compat. Severity: minor. Deliberate: yes (`db17860`). Effort: S.
- Where: `src/camera/CameraController.cpp:4935-4945`, `:5547-5550`.
- Detail: upstream clears `rawPool_` at stop (`CC:3486` @upstream-1.6.0). The port keeps `min(queue, max(workers+2, 4))` copies, about 100-110 MB idle at 4K, until the session is reconfigured. On a 1-2 GB Pi 4 this memory stays held between takes.
- Fix: free the idle pool after 30 s idle (the rule of `src/playback/DecodeSlots.hpp:9-13`), or keep it only when `MemTotal` allows, read as in `BufferBudget.hpp:83-95`.

### X-board-support-9: the new cards do not follow `recording_capabilities`

- Category: mismatch. Severity: minor. Effort: S.
- Where: `src/camera/CameraController.cpp:10838-10843`, `:10949-10958`; `src/camera/ModeLadder.hpp:41-44`; `src/web/WebControlPage.cpp:8155-8166`.
- Detail: upstream hides and disables options the board cannot do (`WCP:9524-9529` @upstream-1.6.0). The ladder probe goes through the sanitiser, which clamps the compression, and compares fps/bits/Clear HDR only, so on a board without `rawCompression` every compression reads usable with the uncompressed ceiling; the default for SDR is `lossless_jpeg`. Pi 4 shows "Lossless JPEG" and records uncompressed with no sentence. Pi 3/Zero 2 W see raw-only cards.
- Fix: `ceilingBy[i] = 0` for `i >= 1` when `!recordingCapabilities().rawCompression`; caller picks `none` as default on such a board; hide raw-only cards with `recordingFeatureSupported` / `raw_recording === false` (`WCP:9488-9496`).

### X-board-support-10: the media tuning helper sets dirty-page limits in absolute bytes

- Category: pi-compat. Severity: minor (opt-in). Effort: S.
- Where: `scripts/apertar-media-tune:68-71`, `:87-90`.
- Detail: `dirty_bytes` 256 MiB to 1 GiB regardless of RAM; on a 512 MB-1 GB board that is half of RAM or more. Not measured.
- Fix: cap both values by `MemTotal` in the script (a quarter, background half of that).

### X-board-support-11: the root helper wants `[pi5]`, `[pi4]` or `[all]`, and the fan mode goes through it

- Category: stock-behaviour-change. Severity: nit. Effort: S.
- Where: `scripts/apertar-boot-config:51-54`; `src/ApertarCoreApp.cpp:3589-3591`, `:3620-3649`.
- Detail: upstream installs the fan text with `sudo -n install`, no content rule (`App:3127-3165` @upstream-1.6.0). The port's helper refuses a file without those headers and Core does not fall back. Stock files carry `[all]`, so only a hand-written file is hit.
- Fix: accept any `[section]` header or drop the header rule; Core's `textProblem` already checks size and NUL.

### X-board-support-12: `APERTAR_RT=1` pins to cores 1 to 3

- Category: pi-compat. Severity: nit (opt-in). Effort: S.
- Where: `scripts/start-apertar-core.sh:28`, `:35-37`.
- Detail: with fewer CPUs online `taskset` fails at `exec` and Core does not start.
- Fix: test `taskset -c "$RT_CPUS" /bin/true` first, as `chrt` is tested at `:29`.

### X-board-support-13: the clip viewer refuses 8-bit DNG

- Category: bug. Severity: minor. Effort: S.
- Where: `src/playback/DngTags.hpp:307-312`; `src/playback/DngFrameReader.hpp:67-82`.
- Detail: only 10/12/16 bits accepted; Core's own writer stores 8-bit clips as `BitsPerSample=8` (`src/cdng/CdngEncoder.cpp:149-152`, `:1206-1209`). IMX477 8-bit clips cannot be opened in the WebUI viewer.
- Fix: accept `bits == 8`: one byte per sample in the row size and one branch in the row loop.

### X-board-support-14: sensor paths that were run on a CM5 only

- Category: pi-compat. Severity: minor. Deliberate: yes for scope (driver `APERTAR.md:3-4`). Effort: S (docs) + board runs.
- Where: `src/camera/Imx585Modes.hpp:40-98`; `src/camera/CameraController.cpp:8295-8296`, `:1334-1338`, `:7119-7239`, `:3426-3434`; `src/camera/FramePhaseLock.hpp:9-25`.
- Detail: the IMX585 12-bit crop auto-config fallback is gone (upstream `CC:5993-5996` @upstream-1.6.0); mode tables, Clear HDR 8 x 16.9 MB buffers, start-up sensor probe and phase lock were only run on PiSP. Upstream README lists the IMX585 for Pi 3/4 (`README.md:143`).
- Fix: no code; state the tested scope in Core's README and run T3-T6, T8.

### X-board-support-15: preview temporal denoise is off by default

- Category: stock-behaviour-change. Severity: minor (owned by the camera review). Deliberate: yes (`e625c68`). Effort: S.
- Where: `include/apertar/core/Types.hpp:139`; `src/camera/CameraController.cpp:7306-7318`, `:7412`.
- Detail: the tdn-stripped tuning copy is loaded for every format; on Pi 5-class, H.264 and ProRes record the ISP output, so they lose temporal denoise by default (**probable**, no frame compared). VC4: no effect.
- Fix: `previewTdn = true` by default, or strip only when a raw format records.

### X-board-support-16: drivers need kernel 6.12

- Category: pi-compat. Severity: nit. Effort: S.
- Where: imx283 `imx283.c:10`, `README.md:9`.
- Detail: `<linux/unaligned.h>` replaces `<asm/unaligned.h>` (`origin/master`); a 6.6 image cannot build the module. The Apertar imx585 base already uses it.
- Fix: none if 6.12 is the image floor; say it once in Core's README.
