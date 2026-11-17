# Boot Config card and the root helpers: final plan

Read at Apertar-Core `/home/user/wt/core-work` `0d13a6f` (port `01f170c` + 10 fixes; the Boot Config, fan and trim lines quoted here have the same numbers as at `7dc6f7a`, where the first draft was read) and Apertar-UI `/home/user/wt/ui-work` `ac1fc28`. Upstream at `/home/user/wt/core-upstream` and `/home/user/wt/ui-upstream`, tag `upstream-1.6.0`. Every port `path:line` is `@0d13a6f` unless marked. This page replaces the first draft and its challenge; the last section says what the challenge changed.

## In short

- Today the Boot Config card (WebUI, System pane) writes `/boot/firmware/config.txt` through its own HTTP route with its own lock, a revision header, status codes 400/403/409/500 and an "is it a browser" rule. The same setter is also a socket command with weaker rules.
- A `text` field lets any LAN client hand Core a whole new `config.txt`, which a root helper then installs. `kernel=`, `os_prefix=`, `initramfs` all pass.
- The editing engine is a 1355-line header that also carries a line diff, managed-line marks, labels and its own JSON escaper.
- It does not see `include camera-selection.txt`, the stock image's own way of loading a sensor.
- Three root helpers are `/bin/sh` scripts with sudoers and a tmpfiles file in the Core repo. Upstream has `sudo -n <fixed tool>` from Core, and C++ helpers with literal verbs in the UI repo.
- Target: `set_boot_config` is an ordinary `handleCommand` block that the card sends through `POST /api/command`. `GET /api/boot-config` is the one read, shaped like upstream's `GET /api/config`. Core writes only lines generated from the card's fields. The file is replaced with two `sudo -n install` calls, the fan mode's own shape plus the backup line. All three helper scripts and their sudoers files go; one install file stays (decision 12). The engine loses everything the free-text editor needed. The sensor overlay, its port, mono, `ccmp` and link frequency stay switchable from the WebUI.
- 21 commits, all in Apertar-Core. No UI commit. Five are owner-optional (6, 10, 15, 18, 21). Two of the first draft's commits are other themes' (webui-state 9, command-plane 11).

## How it works in the port today

The mechanism, read end to end. "Card" = the Boot Config card in the WebUI System pane. "Engine" = `src/hardware/BootConfigText.hpp` (`apertar::bootconf`, header-only, no I/O). `BCT` = that file.

| Value or path | Who writes | Who reads | Thread and lock | File it is saved in | Shown where |
| --- | --- | --- | --- | --- | --- |
| `config.txt` path | `bootConfigPath()` returns `$APERTAR_BOOT_CONFIG` or `kBootConfigPath` (`App:3505-3510`) | every reader below | none | - | card note `payload.path` |
| Card state (sensor per port, link Hz, I2C/I2S/SPI/audio, RP1 clock, DPI display, `camera_auto_detect`) | nobody; read from the file | `bootconf::parseDocument` + `readState` (`BCT:315`, `:512`); `bootConfigJson` (`App:3690-3707`) | web server thread (GET route) or command thread; `bootConfigMutex()` (`App:3513`, `:3769`) | `config.txt` | card selects and pills (`WCP:20122-20258`) |
| `GET /api/boot-config` | - | `bootConfigGet(-1)` (`App:9165-9172`) | web thread, `bootConfigMutex()` | - | `loadBootConfig` (`WCP:20273`) |
| `get_boot_config` command | - | `bootConfigGet(command.id)` (`App:14602-14603`); listed in the commands reply (`App:12947`) | `commandMutex_` and `bootConfigMutex()` | - | no client: not in `ui-work/src`, `qml`; only `README.md:211` |
| Save via `POST /api/boot-config` | page `bootConfigPost` with header `X-Apertar-Revision` (`WCP:20075-20087`) | route splices `"cmd":"set_boot_config"` into the body, `parseControlCommand`, `bootConfigSet(cmd, revision, origin present)` (`App:9174-9199`) | web thread, NOT `commandMutex_`; `bootConfigMutex()` (`App:3785`) | `config.txt` + `config.txt.apertar.bak` | review diff box, toasts |
| Save via `set_boot_config` on socket or `/api/command` | any client | `bootConfigSet(command, revision field, browser=false)` (`App:14605-14606`) | `commandMutex_` + `bootConfigMutex()` | same | - |
| `revision` (FNV-1a of the file) | `bootconf::revisionOf` (`BCT:1343`) | `bootConfigSet`: missing revision refused only when `browser` is true; wrong revision -> 409 `stale` (`App:3790-3799`) | under `bootConfigMutex()` | - | page keeps `payload.revision` |
| `text` (whole file typed by hand) | card "Edit file" / "Use This Text" (`WCP:20544-20622`), `body.text` (`WCP:20070-20071`) | `bootConfigSet`: `textProblem` (non-empty, 64 KiB, no NUL) then `applyRequest` on top (`App:3803-3816`) | as above | `config.txt` as root | Edit file textarea with italic marks from `state.managed` (`BCT:498-500`, `:597-620`) |
| `previewState` | `bootConfigPreviewText` stores `payload.state` / `result.state` (`WCP:20477`, `:20485`) | only the italic marks (`WCP:20499`, `:20556`) | page | - | View file and Edit file marks |
| `dry_run` review | page `reviewBootConfig` (`WCP:20313`) | `bootConfigSet` returns `changes[]`, `text`, `state`, `drm[]` (`App:3817-3822`) | as above | - | diff box with Save and Reboot / Save Only / Back |
| `confirm_display` | page checkbox gate | `bootConfigSet` 409 `confirm_display` with `drm[]` (`App:3823-3827`) | as above | - | checkbox "Change the display anyway" |
| Booleans | page sends JSON `true`/`false` (`WCP:20066`); `parseControlCommand` keeps bare `true`, `false`, `null` and numbers as text (`ControlProtocol.cpp:120-137`) | `boolFieldValue` (on/yes/off/no too, `App:3709-3718`) | - | - | - |
| Upload and live marks | page `uploadBootConfig`, `bootConfigEditorEdited` every 500 ms | `POST /api/boot-config/parse` (`App:9204-9216`), called at `WCP:20528` (Upload), `:20578` (marks), `:20604` (Use This Text) | web thread, no lock | - | card form, gutter marks |
| The write | `writeBootConfigText` (`App:3533-3610`): (1) direct temp+fsync+rename when writable; (2) `sudo -n /usr/local/libexec/apertar-boot-config < staged`; (3) `sudo -n install` twice (backup `:3595`, file `:3596`) | - | caller's thread and locks | `config.txt`, `config.txt.apertar.bak` | 403 sentence carries two `sudo install` command lines (`App:3602-3607`) |
| Root helper `apertar-boot-config` | `scripts/apertar-boot-config:1-71` (`#!/bin/sh`, text on stdin) | `sudo` via `config/apertar-boot-config.sudoers:4` | root | - | README install block (`README.md:198-206`) |
| Fan mode | `set_fan_mode` -> `applyFanMode` (`App:3620-3649`), block `# BEGIN APERTAR FAN MODE`, now through `writeBootConfigText` | `currentFanMode` (`App:3612`) into state `fan_mode` | `commandMutex_` + `bootConfigMutex()` | `config.txt` | WebUI Thermal card, touch UI Settings |
| Touch UI fan mode | `SystemActionBridge::applyFanMode` sends `set_fan_mode` over its own `QLocalSocket` (`UI src/SystemActionBridge.cpp:66-97`, `:404-409` @`ac1fc28`). Upstream UI wrote `config.txt` itself (`UI src/SystemActionBridge.cpp:25`, `:431-469@upstream-1.6.0`) | Core as above | GUI thread, 8 s timeout | `config.txt` (by Core) | touch UI Settings |
| Board | `bootConfigFacts` reads only `/proc/device-tree/compatible` (`App:3656`); `boardFromDeviceTree` turns NUL into `,` and searches substrings; no match -> "pi5" (`BCT:83-97`) | `filterApplies`, `boardPorts`, `linkOptionsFor` (cap only on "pi4") (`BCT:101-130`, `:182-188`) | caller | - | card note |
| `include camera-selection.txt` | the stock image | nobody: a line without `=` gets no key (`BCT:288-289`) | - | `config.txt` | not shown |
| IMX585 overlay options | the port driver: `mono`, `ccmp`, `2lane`, `always-on`, `rotation`, `orientation`, `sync-mode`, `link-frequency` (`imx585-overlay.dts:122-139`, `ccmp` from driver `70bdb26`) | engine writes `mono` and `link-frequency` only (`BCT:917-935`); other params on an existing line are kept (`BCT:349-372`) | - | `config.txt` | only Edit file can add `ccmp`. Mono 12-bit Clear HDR needs `dtoverlay=imx585,...,mono,ccmp`, else stream-on fails with `-EINVAL` (`raw/inv-Driver-imx585.md` F5) |
| Trim helper `apertar-media-trim` | `runTrimHelperProcess`: `execl("/usr/bin/sudo","sudo","-n",helper,mountPoint)` (`App:6419-6456`), from `runMediaTrim` (`App:11486-11596`) | `scripts/apertar-media-trim:1-90` (canonical path, `findmnt`, discard check, `timeout 20 fstrim`), sudoers `config/apertar-media-trim.sudoers` (any argument) | trim worker, `mediaTrimMutex_`; `waitForMediaTrim` sends SIGTERM to the sudo pid, 1 s later SIGKILL (`App:11959-11965`) | - | state `media_trim_*` |
| Kernel tune helper `apertar-media-tune` | `applyMediaTuning` (`App:11400-11435`), plain `sudo -n`, from the media watcher | `scripts/apertar-media-tune:1-112`, `config/apertar-media.sudoers`, `config/apertar-media.tmpfiles.conf:5` | media watcher thread | `/run/apertar-media/tune/` | journal only; off unless `APERTAR_MEDIA_TUNE=1` or `kernel_tune=on` |
| `/run/apertar-media` | `config/apertar-media.tmpfiles.conf:3-5` (pi-owned dir, `eject`, `tune`) | `MediaIntent.hpp:15-25` writes eject flags, best effort; no reader in Apertar (App-1-F14, Media-fault-tune-F4) | - | `/run` | - |

Sizes today: engine 1355 lines; App boot-config code about 340 lines (`App:3502-3843`) plus routes (`App:9164-9216`); card HTML 90 lines (`WCP:5859-5950`) and JS about 740 lines (`WCP:19937-20678`); host tests `tools/boot_config_test.cpp` 427 lines and `tools/boot_config_helper_test.sh` 33 lines.

## How original Apertar does this kind of thing

| Kind of problem | Upstream precedent (`@upstream-1.6.0`) |
| --- | --- |
| A WebUI control that writes `config.txt` | Fan mode. Page: `sendCommand({ cmd: "set_fan_mode", value })` (`WCP:11093`). Core: `if (command.name == "set_fan_mode")` inside `handleCommand` under `commandMutex_` (`App:10568-10577`). Only a generated, fenced block is written (`fanModeBlock` `App:3042`, `stripManagedFanBlock` `App:3084`). |
| Writing a root-owned file | `applyFanMode`: stage a temp file, then `"sudo -n install -m 644 " + shellQuote(tempPath) + " " + shellQuote(kBootConfigPath)` (`App:3127-3175`, call `:3155-3158`). A refusal becomes "Changing the fan mode needs sudo permission." (`App:3164-3170`). No helper, no sudoers file. GNU `install` unlinks the target, then creates and writes it (strace here: `unlinkat(dst)`, `openat(dst, O_CREAT|O_EXCL)`). |
| Simple privileged steps | `sudo -n` + fixed tool + `shellQuote`: `mkdir -p` (`App:3609`), `mount` (`App:3636`), `blockdev --flushbufs` (`App:3353`), `systemctl` (`App:3205`). PLT-5. |
| A real root program | Single-file Qt-free C++ in the UI repo (`UI src/StandbyLowPower.cpp`, `StandbyUsbPower.cpp`), each makes its own `/run/apertar-<name>` (`StandbyUsbPower.cpp:23`, `StandbyLowPower.cpp:17`); sudoers listing every verb (`UI systemd/apertar-standby-usb.sudoers`); called as `/usr/bin/timeout 6s /usr/bin/sudo -n /usr/local/libexec/apertar-standby-usb <verb>` (`App:1541-1549`). PLT-4, PLT-6, R14. Core never kills these. |
| A text file the operator edits in the browser | `GET /api/config` and `POST /api/config` -> `saveHardwareConfigFile` (`App:7168-7195`, `:5323-5385`): `.bak`, temp + rename, written as `pi`, never a boot file. No command twin, no lock on the read. |
| `get_*` commands | Only `get_state` and `get_media_test_state` (`App:9218`, `:10608`). A file the browser edits has no command twin. |
| JSON for a reply | Builders in a header next to their data: `recordingCapabilitiesJson` (`include/apertar/core/RecordingCapabilities.hpp:52-60`), `exposureMeteringJson` (`src/camera/ExposureMetering.hpp:28-39`). The escaper is the public `apertar::escapeJson` (`src/ipc/ControlProtocol.hpp:25`, `.cpp:235`), used by App's `okReply`/`errorReply` (`App:108-128`). CameraController keeps a second local one (`CameraController.cpp:95`). |
| Command entry and errors | `POST /api/command` -> `handleWebCommand` -> `handleCommand` (`App:7085-7091`); `okReply` / `errorReply` with one sentence, HTTP 200. No route reads a custom header or answers 403/409. Origin policy is server-wide (`WS:156-171`). |
| Confirm a system-level action | `if (!window.confirm("Restart the Apertar system now?")) return;` then `sendCommand({ cmd: "restart_system" })` (`WCP:11325-11334`). Core has no confirm field. |
| Which sensor the camera has | UI reads `/boot/firmware/camera-selection.txt` first: "Apertar's camera-selection file is authoritative" (`UI src/DeviceInfoBridge.cpp:213-215`). |
| Board detection | PLT-3: pure `recordingCapabilitiesFromCompatible` comparing each NUL-separated entry to exact SoC strings `brcm,bcm2712`, `brcm,bcm2711`, `brcm,bcm2837`, ...; reader tries `/sys/firmware/devicetree/base/compatible`, then `/proc/device-tree/compatible` (`RecordingCapabilities.hpp:18-50`). |
| Booleans in a command | `*enabled == "true" \|\| *enabled == "1"`, anything else false (`App:9486`). CMD-8. |
| Select fill | `ensureSelectEntries` / `normalizeSelectEntries` (`WCP:6210-6230`). |
| Install files | Core holds only `config/apertar-core-capture-priority.conf` and `scripts/start-apertar-core.sh`; sudoers live in `UI/systemd/` (PLT-6). No tmpfiles file anywhere. |

Where upstream has nothing: a WebUI editor of sensor overlays in `config.txt`, a dry-run review with a line diff, a read-back check, a revision check, a reboot wait, a drive trim, a runtime directory shared with an automounter. That is new ground (below).

## The target

- **Entry point.** One write door: `set_boot_config` inside `handleCommand`, reached from the socket and from `POST /api/command` (the card uses `sendCommand`). One read: `GET /api/boot-config`, as `GET /api/config` upstream. No `get_boot_config`, no other route.
- **What it may write.** Only lines the engine generates from the card's fields: comment or uncomment the existing `dtoverlay=<sensor>[,cam0][,mono][,ccmp][,link-frequency=<Hz>]` lines and set those parameters, `camera_auto_detect=0`, the four `dtparam` switches, the RP1 clock overlay, the listed DPI overlays. Other parameters already on a line stay. The fan block stays `set_fan_mode`'s. Never caller text.
- **How it is guarded.** `commandMutex_` (one lock for fan mode and Boot Config). A `revision` field on every save that is not a dry run (command-plane commit 10). Read-back: a result that would not load what was asked is refused with the line that decides it. A file with an active `include` keeps its sensor rows read-only. An unknown board is read-only. A display change is confirmed in the page with `window.confirm`; Core has no confirm field.
- **How it writes.** Real file: stage in `temp_directory_path()`, `sudo -n install -m 644 config.txt config.txt.apertar.bak`, `sudo -n install -m 644 <staged> config.txt`: the fan mode's shape plus the port's backup line. `$APERTAR_BOOT_CONFIG` (a copy on a dev host) is written by Core itself, the way `saveHardwareConfigFile` writes its file.
- **How big.** Engine about 1000 lines (from 1355); App about 170 (from about 340); card about 520 JS + HTML lines (from about 830). Below 800 for the engine only if the owner drops rows (decision 3).
- **Root helpers.** None in Core. Trim calls `/usr/bin/sudo -n /usr/bin/timeout -k 2s 20s /usr/sbin/fstrim -v <mount>`, so the timeout that ends `fstrim` runs as root. The kernel tuning helper is deleted if the owner agrees (decision 10). A future real root program follows R14: `Apertar-UI/src/<Name>.cpp`, literal verbs, sudoers in `Apertar-UI/systemd/`.

| Value | Before (port) | After |
| --- | --- | --- |
| Card save | `POST /api/boot-config`, header revision, 200/400/403/409/500, `code` field | `sendCommand({cmd:"set_boot_config", ..., revision})`; `okReply` / `errorReply` sentence; HTTP 200 |
| Card read | `GET /api/boot-config` and `get_boot_config` | `GET /api/boot-config` only |
| Lock | `bootConfigMutex()` on the route, both locks on the socket | `commandMutex_` only; the GET read takes no lock, as `GET /api/config` |
| `revision` | required only when an Origin header is present | required on every non-dry-run save, command-plane's sentence "config.txt changed since the card loaded it. Reload the card and choose again." |
| `text` field, Edit file, Use This Text, managed marks, `previewState` | yes | gone |
| `ccmp` | only by Edit file | sensor choice "StarlightEye (IMX585, mono, 12-bit Clear HDR)" = `imx585,...,mono,ccmp`, offered when the installed `imx585.dtbo` has the `ccmp` parameter |
| Upload, `POST /api/boot-config/parse` | yes | gone if the owner agrees (decision 2) |
| `confirm_display`, `drm[]` | Core 409 + page checkbox | page `window.confirm` naming the effect; Core field gone |
| Review | `changes[]` from Core, own renderer | reply carries the would-be `text`; page shows it with the port's own `configDiffLines` (new ground, shared with the Config page) |
| `set_boot_config` reply | `written, via, changes[], display_changed, text, state{}, revision, reboot_required, drm[]` | `written, dry_run, display_changed, text, revision, reboot_required` (scalars) |
| GET reply | `boot_config{path, readable, revision, helper, backup_path, state{... managed[], sensors[{link{options[{label}]}}]}, drm[], text}` | `boot_config{path, readable, revision, backup_path, state{...}, text}`; link options are Hz numbers, the page writes the label. Nested objects stay: a read route, as `/api/media` |
| The write | direct / helper / `sudo -n install` | dev copy: Core writes it; real file: `sudo -n install` backup, `sudo -n install` staged copy |
| Permission error | two `sudo install ...` command lines | "Writing config.txt needs sudo permission." (fan mode keeps its own sentence) |
| Board | substring, unknown = Pi 5, cap only on Pi 4 | exact SoC strings per NUL entry, PLT-3 path order; unknown = read-only (read as Pi 5 only with `$APERTAR_BOOT_CONFIG` and no device tree); cap on every board that is not Pi 5-class |
| `include camera-selection.txt` | invisible | read; sensor rows read-only with one sentence |
| IMX283 | missing | listed, no link menu |
| Booleans | `boolFieldValue` (on/yes/off/no) | `== "true" \|\| == "1"`, `== "false" \|\| == "0"`, else "<field> must be true or false." (command-plane commit 11) |
| Page store | `const bootConfig = {...}` + `installBootConfigInteractions` | `state.bootConfig*` (webui-state commit 9) |
| Trim | `sudo -n /usr/local/libexec/apertar-media-trim <mount>` | `sudo -n /usr/bin/timeout -k 2s 20s /usr/sbin/fstrim -v <mount>`; canonical-path and discard check in Core, disk read from the mount at trim time |
| Kernel tune | `sudo -n /usr/local/libexec/apertar-media-tune ...` | gone (decision 10) |
| Files in Core `scripts/`, `config/` for root work | 3 helpers, 3 sudoers, tmpfiles file (`/run/apertar-media`, `eject`, `tune`), 2 shell tests | `config/apertar-media.tmpfiles.conf` with its two `eject`-side lines only (decision 12); nothing else |
| Fan mode `fan_mode` in state, `set_fan_mode` | unchanged | unchanged (same field, same type) |

How a value reaches the UIs: the card reads `GET /api/boot-config` when the System pane opens (as today), saves with `set_boot_config`, re-reads after a save. Nothing of it is in `/api/state` or `get_state`, and the touch UI shows none of it, as today. The touch UI's sensor name keeps coming from `DeviceInfoBridge` (camera-selection file, then sysfs, then `config.txt`).

Old files: nothing moves. `config.txt` keeps its layout. A line `dtoverlay=imx585,cam0,mono,ccmp` written by hand is read as the new mono-with-ccmp choice; a `ccmp` on a colour line is kept as an unknown parameter, as today. `config.txt.apertar.bak` keeps its name. An installed `/usr/local/libexec/apertar-boot-config`, `apertar-media-trim` or `/etc/sudoers.d/apertar-*` on the owner's Pi is no longer called and does no harm; the README says how to remove them. A media tuning file with `kernel_tune = on` keeps loading (the key stays known to the parser until storage-settings decides its fate) and does nothing once commit 10 lands.

Stock camera: the card only reads until the operator presses Save. No key is added to any file. The mono-with-ccmp choice is not offered with the stock imx585 driver (its overlay has no `ccmp`).

## Commit plan

All commits are in Apertar-Core. Each one: `check_core.sh <tree> <tag> both tests` builds with and without libcamera and runs the host tests; `smoke_core.sh` diffs the reply shapes against the previous commit (`/api/state` and `get_state` must not change). "Sim card" means: copy the fixture text of `tools/boot_config_test.cpp` (`kApertar`) to `/tmp/bc/config.txt`, start `APERTAR_BOOT_CONFIG=/tmp/bc/config.txt apertar-core --simulate --web-port 8091 ...`, open the System pane in headless Chromium, and curl `/api/boot-config`.

Before this plan: command-plane commits 10 (Boot Config refusals are one sentence, every save names its revision, `browser` goes) and 11 (Boot Config switches read true or 1) land first. They edit the same `bootConfigSet` lines (`App:3775-3841`). This theme does not repeat them.

### 1. `core, web: the Boot Config card saves through /api/command`

- Files: `App` `bootConfigSet`, `bootConfigGet`, `applyFanMode`, `handleWebRequest`; `WCP` `bootConfigPost`, `saveBootConfig`, `reviewBootConfig`, `bootConfigPreviewText`.
- Deleted: the `POST /api/boot-config` branch (`App:9174-9199`), `BootConfigReply` (`App:3761-3764`), `bootConfigMutex()` and its three `lock_guard`s (`App:3513-3517`, `:3628`, `:3769`, `:3785`), `result.httpStatus` in the page.
- Changed: `bootConfigSet(const ControlCommand &)` and `bootConfigGet(int)` return `std::string`. `bootConfigPost` becomes `sendCommand({ cmd: "set_boot_config", ...body, revision })` in `try/catch` with `showToast(error.message, true)`. The body is sent as it is: `parseControlCommand` already keeps bare `true`, `false`, `null` and numbers as text (`ControlProtocol.cpp:120-137`). The "reload on any refusal" in `saveBootConfig` is command-plane 10's and stays.
- Lines: about -50 / +15.
- Check here: both builds, host tests; sim card: `curl -X POST /api/boot-config` -> 404; `curl /api/command -d '{"cmd":"set_boot_config","cam0_sensor":"imx477"}'` -> command-plane's revision sentence; same with `"dry_run":true` -> ok; Chromium: change the cam0 sensor, Save Only, `diff /tmp/bc/config.txt /tmp/bc/config.txt.apertar.bak` shows the one line.
- Pi only: Save from the card on the CM5 and reboot; `journalctl -u apertar-core | grep 'boot config'`.
- Depends on: command-plane 10 and 11. If they have not landed, this commit first applies their Boot Config parts as written in `design/command-plane.md` commits 10 and 11, and command-plane drops them.

### 2. `core: the Boot Config card offers the IMX585 mono with ccmp`

- Files: `BCT` `Sensor` gains `bool ccmp`; `sensors()` gains `{"imx585_mono_ccmp", "imx585", "StarlightEye (IMX585, mono, 12-bit Clear HDR)", true, ccmp=true, ...imx585Options}`; `sensorKeyOf` returns `imx585_mono_ccmp` for `mono` + `ccmp` (`BCT:386`); `applyRequest` adds or removes `ccmp` after `mono` exactly as it does `mono` (`BCT:917-926`); `Facts` gains `bool imx585Ccmp`; `readState` leaves the choice out of `sensors[]` when `!facts.imx585Ccmp` unless the file already has it. `App` `bootConfigFacts`: `imx585Ccmp` = the bytes `ccmp` appear in `<overlays>/imx585.dtbo` (the dtbo carries its parameter names as strings; `readTextFileRaw` + `find`). Test: a fixture line `dtoverlay=imx585,cam0,mono,ccmp` reads as `imx585_mono_ccmp`; picking it on `imx585,cam0` writes `imx585,cam0,mono,ccmp`; picking `imx585_mono` removes `ccmp`.
- Why here, before Edit file goes: after commit 3 the card is the only WebUI way to set `ccmp`, which mono 12-bit Clear HDR needs (`raw/inv-Driver-imx585.md` F5). It has the shape of `mono`: one sensor choice, no new field, no page code (the select is filled from `state.sensors`).
- Lines: about -2 / +25 (BCT +12, App +5, test +10).
- Check here: host test; sim card with a copy of the port driver's `imx585.dtbo` (or a file containing `ccmp`) in `/tmp/bc/overlays/`: the choice is listed; without it: not listed.
- Pi only: on the CM5, pick the new choice for cam0, Save and Reboot, `grep imx585 /boot/firmware/config.txt` shows `mono,ccmp`, and a mono 12-bit Clear HDR mode starts (`v4l2-ctl -d /dev/v4l-subdev* --list-subdev-mbus-codes` lists the 12-bit HDR code). On a stock imx585 driver: the choice is absent.
- Depends on: nothing. If the driver theme makes colour 12-bit CCMP opt-in too (Driver-imx585-F10), an `imx585_ccmp` row follows the same shape.

### 3. `web: the Boot Config card has no Edit file`

- Files: `WCP` HTML `bootConfigEditField`, `editBootConfigButton` (`WCP:5932-5949`); JS `BOOT_CONFIG_MANAGED`, `bootConfigManagedMap`, `bootConfigManagedSummary`, `bootConfigOwnLinesHint`, `openBootConfigEditor`, `showBootConfigEditorMarks`, `bootConfigEditorEdited`, `closeBootConfigEditor`, `useBootConfigText`, `bootConfig.text/editorMarks/editorTimer/previewState`, the two `previewState` stores (`WCP:20477`, `:20485`), the `text` line in `bootConfigRequestBody`, the italic marks in `toggleBootConfigFile`, the `marks` parameter of `updateEditorGutter`.
- Only deletions. View file and Download stay (read-only).
- Lines: about -170 / +5. Core still accepts `text` after this commit; nothing sends it.
- Check here: Chromium: no Edit file button, View file lists the file; Config page editor gutter still numbers lines; `grep -c 'previewState\|editorMarks' src/web/WebControlPage.cpp` = 0.
- Pi only: nothing new.
- Depends on: 1, 2.

### 4. `core: set_boot_config writes only the card's fields`

- Files: `App` `bootConfigSet` (the `text` block `App:3801-3816`), JSON `managed`; `BCT` `textProblem`, `detail::splitLines`, `lineChanges`, `displayDiffers`, `State::managed` and its loop in `readState` (`BCT:597-620`), the "Edit file" comment block; `tools/boot_config_test.cpp` the `managed`, `lineChanges`, `textProblem`, `displayDiffers` checks; README sentences on Edit file and `text` (`README.md:195`, `:210-211`).
- Lines: about -190 / +3 (BCT -115, App -15, test -55, README -5).
- Check here: host test passes with fewer checks; sim card: `set_boot_config` with `text` -> the field is ignored (file unchanged); `grep -c lineChanges src` = 0.
- Pi only: nothing new.
- Depends on: 3.

### 5. `core, web: a display change on the Boot Config card asks with window.confirm`

- Files: `WCP` `reviewBootConfig` (checkbox gate, `syncGate`, `drmSummary`), `saveBootConfig` (`window.confirm("Change the display overlays and save? A DPI panel that is the camera's only screen stays dark without them.")` when `review.display_changed`); `App` `bootConfigSet` (`confirm_display` field and its refusal, as reworded by command-plane 10), `drmConnectorsJson` and the `drm` members (`App:3667-3688`).
- Why Core loses the guard: upstream confirms system actions only in the page (`WCP:11325@upstream-1.6.0`; `restart_system` has no confirm field). A socket script that changes the display now saves without a second field, as `restart_system` restarts without one.
- Lines: about -55 / +8.
- Check here: Chromium with `page.on("dialog")`: switch Display to Waveshare, Save -> one confirm with that text; dismiss -> file unchanged.
- Pi only: none (no display is switched in the test).
- Depends on: 1; command-plane 10 (it rewords the guard this commit deletes).

### 6. `web, core: the Boot Config card has no Upload` (owner-optional, decision 2)

- Files: `WCP` `uploadBootConfigButton`, `bootConfigUploadInput`, `uploadBootConfig`; `App` `POST /api/boot-config/parse` (`App:9204-9216`).
- Lines: about -45 / +0.
- Check here: Chromium: no Upload button; `curl -X POST /api/boot-config/parse` -> 404.
- Depends on: 3 (after it, Upload is the route's only caller).

### 7. `core: config.txt is read by GET /api/boot-config only`

- Files: `App` the `get_boot_config` block (`App:14602-14603`), its name in the commands reply (`App:12947`); `README.md:211`.
- Why: upstream has no command twin for a file the browser edits (`GET /api/config`, `App:7168@upstream-1.6.0`); nothing calls `get_boot_config`. With it gone, the nested reply is only on a read route, as `/api/media`.
- Lines: about -4 / +0.
- Check here: socket `get_boot_config` -> "Unknown command"; `/api/boot-config` unchanged; the commands reply loses one name (not a 1.6.0 name).
- Depends on: 1.

### 8. `core: config.txt is replaced with sudo -n install, as the fan mode always was`

- Files: `App` `writeBootConfigText`, `kBootConfigHelper`, `fsyncPath`, `bootConfigJson` (`helper` member), `bootConfigSet` (`via`, `how`); delete `scripts/apertar-boot-config`, `config/apertar-boot-config.sudoers`, `tools/boot_config_helper_test.sh`; `README.md:196-206` install block.
- New body of `writeBootConfigText(text, errorMessage, permissionDenied)`:
  - `$APERTAR_BOOT_CONFIG` set: copy to `.apertar.bak`, write `<path>.tmp`, rename (the `saveHardwareConfigFile` shape, `App:5359-5383@upstream-1.6.0`).
  - Real file: stage the text in `temp_directory_path()`; `sudo -n install -m 644 config.txt config.txt.apertar.bak`; `sudo -n install -m 644 <staged> config.txt` (`App:3595-3596` as they are, upstream's `App:3155-3158` plus the backup line). "password" / "not allowed" / "permission denied" -> `permissionDenied`; `bootConfigSet` says "Writing config.txt needs sudo permission."; `applyFanMode` keeps "Changing the fan mode needs sudo permission."
  - The staged-copy-plus-`mv` variant stays on the owner's list (decision 4).
- Lines: about -75 / +25 in App; files -108; README -11.
- Check here: both builds; host tests 16 (helper test gone); sim card save works on the dev copy and leaves `.apertar.bak`; fan mode on the dev copy (`set_fan_mode` `Silent`) writes the block; `grep -rn apertar-boot-config src config scripts` = 0.
- Pi only, BEFORE this commit merges: `sudo -n -l | grep -E 'NOPASSWD: ALL|/usr/bin/install'` as `pi` on the CM5. If it prints nothing, the rig has only the port's narrow rules and this commit waits (decision 4 C). After: card Save on the CM5, `ls -l /boot/firmware/config.txt*`, `cmp` with the review text, reboot, `dtoverlay -l` or `vcgencmd get_config str | grep -i overlay`, camera starts. Fan mode from the touch UI and the WebUI. On a Pi 4: the same with `[pi4]`.
- Depends on: 4 (no caller sends whole-file text any more).

### 9. `core: the media trim runs fstrim through sudo -n and a root timeout`

- Files: `App` `runTrimHelperProcess` -> `runFstrimProcess(mountPoint, pidOut, output)`: `execl("/usr/bin/sudo", "sudo", "-n", "/usr/bin/timeout", "-k", "2s", "20s", "/usr/sbin/fstrim", "-v", mountPoint, nullptr)`. `runMediaTrim`: the helper path and its "not installed" branch with install lines (`App:11510-11520`) go; `std::filesystem::exists("/usr/sbin/fstrim")` else skip, warned once (PLT-5). Before the call: `canonical(path) != path` -> "skipped"; disk = `rootDiskForDevice(canonical(findMountEntry(path).device))` read at trim time (`util/MediaProbe.hpp:126`, `:154`); empty disk -> "skipped", no latch; `readSysfsWord("/sys/block/<disk>/queue/discard_max_bytes")` empty or `0` -> "unsupported" with today's per-mount latch. Exit 124 -> "timeout"; killed -> "timeout" as today; output with "password" or "a terminal is required" -> one log line "Trim needs sudo permission." and "failed". `waitForMediaTrim` and `stopMediaTrim` log once when `kill` returns `EPERM`. The comment at `App:11437-11441`. Delete `scripts/apertar-media-trim`, `config/apertar-media-trim.sudoers`, `tools/media_trim_test.sh`, `README.md:302-313` install block.
- Why this order: `waitForMediaTrim` sends SIGTERM, then SIGKILL 1 s later (`App:11959-11965`). With `timeout ... sudo -n fstrim` (upstream's order, `App:1544@upstream-1.6.0`, for helpers Core never kills) the SIGKILL ends the `pi`-owned `timeout` before its `-k` fires, and a `pi`-owned `timeout` cannot signal a root `fstrim` anyway. With `sudo -n timeout`, the `timeout` runs as root: it ends `fstrim` at 20 s + 2 s whatever happens to Core's signals. SIGTERM to `sudo` is relayed to `timeout`, which forwards it to `fstrim`. Say this in the commit message.
- Lines: about -45 / +35; files -135; README -12.
- Check here: both builds; host tests 15; sim: trim is skipped without a mount (journal "trim ... result=skipped"); `media_trim_*` state fields keep names and types.
- Pi only, before this commit merges, as `pi`: `sudo -n /usr/bin/timeout -k 2s 20s sleep 100 & P=$!; sleep 1; kill -TERM $P; echo kill=$?; sleep 3; pgrep -a 'sleep 100'` must print `kill=0` and no `sleep`. If `kill` prints "Operation not permitted", Core cannot end a running trim; the root `timeout` still bounds it at 22 s (see Risks). After: delete 2 GiB of clips on the CFexpress card, `journalctl -u apertar-core | grep trim` shows "result=trimmed bytes=..."; a USB stick without discard: "result=unsupported" once.
- Depends on: nothing in this theme. storage-settings owns `APERTAR_MEDIA_TRIM` and `set_media_trim` (its commit 8 changes which flag the worker reads); this commit leaves both.

### 10. `core: the kernel tuning helper is gone` (owner-optional, decision 10)

- Files: `App` `applyMediaTuning` (`App:11396-11435`), its two calls (`App:10946`, `:10967`), its declaration in `ApertarCoreApp.hpp`; delete `scripts/apertar-media-tune`, `config/apertar-media.sudoers`, the `tune` line of `config/apertar-media.tmpfiles.conf:5`; README `APERTAR_MEDIA_TUNE` row (`README.md:357`).
- Not touched: `kernel_tune` in `src/util/MediaTune.hpp`, `scripts/apertar-tune`, `config/apertar-media-tune.conf` (storage-settings commits 18-19). Until then the key parses and does nothing; old files load without a warning.
- Lines: about -45 / +0; files -115.
- Check here: both builds; `grep -rn 'apertar-media-tune"\|applyMediaTuning' src` = 0.
- Pi only: insert and pull the card: the media watcher logs the profile as before, no "tuning helper" line.
- Depends on: nothing. storage-settings commit 18 edits `applyMediaTuning` (`APERTAR_MEDIA_TUNE=1` only); if this commit lands, that line of commit 18 is dropped; if the owner says B, commit 18 applies as written.

### 11. `core: the Boot Config card knows the board by its SoC string`

- Files: `BCT` `boardFromDeviceTree` walks the NUL-separated entries exactly as `recordingCapabilitiesFromCompatible` (`RecordingCapabilities.hpp:21-33@upstream-1.6.0`): `brcm,bcm2712` -> pi5, `brcm,bcm2711` -> pi4, `brcm,bcm2837` or `brcm,bcm2710` -> pi3; no match -> `detected=false`, family empty. `readState`: `!board.detected` -> `editable=false`, "This board is not one the Boot Config card knows. Edit config.txt by hand." `Sensor::pi4MaxHz` -> `slowBoardMaxHz`, applied on every family that is not pi5 (`BCT:186`). `App` `bootConfigFacts`: reads `/sys/firmware/devicetree/base/compatible`, then `/proc/device-tree/compatible` (PLT-3 order); with `$APERTAR_BOOT_CONFIG` set and no device tree, the board is a Pi 5 (the dev host). This is the one place the dev fallback lives.
- Host test cases: `boardFromDeviceTree("")`, `"raspberrypi,4-model-b\0brcm,bcm2711\0"`, `"raspberrypi,5-compute-module\0brcm,bcm2712\0"`, `"raspberrypi,model-zero-2-w\0brcm,bcm2837\0"`, `"brcm,bcm2835\0"` (unknown, read-only); `[pi5]` lines do not apply on an unknown board.
- Lines: about -15 / +30.
- Check here: host test (the sim card without the env var is read-only already, because `/boot/firmware/config.txt` is absent here, `App:3693-3698`); sim card with the env var: as today.
- Pi only: on a Pi 4 with an IMX477: the link list ends at 500 MHz; on a Zero 2 W / Pi 3 if one is at hand: the card edits `[all]` (board-support T5 for `[pi3]`).
- Depends on: nothing. hardware-inputs commit 14 reads `config.txt` through the engine for the pin checks: it takes the board from `bootConfigFacts().board`, not from `boardFromDeviceTree` directly, so a dev host still reads `[pi5]` lines and a real Pi 5/4/3 sees what it sees today. An unknown SoC (Pi 1, 2, Zero) then counts only `[all]` lines, which is what its firmware does (today it counts `[pi5]` lines there).

### 12. `core: the Boot Config card leaves a sensor from include camera-selection.txt alone`

- Files: `BCT` `lineFrom` (a line `include <file>` gets key `include`, value the file name); `State` gains `std::string cameraProblem`; `readState` (an uncommented `include` in a section that applies -> `cameraProblem = "config.txt includes <file>: the sensor comes from that file."`); `applyRequest` (a sensor or link change while `cameraProblem` is set -> refused with that sentence); `App` JSON `camera_problem`; `WCP` `renderBootConfigPort` disables both sensor selects and shows the sentence; test fixture: an `include camera-selection.txt` line under the stock comment.
- Lines: about -0 / +30.
- Check here: host test; sim card with an `include` line added to the copy: sensor selects disabled, buses still editable.
- Pi only: on a fresh Apertar 1.6.0 image: `grep -n '^include' /boot/firmware/config.txt; cat /boot/firmware/camera-selection.txt` settles the premise. Then `cp /boot/firmware/config.txt /tmp/before.txt`, pick IMX585 in the card, Save: refused with the include sentence; `cmp /tmp/before.txt /boot/firmware/config.txt` prints nothing. The owner's CM5 has the include removed, so its card behaves as today.
- Depends on: 4. Decision 5 for the larger option.

### 13. `core: the Boot Config card lists the IMX283`

- Files: `BCT` `sensors()` gains `{"imx283", "imx283", "IMX283", false, false, 0, 0, {}}`; the comment above it names the sensors without the CameraController function; one test check.
- Lines: -1 / +3.
- Check here: host test; sim card select shows IMX283.
- Pi only: with the imx283 driver installed, pick IMX283 on cam0, reboot, camera starts.
- Depends on: 2 (the `Sensor` row shape).

### 14. `core, web: Boot Config link options are Hz; the page writes the label`

- Files: `BCT` `linkOptionLabel` and the `mbpsPerLane` / `fps4k` members deleted (`LinkOption` keeps `hz`, `overRp1Spec`, `experimental`), `stateJson` sends `hz`, `default`, `over_rp1_spec`, `experimental` per option; `WCP` label = `megahertzText(hz)` + " (default)" / " (experimental)" / " (over RP1 spec)"; test checks of the label move to the four inputs.
- `managed` (commit 4), `drm` (commit 5) and `helper` (commit 8) are already gone.
- Lines: about -50 / +12.
- Check here: host test; `smoke_core.sh` shape diff of `GET /api/boot-config` shows only the `label` strings gone; Chromium: link select renders "720 MHz (default)".
- Depends on: 8.

### 15. `core: the Boot Config JSON escapes strings with escapeJson` (owner-optional, decision 13)

- Files: `BCT` includes `ipc/ControlProtocol.hpp`; `jsonString` deleted, its uses become `'"' + escapeJson(x) + '"'`; the same in App's Boot Config lines (`App:3680`, `:3701-3706`, `bootConfigSet`); `tools/boot_config_test.cpp` compile line adds `src/ipc/ControlProtocol.cpp`.
- The builder stays in the header, as `recordingCapabilitiesJson` and `exposureMeteringJson` do upstream. No move.
- Lines: about -25 / +22.
- Check here: host test; `smoke_core.sh` byte diff of `GET /api/boot-config` on the fixture is empty.
- Depends on: 14.

### 16. `core, web: the Boot Config review shows the line diff of the would-be file`

- Files: `App` `bootConfigSet` reply drops `changes` and `state` (scalars: `written`, `dry_run`, `display_changed`, `text`, `revision`, `reboot_required`); `BCT` `changesJson` deleted, `Change` stays internal (the host test counts edits with it); `WCP` `reviewBootConfig` renders `configDiffLines(payload.text, result.text)` in the box shape of the Config page's Save (`WCP:18884-18960`); `bootConfigDiffLine`'s own layout goes.
- `configDiffLines` is port code (upstream's Config page saves with no review). This reuses a port helper; the review is new ground (below).
- Lines: about -50 / +20.
- Check here: Chromium: review lists the same changed lines as before for "imx585 -> imx477".
- Depends on: 3 (no `previewState` reader left), 5. If hardware-inputs reshapes `configDiffLines` / `showConfigDiff` (WCP-10-F8, WCP-10-F12), this commit uses their helper.

### 17. `web: Boot Config selects are filled by ensureSelectEntries`

- Files: `WCP` `normalizeSelectEntries` passes `enabled: false` through to `option.disabled`; `renderBootConfigPort` and the display select call `ensureSelectEntries`; `bootConfigOption` deleted.
- Lines: about -20 / +8.
- Check here: Chromium: a missing overlay shows a disabled option.
- Depends on: 16; lands after webui-state commit 9 (it moves `bootConfig.*` to `state.bootConfig*`; write against the moved names). Shared helper change: tell webui-state.

### 18. `web: Save and Reboot hands over to the restart like the Restart button` (owner-optional, decision 6)

- Files: `WCP` `rebootForBootConfig` becomes `sendCommand({ cmd: "restart_system" })` + toast "Restart requested."; `waitForCameraAfterReboot`, `bootConfigSleep`, `bootConfig.waiting`, the "Rebooting" pill deleted. The page's 1 Hz `fetchState` shows when the camera is back.
- Lines: about -45 / +5.
- Pi only: Save and Reboot; the page reconnects by itself after the reboot.
- Depends on: 16; after webui-state commit 9.

### 19. `core, web: Boot Config comments and card copy in the Apertar register`

- Files: `BCT` header essay to two lines, `// ----` banners and Cinemate references out, non-ASCII label glyphs out; `App:3651` banner; `WCP` comment banner (`WCP:19937-19940`), card copy to one sentence ("Sensor overlays, buses and display in config.txt; a change takes effect after a reboot."), RP1 text only in `bootConfigRp1Note`; `tools/boot_config_test.cpp` header line.
- Lines: about -60 / +8.
- Check here: builds; `grep -n -i cinemate src/hardware/BootConfigText.hpp` = 0; `grep -nP '[^\x00-\x7F]' src/hardware/BootConfigText.hpp` = 0.
- Depends on: 14.

### 20. `docs: the README says what the Boot Config card does in one paragraph`

- Files: `README.md:179-212` -> one paragraph and the recovery line ("If the camera does not come back, put the card in a reader and copy `config.txt.apertar.bak` over `config.txt`."); the socket-command list out; one line: "Earlier port builds installed `/usr/local/libexec/apertar-boot-config`, `apertar-media-trim`, `apertar-media-tune` and their sudoers files; they are no longer used and can be removed."
- Lines: about -30 / +4.
- Depends on: 7, 8, 9; 10 if taken.

### 21. `core: the config.txt editor is src/hardware/BootConfig.{hpp,cpp}` (owner-optional, decision 11)

- Files: `BootConfigText.hpp` -> `src/hardware/BootConfig.hpp` (types, declarations, `namespace apertar::bootconf`) + `BootConfig.cpp` (bodies), `.cpp` listed by name in `add_executable` (HW-23, PLT-1); `tools/boot_config_test.cpp` compile line names `src/hardware/BootConfig.cpp`.
- Lines: about -1000 / +1010 (a move).
- Check here: both builds; host test links the `.cpp`.
- Depends on: 19, and the hardware-inputs decision for `HardwareConfigText.hpp` (same shape); do both or neither.

Order: 1-7 fix the doors and the free text first; 2 comes before 3 so the rig can set `ccmp` from the WebUI after every commit. 8-10 fix the helpers. 11-13 are board and sensor correctness. 14-21 are shape and size. After each commit the card still switches the sensor overlay on the dev copy and on the Pi.

## What stays as new ground

| Feature | Shape it keeps | Why that shape |
| --- | --- | --- |
| A WebUI card that edits `config.txt` sensor overlays | One settings card in the System pane, one command, one read route | The owner switches IMX585 options from the WebUI on the rig. Upstream only has the fan block; a fenced block cannot switch off an earlier sensor line, because every uncommented `dtoverlay` loads (App-1-F6 `rework_risk`). So edits stay in place |
| In-place comment / uncomment engine with read-back | `apertar::bootconf`, pure functions, no I/O, about 1000 lines | It does what the image's own comment tells the operator ("uncomment the dtoverlay for your sensor"). The read-back is the safety net that makes a generated write trustworthy |
| `revision` stale-write guard | One plain field on every save (command-plane 10) | Two tabs, or the fan mode, can change the file between load and save. Not a security control |
| Dry-run review with a line diff | `dry_run` on the same command; the page shows the diff with the port's `configDiffLines` | It is the confirm step for a boot file. Upstream confirms system actions with `window.confirm`; the review adds what changes |
| `config.txt.apertar.bak` | One backup, same rule as `saveHardwareConfigFile`'s `.bak` | A bad overlay can stop the boot; the README names the recovery |
| Drive trim | `sudo -n timeout ... fstrim` from Core, no helper | No upstream trim. The call is a fixed tool (PLT-5); the root-side timeout is the one thing a fixed tool needs here |
| `/run/apertar-media` tmpfiles file | `config/apertar-media.tmpfiles.conf`, two lines (decision 12) | A `pi`-owned runtime dir under `/run` needs root once per boot. Upstream helpers make their own `/run` dir as root; Core runs as `pi` |
| `$APERTAR_BOOT_CONFIG` | A path override, as `APERTAR_HARDWARE_CONFIG` upstream | Host tests and `--simulate`. Not new ground in form |
| Host test `tools/boot_config_test.cpp` | Plain `g++`, outside CMake | Decision 9, port-wide |

## For the owner

| # | Question | Options | Recommendation and cost |
| --- | --- | --- | --- |
| 1 | Keep whole-file text editing (Edit file, `text` field)? | A. Remove. B. Keep, refuse boot-chain keys (`kernel`, `cmdline`, `os_prefix`, `initramfs`, `start_file`, `device_tree`, ...) by diffing against the file. C. Keep, but a save needs a press on the touch screen | **A.** Edit file was the only WebUI way to add a parameter the card has no row for. `ccmp` gets a row first (commit 2). `2lane`, `always-on`, `rotation`, `orientation`, `sync-mode` (`imx585-overlay.dts:122-128`) then need `ssh` or the card reader to add; once on a line, the card keeps them. B keeps about 120 engine and 170 page lines, and a deny list is never complete. C is a second confirmation channel upstream has nowhere |
| 2 | Keep Upload (fill the card from a `config.txt` on the laptop)? | A. Remove it and `/api/boot-config/parse` (commit 6). B. Keep | **A.** With 1 A it only copies the card's own values; about 45 lines |
| 3 | Which rows stay? | A. All: sensors, link frequency, RP1 clock, I2C/I2S/SPI/audio, DPI display. B. Sensors, link frequency and RP1 clock only | **A** keeps every feature. B removes about 200 engine lines and the DPI "dark screen" risk; buses and display then need `ssh` again |
| 4 | How is `config.txt` replaced? | A. `sudo -n install` backup + staged copy next to `config.txt` + `sudo -n mv`. B. Two `sudo -n install` calls, the fan mode's shape plus the backup (commit 8). C. A C++ helper in `Apertar-UI/src` per R14, literal verbs, for an image where `pi` lacks `NOPASSWD: ALL` | **B.** It is upstream's shape. Cost: `install` unlinks `config.txt` before it writes the new one, so a power cut in those milliseconds leaves no `config.txt` (the `.apertar.bak` remains), as upstream's fan mode has. A shortens that window to one rename for one more root verb and a leftover dotfile on a failed `mv`; neither is crash-safe on FAT, not measured. C is needed only if the rig has narrow sudo rules (the check before commit 8) |
| 5 | `include camera-selection.txt` on a stock image | A. Sensor rows read-only with one sentence. B. Picking a sensor comments the `include` out and uncomments the overlay, as the image's comment says | **A** now (commit 12). B after a fresh image shows what writes `camera-selection.txt` at boot and whether it puts the include back. About 25 more lines |
| 6 | Keep the wait-for-reboot loop after Save and Reboot? | A. Remove (commit 18); the page reconnects by its 1 Hz poll. B. Keep | **A.** About 45 lines and a third use of `/api/buffer` go |
| 7 | Link labels "up to 50 fps at 4K", "1440 Mbps/lane" | A. Drop (commit 14); MHz plus default / experimental / over RP1 spec. B. Keep a per-sensor fps hint in the page | **A.** The numbers hold for one sensor mode only |
| 8 | Touch UI fan mode goes through Core | A. Keep. B. Restore the UI's own writer (`SystemActionBridge.cpp:431-469@upstream-1.6.0`) | **A.** With the card editing the same file, one writer under `commandMutex_` keeps a fan change from undoing a card save. Stock change to name in the handoff: with Core down, the touch UI's fan mode fails, which 1.6.0 does not. This plan has no UI commit; B would be one |
| 9 | Host tests in `tools/` | Keep outside the build, or drop | Port-wide decision; this theme leaves 15 of 17 (the two shell tests go with their helpers) |
| 10 | Kernel tuning helper | A. Delete (commit 10). B. Rebuild as an R14 helper in the UI repo (not in this plan) | **A.** Off by default (`config/apertar-media-tune.conf:39`), never measured as helping. It is a port feature, so it is your call |
| 11 | Split the engine into `.hpp/.cpp` (commit 21) | Yes with `HardwareConfigText.hpp`, or neither | Yes, together, after hardware-inputs decides |
| 12 | `config/apertar-media.tmpfiles.conf` (a pi-owned `/run/apertar-media/eject`) | A. Keep the file with its two directory lines; Core's eject flag stays best effort. B. Delete the file and the eject-intent flag (`MediaIntent.hpp`): nothing in Apertar reads it (App-1-F14, Media-fault-tune-F4, X-knobs-11) | **A** until a Pi check shows whether the rig's automounter reads the flag: `grep -rn 'apertar-media/eject' /etc/udev /etc/systemd /usr/local/bin 2>/dev/null`. Nothing found -> B, about -40 lines. It is the one install file left in Core with no upstream precedent |
| 13 | One JSON escaper for the Boot Config replies (commit 15) | A. Use `apertar::escapeJson`. B. Keep the header's `jsonString` | **A**, small and net zero. Cost: control characters other than `\b\f\n\r\t` in `config.txt` are no longer `\u`-escaped, the same as every other reply Core sends |

## Risks and what was not determined

- The stock Apertar 1.6.0 `config.txt` is not in this container. Whether it has an active `include camera-selection.txt`, and in which section, is probable from the fixture's comment (`tools/boot_config_test.cpp:56`). Settle with the commit 12 Pi check.
- What writes `camera-selection.txt` is unknown ("No writer in either repo", `working/controls/r3-apertar-readers-ui.md:207`). Decision 5 B waits for that.
- Commit 8 assumes `pi` has `NOPASSWD: ALL`, as upstream's `sudo -n mount` and `install` do. The port README told the owner to install the narrow `apertar-boot-config.sudoers` (`README.md:202-204`). The `sudo -n -l` check runs before commit 8 merges.
- Commit 8 writes in place: `install` unlinks, then writes (strace here). A power cut in that window leaves no `config.txt`; recovery is the `.apertar.bak` from a card reader. Same as upstream's fan mode. Not measured on the Pi.
- Commit 9: whether a `pi` process may signal its own `sudo` process was not determined here (tests ran as root; making a `pi`-like user with a sudoers rule was refused). If `kill` returns `EPERM`, Core cannot end a running trim and a take can start while `fstrim` runs for up to 22 s; the root `timeout` still bounds it, and Core logs the `EPERM` once. The commit 9 Pi check settles it. Smallest safe version if it fails: keep the 22 s bound and add nothing; the first draft's order (`timeout ... sudo -n`) is worse in every case, because a `pi` `timeout` cannot reach a root `fstrim` at all.
- Whether `fstrim` stops promptly on SIGTERM inside the FITRIM ioctl is not checked; the root `timeout -k 2s` is the backstop. `fstrim` at `/usr/sbin/fstrim` on Raspberry Pi OS: probable (the port's own helper used that path).
- `GET /api/boot-config` takes no lock after commit 1, as `GET /api/config` upstream. A read during the milliseconds of a write can see no file; the card then shows "Could not read" until reloaded, and a save from that state is refused by the revision check.
- `set_boot_config` runs two `sudo -n install` calls under `commandMutex_`. That is milliseconds, like upstream's fan mode; a hung `sudo` would hold every command. Upstream accepts the same; no timeout is added.
- Commit 2's dtbo test (the bytes `ccmp` in `imx585.dtbo`) is probable: a compiled overlay keeps its `__overrides__` property names as strings. Check on the Pi: `grep -c ccmp /boot/firmware/overlays/imx585.dtbo` on the port driver (>0) and on the stock driver (0).
- Zero 2 W and `[pi3]` filters: unconfirmed (board-support T5). Commit 11 keeps today's filter rule.
- The IMX585 link options above 891 MHz on a Pi 4 / CM4 come from Cinemate's table; whether the stock imx585 driver accepts them is not checked here.
- Line estimates are from reading the code, not from a trial edit.
- Commits 16-18 touch page helpers (`configDiffLines`, `normalizeSelectEntries`) and names that hardware-inputs and webui-state also touch. Merge order: this theme's 1-16, then webui-state 9, then 17-18.

## Findings covered

| Finding | Commit |
| --- | --- |
| App-1-F4 | 1 |
| App-1-F6 | 4, 14, 19, 21 (size); new ground kept |
| App-1-F7 | 3, 4 |
| Boot-config-F1 | 1 (with command-plane 10) |
| Boot-config-F2 | 8 |
| Boot-config-F3 | 3, 4 |
| Boot-config-F4 | 4, 14, 16, 19, 21; decision 3 for the 600-700 target |
| Boot-config-F5 | 12 |
| WCP-03-F2 | 3, 5, 19; the card stays as new ground |
| WCP-10-F1 | 1 |
| WCP-10-F2 | webui-state commit 9; 17 |
| WCP-10-F3 | 3, 4 |
| WCP-10-F4 | 1 (revision on every door through command-plane 10), 3, 4 |
| X-protocol-security-1 | 3, 4 (the text door is gone, so no deny list is needed) |
| X-board-support-3 | 12 |
| Build-scripts-docs-F4 | 8, 9, 10; tmpfiles: decision 12 |
| Media-buffer-split-F4 | 9 |
| Media-buffer-split-F5 | 9 |
| Media-fault-tune-F2 | 10 |
| X-knobs-10 | 10 (the `kernel_tune` key and `APERTAR_MEDIA_TUNE` parsing: storage-settings) |
| X-knobs-16 | 8, 9 |
| App-1-F8 | 5, 8 |
| App-1-F9 | 7, 14, 16 |
| App-1-F11 | 8 |
| App-1-F12 | 8 |
| App-1-F14 | decision 12 |
| App-1-F16 | 19 (Boot Config part) |
| App-1-F18 | command-plane commit 11 |
| App-3-F1 | 1 |
| App-3-F4 | 1 |
| App-1-F5 | not covered: `errorReplyBody` is command-plane's (its commits 10, 12) |
| Boot-config-F6 | 14 |
| Boot-config-F7 | not covered: kept, decision 8 |
| Boot-config-F8 | 8 |
| Boot-config-F9 | 11 |
| Boot-config-F10 | command-plane 11 (boolean part); the DPI reader in `HardwareConfigText` is hardware-inputs' commit 14 |
| Boot-config-F11 | 13 |
| Boot-config-F12 | 8 |
| Boot-config-F13 | 19 |
| Boot-config-F14 | not covered: decision 9; the helper test goes in 8 |
| Boot-config-F15 | 20 (README); commit history: commit-clarity step |
| Build-scripts-docs-F5 | 8 |
| Build-scripts-docs-F6 | 10 |
| Build-scripts-docs-F12 | 8, 9, 20 (Boot Config and helper recipes only) |
| Driver-imx585-F10 | not covered: driver theme; commit 2 names the follow-up row |
| Media-fault-tune-F4 | decision 12 |
| UI-bridges-F11 | not covered: kept, decision 8 |
| WCP-10-F5 | 5 |
| WCP-10-F8 | 16, 17 (Boot Config part) |
| WCP-10-F11 | 19 (Boot Config banner; the Config page's tags: hardware-inputs) |
| WCP-10-F12 | not covered: Config page Save, hardware-inputs |
| WCP-03-F12 | 19 (Boot Config copy only) |
| X-board-support-4 | 11 |
| X-board-support-6 | 11 |
| X-board-support-11 | 8 |
| X-protocol-security-7 | 1 |
| X-protocol-security-9 | 8, 9, 10 (with 10 declined, `apertar-media.sudoers` stays) |
| App-4-F11 | 10 |
| X-knobs-11 | decision 12 |
| X-knobs-15 | 20 (helper recipes); knob table: storage-settings |
| X-stock-behaviour-11 | 9 (no helper to be missing; a sudo refusal is logged as "failed") |
| HW-config-text-store-F11 | not covered: hardware-inputs (the Controls validator's `config.txt` reader) |
| X-commits-core-1-5 | 10 (the helper); folding the history: commit-clarity step |

## What the challenge changed

Old numbers are the first draft's; new numbers are the list above. Old -> new: 1->1, M1->2, 2->3, 3->4, 4->5, 5->6, M2->7, 6->8, 7->9, 8->10, 9->11, 10->12, 11->13, 12->14 and 15, 13->16, 14 dropped, 15->17, 16->18, 17 dropped, 18->19, 19->20, 20->21.

| Point | Decision | Why |
| --- | --- | --- |
| a. `get_boot_config` as a read twin | Right. New commit 7 deletes it | Upstream's `get_*` are `get_state` and `get_media_test_state` only (`App:9218`, `:10608@upstream-1.6.0`); `GET /api/config` has no twin (`App:7168@upstream-1.6.0`); no client (`App:14602`, `README.md:211` only). It is also in the commands reply (`App:12947`), which the challenge missed |
| a. JSON in the header | Partly right. The builder stays in the header; no move. The label part is commit 14; the escaper is commit 15, owner-optional | Header builders exist upstream (`RecordingCapabilities.hpp:52-60`, `ExposureMetering.hpp:28-39`). The challenge is wrong that a header cannot call `escapeJson`: it is the public `apertar::escapeJson` (`src/ipc/ControlProtocol.hpp:25@upstream-1.6.0`), not App-local. `managed`, `helper`, `drm` already go in commits 4, 8, 5, so 14 is smaller than the challenge's 12a |
| a. `configDiffLines` called upstream's | Right. Commit 16 labels it a port helper; the review stays new ground | No `configDiffLines` or `showConfigDiff` in `core-upstream/src/web/WebControlPage.cpp`; defined at `WCP:18884` in the port |
| a. `sudo -n mv` as default | Right. Commit 8 lands two `sudo -n install` calls; `mv` is decision 4 A | Upstream never runs `mv` as root (`App:3155-3158@upstream-1.6.0`). Measured here: `install` unlinks then creates the target, so B has a no-file window; the cost is now stated in decision 4 |
| a. Board reader | Right. Commit 11 splits on NUL and reads the two paths in PLT-3 order | `bootConfigFacts` reads only `/proc/device-tree/compatible` (`App:3656`); `boardFromDeviceTree` replaces NUL with `,` and searches substrings (`BCT:85-93`) |
| b. command-plane overlap | Right, decided the other way round. command-plane 10 and 11 land first; commit 1 depends on them; the first draft's commit 17 is dropped as command-plane 11; commit 5 deletes the Core display guard that command-plane 10 rewords | `design/command-plane.md` commits 10 and 11 edit `bootConfigSet` and `boolFieldValue` (`App:3709-3841`) and say "either order works". Letting the reply-shape theme own the sentences avoids two revision sentences. The guard goes because upstream confirms only in the page (`WCP:11325@upstream-1.6.0`) |
| b. webui-state overlap | Right. First draft's 14 dropped; 17 and 18 land after webui-state 9 | `design/webui-state.md` commit 9 is the same move and waits for this theme |
| b. hardware-inputs overlap | Right. Commit 11 names it and keeps the dev fallback in `bootConfigFacts`, which hardware-inputs 14 should call | Its commit 14 calls `boardFromDeviceTree` directly (`design/hardware-inputs.md:235-242`). With the fallback in one place, only unknown SoCs change, toward what the firmware does |
| b. Trim kill path | Right. Commit 9 runs `sudo -n /usr/bin/timeout -k 2s 20s /usr/sbin/fstrim` | SIGKILL 1 s after SIGTERM (`App:11959-11965`) ends a `pi` `timeout` before `-k` fires. Not determined (both of us): whether `pi` may signal `sudo` at all; Pi check and risk added. If not, the root `timeout` is still the only bound, so the order holds either way |
| b. Trim discard check | Right. Disk read from the mount at trim time | `mediaProfile_` is set by the watcher (`App:10942-10943`); the helper used `findmnt` at trim time (`scripts/apertar-media-trim:54-70`); `findMountEntry` + `rootDiskForDevice` exist (`MediaProbe.hpp:126`, `:154`). The canonical-path check of the helper is kept too |
| b. `previewState` | Right. Commit 3 deletes it | Its only reader is the marks (`WCP:20499`, `:20556`) |
| b. tmpfiles file | Right. Target table corrected; decision 12 added | `config/apertar-media.tmpfiles.conf` keeps `/run/apertar-media` and `eject`; upstream has no tmpfiles file; storage-settings hands it to this theme (`design/storage-settings.md:489`). The eject flag has no reader in Apertar (App-1-F14), so B (delete) is on the list |
| c. Lost `ccmp` | Right on the loss; the shape differs. New commit 2 adds one sensor choice "IMX585, mono, 12-bit Clear HDR", before Edit file goes | Mono 12-bit Clear HDR needs `mono,ccmp` (`imx585-overlay.dts:138`, `raw/inv-Driver-imx585.md` F5). A sensor choice is the shape `mono` already has (`BCT:386`, `:917-926`), with no new field or page code. It is offered only when the installed dtbo has `ccmp`, so a stock driver never gets an overlay parameter it lacks. Decision 1 names the other options Edit file was the only WebUI route to |
| c. Kernel tune deletes a feature | Right. Commit 10 is owner-optional | The template has `kernel_tune = off`, but the rule is "the features stay" unless the owner agrees |
| c. Rig sudo rights | Right. The `sudo -n -l` check runs before commit 8 merges | The port README installed narrow rules (`README.md:202-204`) |
| d. Commit 1 string conversion | Right. Removed | `parseBareValue` keeps bare values as text (`ControlProtocol.cpp:120-137`); `bootConfigRequestFrom` already reads `"null"` (`App:3728`) |
| d. Commit 5 (Upload) order | Right. Now commit 6, depends on 3 | `/api/boot-config/parse` callers: `WCP:20528` (Upload), `:20578`, `:20604` (Edit file) |
| d. Commit 9 check | Right. Now a host test in commit 11 | Without `$APERTAR_BOOT_CONFIG` the sim reads an absent file and is read-only already (`App:3693-3698`) |
| e. Commit 17 refusal | Moot: the commit is command-plane 11, which keeps the refusal | `boolFieldValue` refuses today; upstream (`App:9486@upstream-1.6.0`) does not |
| f. Decision 4 | Right. Recommendation B, cost stated | See "sudo -n mv" row |
| f. Decision 8 | Right. Stock change stated | Upstream UI wrote the fan block itself (`UI src/SystemActionBridge.cpp:431-469@upstream-1.6.0`) |
| g. Pi checks | Right. Both added, the trim one with `echo kill=$?` to show an `EPERM` | Commit 9 and commit 12 Pi steps |
