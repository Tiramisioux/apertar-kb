# Inventory: Boot-config (stage 1, no judgement)

Refs: port = `cinemate-port` Core `01f170c`, UI `7ea9afc`; upstream = `upstream-1.6.0`. Read completely: BootConfigText.hpp (1355), apertar-boot-config (71), sudoers (4), boot_config_helper_test.sh (33), README section (l.179-211), Core App regions. boot_config_test.cpp (427): read head, test index, ran it. Both host tests pass here (`boot_config_test`, `boot_config_helper_test.sh`: PASSED 0 failed).

## 1. Commits (Core), from `git log origin/main..cinemate-port`

| sha | author | what | tested per message / fork-log |
| --- | --- | --- | --- |
| f19b245 | Claude | engine `BootConfigText.hpp` (1228 lines then) + `boot_config_test.cpp` | host test, dev Pi's file as fixture |
| dda1713 | Claude | helper `scripts/apertar-boot-config`, `config/apertar-boot-config.sudoers`, `tools/boot_config_helper_test.sh` | host test on scratch copy |
| 2955ef8 | Claude | Core: `get/set_boot_config`, `/api/boot-config`, one writer for config.txt (App) | not in my scope list but is the App side |
| 8a56545, afa00e8 | Claude | WebUI Boot Config card, DRM note wrap | card driven in Chromium against a mock server using the real engine |
| 496817f | Claude | README section | n/a |
| 4581a69 | Patrik | merge of PR #1 (`claude/cool-volta-y7fiw7`) | handoff-boot-config.md: "never run on a Pi" |
| 3b87d99 | Patrik | Edit file: `text` field, `lineChanges`, `textProblem`, `displayDiffers` | "desk only (73 checks)" |
| b3e7f52 | Patrik | link rate kept when sensor flips to its twin (colour/mono) | not read in detail |
| 2a4266e | Patrik | `state.managed`, italic managed lines in the editor | "desk only (75 checks)" |

Hint said three Claude commits; `git log` shows six in this area (f19b245, dda1713, 2955ef8, 8a56545, afa00e8, 496817f). Commit trailers read "Co-Authored-By: Claude Opus 5.5".
UI: `41ff827` (Patrik): fan mode through Core `set_fan_mode`. Tested: "pi (apertar.local) build only"; fork-log: "builds on the Pi, not tried by hand".
fork-log.md l.138: whole feature "Not yet run on the camera". handoff-boot-config.md step 1 (Pi verification: install helper, Save Only I2S, fan mode, one Save & Reboot) is unchecked in the KB. Pi verification of fan-mode-through-helper: unconfirmed.

## 2. Features (operator-visible)

| feature | operator gets | files |
| --- | --- | --- |
| Boot Config card (System pane) | choose sensor per connector (cam0, cam1), IMX477/IMX585 link frequency, RP1 clock overlay, I2C/I2S/SPI/audio, display (HDMI / Waveshare 4" DPI / Hyperpixel 4" DPI) and save to `/boot/firmware/config.txt` | engine, App, WCP |
| Review before save | dry run shows the changed lines (diff box), "Save & Reboot" / "Save Only" / "Back" | App `bootConfigSet`, WCP l.20241-20305 |
| Read-back refusal | a save that would not do what was asked is refused, naming the deciding line | `applyRequest` end (hpp:1090-1130) |
| Display guard | display change needs `confirm_display` tick (DPI holds GPIO 0-27, I2C bus 1) | App:3826-3829 |
| Stale-file guard | revision (FNV-1a 64) in `X-Apertar-Revision` header or `revision` field; 409 `stale`; 409 `old_page` for a browser POST with no revision | App:3790-3799, 9170-9198 |
| Backup | previous file kept as `config.txt.apertar.bak` (helper, direct path, and sudo-install fallback) | helper, App:3534 |
| Reboot wait | after Save & Reboot: `restart_system`, polls `/api/buffer` up to 240 s, reports back / never-down / timeout | WCP:20356-20400 |
| View file, Download, Upload | whole file as text, download, upload a config.txt and read it with this Pi's rules (`/api/boot-config/parse`, not written) | WCP, App:9200 |
| Edit file / Use This Text | edit whole file as text; card choices applied on top; diff vs file on disk (3b87d99) | App:3802-3816, hpp `lineChanges` |
| Managed-line marks | italic gutter numbers for lines the card or fan mode may rewrite; legend (2a4266e) | hpp `state.managed`, WCP css l.3107 |
| Fan mode writer shared | fan mode now writes through the same writer under the same mutex; fan block stays byte-for-byte | App `applyFanMode` |
| UI fan mode via Core | touch UI fan mode sends `set_fan_mode` to Core, own block builder and write removed | UI 41ff827 |
| DPI line note on Controls | Controls page names the config.txt line that loads a DPI panel (WCP:18209) | `facts.dpiLines` App:4976 (belongs to Controls unit; uses `bootConfigPath()`) |

## 3. Interfaces added or changed

| kind | name | detail | where |
| --- | --- | --- | --- |
| socket cmd | `get_boot_config` | reply `boot_config` object: path, readable, revision, helper (bool), backup_path, state, drm[], text | App:14586; listed in `list_commands` reply App:12930 |
| socket cmd | `set_boot_config` | fields `cam0_sensor`, `cam1_sensor`, `cam0_link_frequency`, `cam1_link_frequency` (Hz, "" or "null"), `i2c`, `i2s`, `spi`, `audio`, `rp1` (bool strings), `display`, `dry_run`, `confirm_display`, `revision`, `text` | App:14589, `bootConfigRequestFrom` 3722 |
| set reply | | `written`, `dry_run`, `changes[]`, `display_changed`, `text`, `state`, `revision`, `via`, `reboot_required`, `drm`; error `code`: `invalid`, `unreadable`, `stale`, `old_page`, `refused`, `confirm_display`, `permission`, `write_failed`. Nested objects/arrays in reply (not flat scalars) | App:3817-3840 |
| HTTP | `GET /api/boot-config` | same body as `get_boot_config` | App:9161 |
| HTTP | `POST /api/boot-config` | JSON body; handler injects `"cmd":"set_boot_config"` by string insert and feeds `parseControlCommand`; HTTP status 200/400/403/409/500 from `BootConfigReply.status` | App:9170-9198 |
| HTTP | `POST /api/boot-config/parse` | text body, max 64 KiB, no NUL; returns `state`, no write | App:9200 |
| HTTP header | `X-Apertar-Revision`, `Origin` presence | `Origin` present = "browser" (decides `old_page`) | App:9190-9194 |
| existing cmd touched | `set_fan_mode` | body unchanged; `applyFanMode` now takes `bootConfigMutex`, writes via `writeBootConfigText`; error text "needs sudo permission" kept | App:3622-3649 |
| state field | none added to `get_state` | boot config is on-demand only | grep, confirmed |
| event | none | | |
| config key | none | no `.conf` key; board and overlay facts read live | confirmed |
| env var | `APERTAR_BOOT_CONFIG` | path override (dev machine, tests); helper only writes real path; direct write allowed to the copy | App:3505-3510 |
| files on disk | `/usr/local/libexec/apertar-boot-config` (root, 0755) | installed by hand from `scripts/` | README l.200 |
| | `/etc/sudoers.d/apertar-boot-config` (0440) | from `config/apertar-boot-config.sudoers` | README l.201 |
| | `/boot/firmware/config.txt.apertar.bak` | backup | helper |
| | `/boot/firmware/.config.txt.XXXXXX` | temp beside target (helper) | helper l.40 |
| | `<tmp>/apertar-boot-config-<pid>.txt` | staged text for helper / install fallback; removed by RAII `RemoveStaged` | App:3572-3578 |
| | `<dir>/.config.txt.apertar-<pid>.tmp` | direct-write temp | App:3551 |
| read-only sources | `/proc/device-tree/compatible`, `/proc/device-tree/model`, `<config dir>/overlays/*.dtbo`, `/sys/class/drm/card*-*/{status,modes}` | board, overlay presence, DPI connector info | App:3653-3687 |
| UI element (WebUI) | card `#settingsBootConfigCard` in System pane, after the Fan Mode card (WCP:5859-5949) | cam0/cam1 selects + link selects, RP1 pills, display select, I2C/I2S/SPI/Audio pills, buttons Reload, View file, Edit file, Download, Upload, Save & Reboot (+ Save Only, Back in review), Use This Text, Close; pill `#bootConfigStatePill`; diff, file view, editor with gutter | WCP:5859-5949 (HTML), 19868-20600 (JS, about 730 lines), css 3107-3135 and others |
| UI element (Qt) | none new | UI only loses code | UI 41ff827 |

Sizes: WCP has 118 lines matching `bootConfig/BootConfig`; whole WCP diff has 295 hunks across all units (not only this unit).

## 4. Original code regions modified

| region | where | kind | change |
| --- | --- | --- | --- |
| `kBootConfigPath` constant | App:3228 @port (= :2845 @upstream) | unchanged, now a default only | still the literal path, wrapped by `bootConfigPath()` |
| `currentFanMode()` | App:3613 (@up 3118) | extended in place | `readTextFileRaw(kBootConfigPath)` -> `bootConfigPath()` |
| `applyFanMode()` | App:3622 (@up 3127) | rewritten tail | adds `std::lock_guard` on `bootConfigMutex()`; temp file + `sudo -n install` + error mapping replaced by `writeBootConfigText(...)`. Fan block builders (`fanModeBlock`, `stripManagedFanBlock`, `detectManagedFanMode`, `kFanBlock*`) untouched. Upstream wrote `apertar-fan-mode-<pid>.tmp`, `sudo -n install -m 644 tmp dest`, no backup, no lock |
| `hardwareConfigFacts()` | App:4976 | extended | `facts.dpiLines` from `hwconf::parseConfigTxt(readTextFileRaw(bootConfigPath()))` (Controls unit; shares path function) |
| `#include "hardware/BootConfigText.hpp"` | App:15 | added | |
| `list_commands` reply | App:12930 | extended | adds `get_boot_config`, `set_boot_config` |
| `handleCommand` chain | App:14586-14591 | extended in place | two `if (command.name == ...)` blocks, placed before `set_fan_mode`; each one-liner delegating |
| HTTP routes in `handleWebRequest`-like function | App:9161-9215 | extended in place | three route blocks, body-rewriting hack for `POST /api/boot-config` |
| UI `SystemActionBridge::applyFanMode` | UI SystemActionBridge.cpp | rewritten | removes `fanModeBlock`, `stripManagedFanBlock`, `QTemporaryFile` write and `invokePrivilegedCommand("install", ...)`; adds `coreFanModeCommand` (sync `QLocalSocket`, id 42002, 8 s timeout, "same pattern as MediaStatusBridge"). `detectManagedFanMode`, `refreshFanMode`, `kBootConfigPath` read stay (UI still reads config.txt itself to show the current fan mode) |
| `README.md` | l.179-211 | added section | no change to upstream text |

## 5. New abstractions

| name | purpose | files | upstream equivalent | used by |
| --- | --- | --- | --- | --- |
| `apertar::bootconf` header-only engine | parse config.txt to lines/sections, board filters, state, edit by comment/uncomment/param change, read back, line diff, JSON | `src/hardware/BootConfigText.hpp` (1355 lines; `Board`, `Sensor`/`LinkOption` tables, `Display`, `Toggle`, `Line`, `Document`, `Overlay`, `State`, `Request`, `Facts`, `Change`, `ApplyResult`, `detail::Editor`) | no config.txt editor. Upstream has no `HardwareConfigText.hpp` (confirmed by ls). Fan block: string find/strip in App only | App only |
| engine emits its own JSON | `jsonString`, `stateJson`, `changesJson` hand-built strings inside the header | same | App has `escapeJson` + `okReply` string concat | App |
| `bootConfigMutex()` | one writer at a time (fan mode + card) | App:3512 | none (upstream had no lock) | `applyFanMode`, `bootConfigGet`, `bootConfigSet` |
| `writeBootConfigText()` | three-step writer: direct write (access W_OK) -> root helper via `sudo -n helper < staged` -> `sudo -n install` fallback; `how` = direct/helper/install | App:3533-3611 | upstream `sudo -n install` in `applyFanMode`; upstream root helpers called as `sudo -n /usr/local/libexec/<name> <arg>` with `/usr/bin/timeout` (App@up:1544, :1549) | fan mode, card |
| `fsyncPath()` | fsync a path | App:3516 | none seen | writer |
| `bootConfigFacts()`, `drmConnectorsJson()`, `bootConfigJson()`, `bootConfigRequestFrom()`, `bootConfigGet()`, `bootConfigSet()`, `BootConfigReply{status, body}`, `boolFieldValue()` | request/response plumbing, in App | App:3651-3846 (about 195 lines) | handleCommand returns a string; no struct with HTTP status | commands + routes |
| root helper `scripts/apertar-boot-config` | /bin/sh; stdin to config.txt; refuses args, empty, >64 KiB, NUL, no `[pi5]/[pi4]/[all]`; backup; mktemp + sync + `mv -f` | scripts/ | `/usr/local/libexec/apertar-standby-usb`, `apertar-standby-low-power` (sudoers `pi ALL=(root) NOPASSWD: ... on, off` in `ui-upstream/systemd/*.sudoers`). Upstream helper style: argument words pinned in sudoers. Port rule pins "" (no args). Sudoers file lives in `config/` (Core) not `systemd/` | `writeBootConfigText` |
| sudoers `config/apertar-boot-config.sudoers` | pins helper, no args | config/ | `ui-upstream/systemd/apertar-standby-*.sudoers`. Core upstream `config/` holds only `apertar-core-capture-priority.conf` | install by hand |
| host tests | `tools/boot_config_test.cpp` (76 `check(` lines, per commit msgs 75), `tools/boot_config_helper_test.sh` (10 checks) | tools/ | upstream Core has no tests and no `tools/` tests. Not wired in CMake; run with plain g++ | dev |
| Board model in engine | `Board{family,model,computeModule,detected}`, `filterApplies` for pi5/cm5/pi500/pi4/cm4/cm4s/pi400/pi3/pi3+/pi02/cm3 | hpp:77-125 | none | engine |

## 6. Upstream removed, narrowed or hidden

| what | where | effect |
| --- | --- | --- |
| UI's own fan-block writer | UI SystemActionBridge (41ff827) | UI no longer writes config.txt; no UI fallback if Core socket down ("Connect to Apertar Core before changing the fan mode."). Upstream UI wrote via `invokePrivilegedCommand` without Core |
| Core fan mode write path | App `applyFanMode` | `sudo -n install` is now third fallback; still present. Backup `config.txt.apertar.bak` now written for fan changes too (direct and helper paths; fallback runs `sudo -n install` copy of the old file, errors ignored) |
| fan mode error text on denial | | same string ("Changing the fan mode needs sudo permission.") only when nothing was allowed; if the helper exists and ran but failed, its stderr text is returned instead |
| anything else | | nothing removed from upstream UI/WCP; Boot Config card added next to the Fan Mode card |

## 7. Board and environment assumptions

| assumption | where | detail |
| --- | --- | --- |
| path `/boot/firmware/config.txt`, FAT boot partition, Bookworm layout | App:3228, helper `DEST`, hpp header | helper notes `chown/chmod` may do nothing on FAT |
| Apertar-standard sectioned file `[pi4] [cm4] [cm5] [pi5] [all]`, DPI list at end | hpp header comment; `readState` refuses when neither the board section nor `[all]` exists | "not the Apertar layout" |
| helper accepts input only with a `[pi5]`, `[pi4]` or `[all]` section | helper l.55 | `[cm5]`-only file would be refused |
| board families pi5 (BCM2712), pi4 (BCM2711), pi3 (BCM2837/2710); undetected (no device tree) reads as Pi 5 | hpp:77-95 | `detected` flag in JSON |
| board section = family name (`[pi5]` for Pi 5 and CM5 alike) | `boardSection` | CM5-specific `[cm5]` lines are only read for filters, edits go to `[pi5]` |
| camera ports: Pi 5 or compute module = cam0 and cam1; Pi 4/3 = cam1 only | `boardPorts` | |
| RP1 clock overlay only on pi5 family; `rp1-clk-333mhz`; needs `.dtbo` installed | hpp:530, 858-870 | hint mentions will127534 rp1-overclock-tool |
| sensor list fixed: imx477, imx577, imx585 (colour/mono), imx294 (comment: matches `detectSensorFamily`); IMX283 not in list although Core has IMX283 support elsewhere in the port | hpp:158-168 | other `ov*`/`ar*`/`imx*` overlays recognised as camera overlays by prefix and kept ("a sensor this card does not list, kept as it is") |
| link-frequency tables from Cinemate `sensors.json`: IMX585 297-1039.5 MHz (1188 MHz omitted), IMX477 450-972 MHz; on Pi 4 options above `pi4MaxHz` dropped (IMX477 500 MHz, IMX585 891 MHz) | hpp:148-168 | "over RP1 spec" and "experimental" flags |
| `camera_auto_detect` forced to 0 when a sensor is set | hpp:960 | |
| I2C = `dtparam=i2c_arm=on` (alias `i2c`), I2S, SPI in board section; audio in `[all]` | `toggles()` | |
| display: DPI overlays `vc4-kms-DPI-4inch`, `waveshare-4dpi`, `waveshare-touch-4dpi` or `vc4-kms-dpi-hyperpixel4sq`; DPI panel holds GPIO 0-27 incl. I2C bus 1 | hpp displays(), App:3828 message | DRM connectors read from `/sys/class/drm` |
| fixed fan block (`# BEGIN/END APERTAR FAN MODE`) skipped as `fenced`, never edited by the card | hpp parse | fan = `dtparam=cooling_fan`, `fan_tempN*` (upstream, unchanged) |
| Core runs as user `pi` (sudoers `pi ALL=(root)`) | sudoers | |
| install path assumption `~/ApertarCore/` in README and error message | README l.200, App:3606 | |
| helper uses coreutils `mktemp`, `head -c`, `chown --reference` (GNU) | helper | |
| no RAM size, core count, gpiochip numbering or I2C bus number used in this unit; I2C bus 1 only named in the display warning text | | confirmed |

## 8. Comparison: how original Apertar touches config.txt and gets root

| item | upstream 1.6.0 | port |
| --- | --- | --- |
| Core reads config.txt | `App:2845` constant; `currentFanMode` (:3118); `applyFanMode` (:3127) | same plus engine, DPI facts, boot-config routes |
| Core writes config.txt | only the fan block, `sudo -n install -m 644 tmp dest` | engine edits any line; same sudo-install is fallback; direct write; helper |
| UI reads | `DeviceInfoBridge.cpp:231` scans for sensor token; `SystemActionBridge.cpp:25` path, read for fan mode | unchanged |
| UI writes | `SystemActionBridge::applyFanMode` via `invokePrivilegedCommand("install", ...)` (second writer, same block) | removed, goes to Core `set_fan_mode` |
| root mechanism | `sudo -n install` plus per-helper `/usr/local/libexec/apertar-standby-*` with sudoers files in `ui-upstream/systemd/` | adds a third root helper in Core's `scripts/` with its sudoers in Core `config/`; install steps in README only |
| helper install steps upstream | not found in either README (grep `sudo install`, `libexec`: only references) | README gives `sudo install` commands |
| locking | none | `bootConfigMutex` |
| tests | none | 2 host tests |
| Core `set_fan_mode` | exists upstream (App@up:10568); UI did not use it | UI now uses it |

## 9. Open points to verify later (not judged)

- `HardwareConfigText.hpp` is absent upstream (ls of core-upstream/src/hardware): `hwconf::parseConfigTxt` is port code from the Controls unit, so the engine's "same rule as HardwareConfigText" comment points at another port file.
- b3e7f52: WCP only, 9 lines.
- WCP card JS (about 730 lines) read only at its anchors, not completely.
- Pi behaviour of helper fallback order: unconfirmed (never run on a Pi per fork-log).
