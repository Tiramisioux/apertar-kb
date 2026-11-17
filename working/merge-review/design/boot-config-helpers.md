# Boot Config card and the root helpers: design

Read at Apertar-Core `/home/user/wt/core-work` `7dc6f7a` (port `01f170c` + 2 fixes) and Apertar-UI `/home/user/wt/ui-work` `ac1fc28`; upstream at `/home/user/wt/core-upstream` and `/home/user/wt/ui-upstream` tag `upstream-1.6.0`. Every port `path:line` below is `@7dc6f7a` unless marked.

## In short

- Today the Boot Config card (WebUI, System pane) writes `/boot/firmware/config.txt` through its own HTTP route with its own lock, a revision header, status codes 400/403/409/500 and an "is it a browser" rule. The same setter is also a socket command with weaker rules.
- A `text` field lets any LAN client hand Core a whole new `config.txt`, which a root helper then installs. `kernel=`, `os_prefix=`, `initramfs` all pass.
- The editing engine is a 1355-line header that also carries a line diff, managed-line marks, labels and its own JSON writer.
- It does not see `include camera-selection.txt`, the stock image's own way of loading a sensor.
- Three root helpers are `/bin/sh` scripts with sudoers and tmpfiles files in the Core repo. Upstream has `sudo -n <fixed tool>` from Core, and C++ helpers with literal verbs in the UI repo.
- Target: `set_boot_config` is an ordinary `handleCommand` block that the card sends through `POST /api/command`. It writes only lines generated from the card's checked fields. The file is replaced with `sudo -n` and fixed tools, the way upstream's fan mode does it. All three helper scripts go. The engine loses everything the free-text editor needed and its JSON. The sensor overlay, its port, mono and link frequency stay switchable from the WebUI.
- 20 small commits, all in Apertar-Core. No UI commit. Three are owner-optional (5, 16, 20).

## How it works in the port today

The mechanism, read end to end. "Card" = the Boot Config card in the WebUI System pane. "Engine" = `src/hardware/BootConfigText.hpp` (`apertar::bootconf`, header-only, no I/O).

| Value or path | Who writes | Who reads | Thread and lock | File it is saved in | Shown where |
| --- | --- | --- | --- | --- | --- |
| `config.txt` path | `bootConfigPath()` returns `$APERTAR_BOOT_CONFIG` or `kBootConfigPath` (`App:3505-3510`, `:3228`) | every reader below | none | - | card note `payload.path` |
| Card state (sensor per port, link Hz, I2C/I2S/SPI/audio, RP1 clock, DPI display, `camera_auto_detect`) | nobody; read from the file | `bootconf::parseDocument` + `readState` (`BCT:315`, `:512`); `bootConfigJson` (`App:3690-3707`) | web server thread (GET route) or command thread; `bootConfigMutex()` (`App:3513`, `:3769`) | `config.txt` | card selects and pills (`WCP:20122-20258`) |
| `GET /api/boot-config` | - | `bootConfigGet(-1)` (`App:9165-9172`) | web thread, `bootConfigMutex()` | - | `loadBootConfig` (`WCP:20265`) |
| `get_boot_config` command | - | `bootConfigGet(command.id)` (`App:14599-14600`) | inside `handleCommand`, `commandMutex_` (`App:12584`) and `bootConfigMutex()` | - | socket clients |
| Save via `POST /api/boot-config` | page `bootConfigPost` with header `X-Apertar-Revision` (`WCP:20075-20087`) | route splices `"cmd":"set_boot_config"` into the body, `parseControlCommand`, `bootConfigSet(cmd, revision, origin present)` (`App:9174-9199`) | web thread, NOT `commandMutex_`; `bootConfigMutex()` (`App:3785`) | `config.txt` + `config.txt.apertar.bak` | review diff box, toasts |
| Save via `set_boot_config` on socket or `/api/command` | any client | `bootConfigSet(command, revision field, browser=false)` (`App:14602-14603`) | `commandMutex_` + `bootConfigMutex()` | same | - |
| `revision` (FNV-1a of the file) | `bootconf::revisionOf` (`BCT:1343`) | `bootConfigSet`: missing revision refused only when `browser` (Origin header present) is true; wrong revision -> 409 `stale` (`App:3790-3799`) | under `bootConfigMutex()` | - | page keeps `payload.revision` |
| `text` (whole file typed by hand) | card "Edit file" / "Use This Text" (`WCP:20544-20622`), `body.text` (`WCP:20070-20071`) | `bootConfigSet`: `textProblem` (non-empty, 64 KiB, no NUL) then `applyRequest` on top (`App:3803-3816`, `BCT:1133-1139`) | as above | `config.txt` as root | Edit file textarea with italic "managed" marks from `state.managed` (`BCT:498-500`, `:597-620`) |
| `dry_run` review | page `reviewBootConfig` (`WCP:20313`) | `bootConfigSet` returns `changes[]`, `text`, `state`, `drm[]` (`App:3817-3822`) | as above | - | diff box with Save and Reboot / Save Only / Back |
| `confirm_display` | page checkbox gate (`WCP:20341-20352`) | `bootConfigSet` 409 `confirm_display` with `drm[]` (`App:3823-3827`) | as above | - | checkbox "Change the display anyway" |
| Line diff of a hand edit | `bootconf::lineChanges` (LCS, `BCT:1164-1213`), `displayDiffers` (`BCT:1215`) | `bootConfigSet` when `text` is set | as above | - | diff box |
| Upload and live marks | page `uploadBootConfig`, `bootConfigEditorEdited` every 500 ms (`WCP:20523-20586`) | `POST /api/boot-config/parse` (`App:9201-9216`) | web thread, no lock | - | card form, gutter marks |
| The write | `writeBootConfigText` (`App:3533-3610`): (1) direct temp+fsync+rename when writable; (2) `sudo -n /usr/local/libexec/apertar-boot-config < staged`; (3) `sudo -n install` twice (backup, file) | - | caller's thread and locks | `config.txt`, `config.txt.apertar.bak` | error toast; 403 sentence carries two `sudo install` command lines (`App:3602-3607`) |
| Root helper `apertar-boot-config` | `scripts/apertar-boot-config:1-71` (`#!/bin/sh`, text on stdin, refuses a file without `[pi5]`/`[pi4]`/`[all]`) | `sudo` via `config/apertar-boot-config.sudoers:4` | root | - | README install block (`README.md:198-206`) |
| Fan mode | `set_fan_mode` (`App:14608-14616`) -> `applyFanMode` (`App:3620-3649`), managed block `# BEGIN APERTAR FAN MODE` | `currentFanMode` (`App:3612`) into state `fan_mode` (`App:9603`) | `commandMutex_` + `bootConfigMutex()`; now also goes through the helper | `config.txt` | WebUI Thermal card, touch UI Settings |
| Touch UI fan mode | `SystemActionBridge::applyFanMode` sends `set_fan_mode` over its own `QLocalSocket` (`UI src/SystemActionBridge.cpp:66-97`, `:404-409` @`ac1fc28`) | Core as above | GUI thread, 8 s timeout | `config.txt` (by Core) | touch UI Settings |
| Board | `boardFromDeviceTree` by substring of `/proc/device-tree/compatible`; no match -> "pi5" (`BCT:84-97`, `App:3653-3665`) | `filterApplies`, `boardPorts`, `linkOptionsFor` (cap only for "pi4") (`BCT:102-130`, `:182-188`) | caller | - | card note "No Raspberry Pi device tree here" |
| `include camera-selection.txt` | the stock image | nobody: `lineFrom` gives a line without `=` no key (`BCT:288-289`) | - | `config.txt` | not shown |
| Trim helper `apertar-media-trim` | Core `runTrimHelperProcess`: `execl("/usr/bin/sudo","sudo","-n",helper,mountPoint)` (`App:6419-6456`), from `runMediaTrim` (`App:11486-11596`) | `scripts/apertar-media-trim:1-90`, sudoers `config/apertar-media-trim.sudoers:4` (any argument) | trim worker thread, `mediaTrimMutex_`; kill of the sudo pid in `waitForMediaTrim` (`App:11960-11964`) | - | state `media_trim_*` (`App:9587-9589`) |
| Kernel tune helper `apertar-media-tune` | `applyMediaTuning` (`App:11400-11435`), plain `sudo -n`, no timeout, from the media watcher (`App:10946`, `:10967`) | `scripts/apertar-media-tune:1-112`, `config/apertar-media.sudoers:3`, `config/apertar-media.tmpfiles.conf:5` | media watcher thread | `/run/apertar-media/tune/` | journal only; off unless `APERTAR_MEDIA_TUNE=1` or `kernel_tune=on` |

Sizes today: engine 1355 lines; App boot-config code about 200 lines (`App:3502-3843`, routes `App:9164-9216`); card HTML 90 lines (`WCP:5859-5950`) and JS about 740 lines (`WCP:19937-20678`); host tests `tools/boot_config_test.cpp` 427 lines and `tools/boot_config_helper_test.sh` 33 lines.

## How original Apertar does this kind of thing

| Kind of problem | Upstream precedent (`@upstream-1.6.0`) |
| --- | --- |
| A WebUI control that writes `config.txt` | Fan mode. Page: `sendCommand({ cmd: "set_fan_mode", value })` (`WCP:11093`). Core: `if (command.name == "set_fan_mode")` inside `handleCommand` under `commandMutex_` (`App:10568-10577`, lock `App:9093`). Only a generated, fenced block is written (`fanModeBlock` `App:3042`, `stripManagedFanBlock` `App:3084`, `detectManagedFanMode` `App:3104`). |
| Writing a root-owned file | `applyFanMode`: stage a temp file, then `"sudo -n install -m 644 " + shellQuote(tempPath) + " " + shellQuote(kBootConfigPath)` (`App:3127-3175`, call `:3155-3158`). A refusal becomes "Changing the fan mode needs sudo permission." (`App:3164`). No helper, no sudoers file. |
| Simple privileged steps | Fixed tools with `sudo -n` and `shellQuote`: `sudo -n mkdir -p` (`App:3609`), `sudo -n mount` (`App:3636`), `sudo -n blockdev --flushbufs` (`App:3353`). PLT-5. |
| A real root program | Single-file Qt-free C++ in the UI repo (`UI src/StandbyLowPower.cpp`, `StandbyUsbPower.cpp`), sudoers listing every verb (`UI systemd/apertar-standby-usb.sudoers`, `apertar-standby-low-power.sudoers`), called as `/usr/bin/timeout 6s /usr/bin/sudo -n /usr/local/libexec/apertar-standby-usb <verb>` with the comment "Fixed executable and arguments only; never accept paths from WebUI/config." (`App:1541-1549`); Core checks it exists (`App:9152`). PLT-4, R14. |
| A text file the operator edits in the browser | `GET /api/config` and `POST /api/config` -> `saveHardwareConfigFile(request.body, ...)`: non-empty, size cap, no NUL, `.bak`, temp + rename, written as `pi`, never a boot file (`App:7168-7195`, `:5323-5385`). One route each way, status 400 + `errorReply(-1, ...)` on failure. |
| A read of file-like data | Routes return nested JSON where it is a listing (`GET /api/media`, `buildMediaLibraryJson`); a command reply carries at most one object per topic (`imuStatusBody`, `App:130`). Replies are written in App with `escapeJson` (`App:108-128`). |
| Command entry and errors | `POST /api/command` -> `handleWebCommand` -> `handleCommand` (`App:7637-7642`, `:7085-7091`); `okReply` / `errorReply` with one sentence, always HTTP 200. No route reads a custom header or answers 403/409. Origin policy is server-wide (`WS:156-171`). |
| Confirm a system-level action | `if (!window.confirm("Restart the Apertar system now?")) return;` then `sendCommand({ cmd: "restart_system" })` and a toast (`WCP:11325-11334`). No checkbox anywhere. |
| Which sensor the camera has | UI reads `/boot/firmware/camera-selection.txt` first: "Apertar's camera-selection file is authoritative" (`UI src/DeviceInfoBridge.cpp:213-215`), `config.txt` only as the last fallback (`:231`). |
| Board detection | Exact SoC strings `brcm,bcm2712`, `brcm,bcm2711`, `brcm,bcm2837`, ... in `recordingCapabilitiesFromCompatible` (`include/apertar/core/RecordingCapabilities.hpp:18-35`); an unknown platform is not guessed (`src/camera/DefaultTuningSelection.hpp:53`, `:66-69`). |
| Booleans in a command | `*enabled == "true" \|\| *enabled == "1"` by hand (`App:9486`). CMD-8. |
| Select fill and option lists | `ensureSelectEntries` / `normalizeSelectEntries` (`WCP:6210-6230`); option lists are `const` arrays copied by hand into the page (WEB-8). |
| Touch UI asks Core over the socket | `coreMediaCommand` in `UI src/MediaStatusBridge.cpp:20-42`, a synchronous `QLocalSocket` with a timeout. |

Where upstream has nothing: a WebUI editor of sensor overlays in `config.txt`, a dry-run review, a read-back check, a revision check, a reboot wait. That is new ground (below).

## The target

What the feature is after the plan:

- **Entry point.** One write door: the command `set_boot_config` inside `handleCommand`, reached from the socket and from `POST /api/command` (the card uses `sendCommand`). One read twin, as upstream has for state: the command `get_boot_config` and `GET /api/boot-config` call the same builder. No other route.
- **What it may write.** Only lines generated by the engine from checked fields: comment or uncomment the existing `dtoverlay=<sensor>[,cam0][,mono][,link-frequency=<Hz>]` lines and set their parameters, `camera_auto_detect=0`, the four `dtparam` switches, the RP1 clock overlay, the listed DPI overlays. The fan block stays `set_fan_mode`'s. Never caller text.
- **How it is guarded.** `commandMutex_` (one lock for fan mode and Boot Config). A `revision` field, required for every save that is not a dry run, on every door. Read-back: a result that would not load what was asked is refused with the line that decides it. A file with an active `include` line keeps its sensor rows read-only. An unknown board is read-only. A display change is confirmed by the page with `window.confirm`.
- **How it writes.** `sudo -n install` of the backup and of a staged copy next to `config.txt`, then `sudo -n mv` over it. Fixed tools, `shellQuote`d fixed paths, as the fan mode. `$APERTAR_BOOT_CONFIG` (a copy on a dev host) is written by Core itself, the way `saveHardwareConfigFile` writes its file.
- **How big.** Engine about 1000 lines (from 1355); App about 150 (from about 260); card about 520 JS + HTML lines (from about 830). Below 800 for the engine only if the owner drops rows (decision 3).
- **Root helpers.** None in Core. Trim calls `/usr/bin/timeout 20s /usr/bin/sudo -n /usr/sbin/fstrim -v <media root>`. The kernel tuning helper is deleted. A future real root program follows R14: `Apertar-UI/src/<Name>.cpp`, literal verbs, sudoers in `Apertar-UI/systemd/`.

| Value | Before (port) | After |
| --- | --- | --- |
| Card save | `POST /api/boot-config`, header revision, 200/400/403/409/500, `code` field | `sendCommand({cmd:"set_boot_config", ..., revision})` to `/api/command`; `okReply` / `errorReply` sentence; HTTP 200 |
| Lock | `bootConfigMutex()` on the route, both locks on the socket | `commandMutex_` only |
| `revision` | required only when an Origin header is present | required on every non-dry-run save: "set_boot_config requires revision." |
| `text` field, Edit file, Use This Text, managed marks | yes | gone |
| Upload, `POST /api/boot-config/parse` | yes | gone (decision 2) |
| `confirm_display`, `drm[]` | Core 409 + page checkbox | page `window.confirm` naming the effect; Core field gone |
| Review | `changes[]` from Core, own renderer | reply carries the would-be `text`; page shows it with the Config page's `configDiffLines` |
| `set_boot_config` reply | `written, via, changes[], display_changed, text, state{}, revision, reboot_required, drm[]` | `written, dry_run, display_changed, text, revision, reboot_required` (scalars) |
| `get_boot_config` / GET reply | `boot_config{path, readable, revision, helper, backup_path, state{... managed[], sensors[{link{options[{label}]}}]}, drm[], text}` from the engine's `jsonString` | `boot_config{path, readable, revision, backup_path, state{...}, text}` built in App with `escapeJson`; link options are Hz numbers, the page writes the label |
| The write | direct / helper / `sudo -n install` | dev copy: Core writes it; real file: `sudo -n install` backup, `sudo -n install` staged copy, `sudo -n mv` |
| Permission error | two `sudo install ...` command lines | "Writing config.txt needs sudo permission." (fan mode keeps its own sentence) |
| Board | substring, unknown = Pi 5, cap only on Pi 4 | exact SoC strings; unknown = read-only (Pi 5 reading only with `$APERTAR_BOOT_CONFIG`); cap on every board that is not Pi 5-class |
| `include camera-selection.txt` | invisible | read; sensor rows read-only with one sentence |
| IMX283 | missing | listed, no link menu |
| Booleans | `boolFieldValue` (on/yes/off/no) | `== "true" \|\| == "1"`, else "<field> must be true or false." |
| Page store | `const bootConfig = {...}` + `installBootConfigInteractions` | `state.bootConfig*` fields, listeners in `installInteractions` |
| Trim | `sudo -n /usr/local/libexec/apertar-media-trim <mount>` | `/usr/bin/timeout -k 2s 20s /usr/bin/sudo -n /usr/sbin/fstrim -v <mount>`; discard check in Core |
| Kernel tune | `sudo -n /usr/local/libexec/apertar-media-tune ...` | gone |
| Files in Core `scripts/`, `config/` | 3 helpers, 3 sudoers, tmpfiles `tune` line, 2 shell tests | none of them |
| Fan mode `fan_mode` in state, `set_fan_mode` | unchanged | unchanged (same field, same type) |

How a value reaches the UIs: the card reads `GET /api/boot-config` when the System pane opens (as today), saves with `set_boot_config`, re-reads after a save. Nothing of it is in `/api/state` or `get_state`, and the touch UI shows none of it, as today. The touch UI's sensor name keeps coming from `DeviceInfoBridge` (camera-selection file, then sysfs, then `config.txt`).

Old files: nothing moves. `config.txt` keeps its layout. `config.txt.apertar.bak` keeps its name. An installed `/usr/local/libexec/apertar-boot-config` or `/etc/sudoers.d/apertar-*` on the owner's Pi is no longer called and does no harm; the README tells how to remove them. A media tuning file with `kernel_tune = on` keeps loading (the key stays known to the parser until the storage-settings theme decides its fate) and does nothing.

Stock camera: the card only reads until the operator presses Save. No key is added to any file.

## Commit plan

All commits are in Apertar-Core. Each one: `check_core.sh <tree> <tag> both tests` builds with and without libcamera and runs the host tests; `smoke_core.sh` diffs the reply shapes against the previous commit (`/api/state` and `get_state` must not change). "Sim card" below means: copy the fixture text of `tools/boot_config_test.cpp` (`kApertar`) to `/tmp/bc/config.txt`, start `APERTAR_BOOT_CONFIG=/tmp/bc/config.txt apertar-core --simulate --web-port 8091 ...`, open the System pane in headless Chromium, and curl `/api/boot-config`.

### 1. `core, web: set_boot_config is an ordinary command, and the card sends it to /api/command`

- Repo: Core. Files: `src/ApertarCoreApp.cpp` (`bootConfigSet`, `bootConfigGet`, `applyFanMode`, `handleWebRequest`, `handleCommand`), `src/web/WebControlPage.cpp` (`bootConfigPost`, `saveBootConfig`, `reviewBootConfig`, `bootConfigPreviewText`).
- Deleted: the `POST /api/boot-config` branch (`App:9174-9199`), `BootConfigReply` (`App:3761-3764`), the `browser` parameter and the `old_page` 409, `bootConfigMutex()` and its three `lock_guard`s (`App:3513-3517`, `:3628`, `:3769`, `:3785`), the `errorReplyBody` calls and their `code` fields in `bootConfigSet` (now `errorReply(command.id, sentence)`), `result.httpStatus`.
- Changed: `bootConfigSet(const ControlCommand &)` returns `std::string`; a non-dry-run save without `revision` returns "set_boot_config requires revision." `bootConfigPost` becomes `sendCommand({ cmd: "set_boot_config", ... })` with every value a string (`"true"`/`"false"`, Hz as text), wrapped in `try/catch` with `showToast(error.message, true)`. On a failed save the page reloads the file keeping the card's choices (what the `stale` branch did) for any refusal.
- Lines: about -70 / +25.
- Check here: both builds, host tests; sim card: `curl -X POST /api/boot-config` -> 404; `curl /api/command -d '{"cmd":"set_boot_config","cam0_sensor":"imx477"}'` -> "requires revision"; same with `dry_run:"true"` -> ok; Chromium: change the cam0 sensor, Save, Save Only, `diff /tmp/bc/config.txt*`.
- Pi only: Save from the card on the CM5 and reboot; `journalctl -u apertar-core | grep 'boot config'`.
- Depends on: nothing. The command-plane theme decides the future of `errorReplyBody`; this commit only stops using it here.

### 2. `web: the Boot Config card has no Edit file`

- Files: `WCP` HTML `bootConfigEditField`, the `editBootConfigButton` (`WCP:5932-5949`); JS `BOOT_CONFIG_MANAGED`, `bootConfigManagedMap`, `bootConfigManagedSummary`, `bootConfigOwnLinesHint`, `openBootConfigEditor`, `showBootConfigEditorMarks`, `bootConfigEditorEdited`, `closeBootConfigEditor`, `useBootConfigText`, `bootConfig.text/editorMarks/editorTimer`, the `text` line in `bootConfigRequestBody`, the italic marks in `toggleBootConfigFile`, the `marks` parameter of `updateEditorGutter`.
- Moved, deleted: only deletions. View file and Download stay (read-only).
- Lines: about -165 / +5. Core still accepts `text` after this commit; nothing sends it.
- Check here: Chromium: no Edit file button, View file still lists the file; Config page editor gutter still numbers lines.
- Pi only: nothing new.
- Depends on: 1.

### 3. `core: set_boot_config writes only the card's fields`

- Files: `App` `bootConfigSet` (the `text` block `App:3801-3816`), `GET`/state JSON `managed`; `BCT` `textProblem`, `detail::splitLines`, `lineChanges`, `displayDiffers`, `State::managed` and its loop in `readState` (`BCT:597-620`), the "Edit file" comment block; `tools/boot_config_test.cpp` the `managed`, `lineChanges`, `textProblem`, `displayDiffers` checks (about lines 364-414); README sentences on Edit file and `text` (`README.md:195`, `:210`).
- Lines: about -190 / +3 (BCT -115, App -15, test -55, README -5).
- Check here: host test passes with fewer checks; sim card: `set_boot_config` with `text` -> the field is ignored (no change to the file); `grep -c lineChanges src` = 0.
- Pi only: nothing new.
- Depends on: 2.

### 4. `web, core: a display change on the Boot Config card asks with window.confirm`

- Files: `WCP` `reviewBootConfig` (checkbox `gate`, `syncGate`, `drmSummary`), `saveBootConfig` (`window.confirm("Change the display overlays and save? A DPI panel that is the camera's only screen stays dark without them.")` when `review.display_changed`); `App` `bootConfigSet` (`confirm_display` field and its refusal), `drmConnectorsJson` and the `drm` members (`App:3667-3688`).
- Lines: about -55 / +8.
- Check here: Chromium with `page.on("dialog")`: switch Display to Waveshare, Save -> one confirm with that text; dismiss -> file unchanged.
- Pi only: none (no display is switched in the test).
- Depends on: 1.

### 5. `web, core: the Boot Config card has no Upload` (owner-optional, decision 2)

- Files: `WCP` `uploadBootConfigButton`, `bootConfigUploadInput`, `uploadBootConfig`; `App` `POST /api/boot-config/parse` (`App:9201-9216`).
- Lines: about -45 / +0.
- Check here: Chromium: no Upload button; `curl -X POST /api/boot-config/parse` -> 404.
- Depends on: 3.

### 6. `core: config.txt is replaced with sudo -n, as the fan mode always was`

- Files: `App` `writeBootConfigText`, `kBootConfigHelper`, `fsyncPath`, `bootConfigJson` (`helper` member), `bootConfigSet` (`via`, `how`); delete `scripts/apertar-boot-config`, `config/apertar-boot-config.sudoers`, `tools/boot_config_helper_test.sh`; `README.md:196-206` install block.
- New body of `writeBootConfigText(text, errorMessage, permissionDenied)`:
  - `$APERTAR_BOOT_CONFIG` set: copy to `.apertar.bak`, write `<path>.tmp`, rename (the `saveHardwareConfigFile` shape, `App:5359-5383@upstream-1.6.0`).
  - Real file: stage the text in `temp_directory_path()`; `sudo -n install -m 644 <config.txt> <config.txt.apertar.bak>`; `sudo -n install -m 644 <staged> /boot/firmware/.config.txt.apertar-new`; `sudo -n mv -f <that> /boot/firmware/config.txt`. All paths fixed and `shellQuote`d. "password" / "not allowed" / "permission denied" in the output -> `permissionDenied`; `bootConfigSet` says "Writing config.txt needs sudo permission."; `applyFanMode` keeps "Changing the fan mode needs sudo permission."
  - The staged copy plus `mv` keeps the port's "old file or new file after a power cut" goal without a helper. Upstream's single `install` writes in place; decision 4.
- Lines: about -70 / +35 in App; files -108; README -11.
- Check here: both builds; host tests are 16 now (helper test gone); sim card save works on the dev copy and leaves `.apertar.bak`; fan mode on the dev copy (`set_fan_mode` `Silent`) writes the block; `grep -rn apertar-boot-config` = README removal note only.
- Pi only: `sudo -n -l` must show `(ALL) NOPASSWD: ALL` for `pi` (or rules for `install` and `mv`). Card Save on the CM5, then `ls -l /boot/firmware/config.txt*`, `cmp` with the review text, reboot, `vcgencmd get_config str | grep -i overlay` or `dtoverlay -l`, camera starts. Fan mode from the touch UI and the WebUI. On a Pi 4: the same with `[pi4]`.
- Depends on: 3 (no caller sends whole-file text any more).

### 7. `core: the media trim runs fstrim through timeout and sudo -n`

- Files: `App` `runTrimHelperProcess` -> `runFstrimProcess(mountPoint, pidOut, output)`: `execl("/usr/bin/timeout", "timeout", "-k", "2s", "20s", "/usr/bin/sudo", "-n", "/usr/sbin/fstrim", "-v", mountPoint, nullptr)`; `runMediaTrim` (helper path and its "not installed" branch with install lines `App:11512-11518` gone; discard check before the call: `/sys/block/<mediaProfile().rootDisk>/queue/discard_max_bytes` = 0 -> "unsupported", the per-mount latch as today; exit 124 -> "timeout"; output with "password" -> one log line "Trim needs sudo permission." and "failed"); the comment at `App:11437-11441`. Delete `scripts/apertar-media-trim`, `config/apertar-media-trim.sudoers`, `tools/media_trim_test.sh`, `README.md:302-313` install block.
- Why the pid is right now: `mediaTrimPid_` is the `timeout` process, owned by `pi`. `timeout` forwards SIGTERM to `sudo`, `sudo` relays it to `fstrim`, and `-k 2s` kills it if it lingers. Today the SIGTERM goes to `sudo`, which relays it to the script's shell only, and `fstrim` runs on (Media-buffer-split-F5).
- Lines: about -40 / +30; files -135; README -12.
- Check here: both builds; host tests are 15; sim: trim is skipped without a mount (journal "trim ... result=skipped"), the state's `media_trim_*` fields keep their names and types.
- Pi only: delete 2 GiB of clips on the CFexpress card, `journalctl -u apertar-core | grep trim` shows "result=trimmed bytes=..."; during a trim press Record and run `pgrep -a fstrim`: nothing left after the 2 s wait; on a USB stick without discard: "result=unsupported" once.
- Depends on: nothing in this theme. The storage-settings theme owns `APERTAR_MEDIA_TRIM` and `set_media_trim`; this commit leaves them.

### 8. `core: the kernel tuning helper is gone`

- Files: `App` `applyMediaTuning` (`App:11396-11435`), its two calls (`App:10946`, `:10967`), its declaration in `AppH`; delete `scripts/apertar-media-tune`, `config/apertar-media.sudoers`, the `tune` line of `config/apertar-media.tmpfiles.conf:5` (the `eject` lines stay: `src/util/MediaIntent.hpp:15-25` uses them); README `APERTAR_MEDIA_TUNE` row (`README.md:357`).
- Not touched: `kernel_tune` in `src/util/MediaTune.hpp`, `scripts/apertar-tune`, `config/apertar-media-tune.conf`. The storage-settings theme removes or keeps the key; until then it parses and does nothing, so old files load without a warning.
- Lines: about -45 / +0; files -115.
- Check here: both builds; `grep -rn 'apertar-media-tune\b' src` = 0 (the tuning file's own name `apertar-media-tune.conf` stays).
- Pi only: insert and pull the card: the media watcher logs the profile as before, no "tuning helper" line.
- Depends on: nothing. Coordinate with storage-settings.

### 9. `core: the Boot Config card knows the board by its SoC string`

- Files: `BCT` `boardFromDeviceTree` (exact `brcm,bcm2712` -> pi5, `brcm,bcm2711` -> pi4, `brcm,bcm2837` -> pi3, as `recordingCapabilitiesFromCompatible`; no match -> `detected=false`, family empty), `readState` (`!board.detected` -> `editable=false`, "This board is not one the Boot Config card knows. Edit config.txt by hand."), `Sensor::pi4MaxHz` -> `slowBoardMaxHz` applied on every family that is not pi5 (`BCT:186`); `App` `bootConfigFacts`: with `$APERTAR_BOOT_CONFIG` set and no device tree, read as a Pi 5 (the dev host); `tools/boot_config_test.cpp` checks for Pi 3 and unknown.
- Lines: about -15 / +25.
- Check here: host test; sim card without the env var shows "Read Only"; with it, as today.
- Pi only: on a Pi 4 with an IMX477: the link list ends at 500 MHz; on a Zero 2 W / Pi 3, if one is at hand: the card edits `[all]` (test T5 of the board-support sweep for `[pi3]`).
- Depends on: nothing.

### 10. `core: the Boot Config card leaves a sensor from include camera-selection.txt alone`

- Files: `BCT` `lineFrom` (a line `include <file>` gets key `include`, value the file name), `State` gains `std::string cameraProblem`, `readState` (an uncommented `include` in a section that applies -> `cameraProblem = "config.txt includes camera-selection.txt: the sensor comes from that file."`, generic file name in the sentence), `applyRequest` (a sensor or link change while `cameraProblem` is set -> refused with that sentence); `App` JSON `camera_problem`; `WCP` `renderBootConfigPort` disables both sensor selects and shows the sentence; test fixture: the stock comment plus an `include camera-selection.txt` line.
- Lines: about -0 / +30.
- Check here: host test; sim card with an `include` line added to the copy: sensor selects disabled, buses still editable.
- Pi only: on a fresh Apertar 1.6.0 image: `grep -n '^include' /boot/firmware/config.txt; cat /boot/firmware/camera-selection.txt` settles the premise. The owner's CM5 has the include removed, so its card behaves as today.
- Depends on: 3. Decision 5 for the larger option.

### 11. `core: the Boot Config card lists the IMX283`

- Files: `BCT` `sensors()` gains `{"imx283", "imx283", "IMX283", false, 0, 0, {}}`; the comment above it names the sensors without the CameraController function; one test check.
- Lines: -1 / +3.
- Check here: host test; sim card select shows IMX283.
- Pi only: with the imx283 driver installed, pick IMX283 on cam0, reboot, camera starts.
- Depends on: nothing.

### 12. `core, web: the Boot Config JSON is built in App with escapeJson`

- Files: `BCT` `jsonString`, `jsonHz`, `stateJson`, `changesJson` move out; `linkOptionLabel` and the `mbpsPerLane`/`fps4k` members are deleted (`LinkOption` keeps `hz`, `overRp1Spec`, `experimental`); `App` gains `bootConfigStateJson(const bootconf::State &, const bootconf::Facts &)` with `std::ostringstream` and `escapeJson`; `WCP` writes the option label from `hz`: `megahertzText(hz)` + " (default)" / " (experimental)" / " (over RP1 spec)"; test checks of `stateJson` move to a string check of the label inputs.
- The `boot_config` object keeps its shape minus `managed`, `helper`, `drm` and the `label` strings (decision 7). Nested objects stay in this read route, as `/api/media` has them.
- Lines: about -150 / +75.
- Check here: host test; `smoke_core.sh` shape diff of `GET /api/boot-config` shows only the removed members; Chromium: selects and link labels render.
- Depends on: 4, 6.

### 13. `core, web: the Boot Config review is the Config page's line diff`

- Files: `App` `bootConfigSet` reply drops `changes` and `state` (scalars only: `written`, `dry_run`, `display_changed`, `text`, `revision`, `reboot_required`); `BCT` `Change` stays internal (the host test counts edits with it); `WCP` `reviewBootConfig` renders `configDiffLines(payload.text, result.text)` in the same box shape as the Config page's Save (`WCP:18884-18960`), and deletes `bootConfigDiffLine`'s own diff layout.
- Lines: about -45 / +20.
- Check here: Chromium: review lists the same changed lines as before for "imx585 -> imx477".
- Depends on: 12. If the hardware-inputs theme reshapes `configDiffLines` / `showConfigDiff` (WCP-10-F8, WCP-10-F12), this commit uses their shared helper.

### 14. `web: Boot Config fields live in state, its listeners in installInteractions`

- Files: `WCP` `const bootConfig = {...}` -> `state.bootConfigPayload`, `bootConfigForm`, `bootConfigFetchInFlight`, `bootConfigSaveInFlight`, `bootConfigReview`; `installBootConfigInteractions` body moves into `installInteractions` next to `restartSystemButton`.
- Lines: about -25 / +20 (renames).
- Check here: Chromium full card walk.
- Depends on: 2, 13; follows the webui-state theme's naming for second stores.

### 15. `web: Boot Config selects are filled by ensureSelectEntries`

- Files: `WCP` `normalizeSelectEntries` passes `enabled: false` through to `option.disabled`; `renderBootConfigPort` and the display select call `ensureSelectEntries`; `bootConfigOption` deleted.
- Lines: about -20 / +8.
- Check here: Chromium: a missing overlay shows a disabled option.
- Depends on: 14. Shared helper change: tell the webui-state theme.

### 16. `web: Save and Reboot hands over to the restart like the Restart button` (owner-optional, decision 6)

- Files: `WCP` `rebootForBootConfig` becomes `sendCommand({ cmd: "restart_system" })` + toast "Restart requested."; `waitForCameraAfterReboot`, `bootConfigSleep`, `bootConfig.waiting`, the "Rebooting" pill deleted. The page's 1 Hz `fetchState` already shows when the camera is back.
- Lines: about -45 / +5.
- Pi only: Save and Reboot; the page reconnects by itself after the reboot.
- Depends on: 14.

### 17. `core: Boot Config fields use the upstream boolean test`

- Files: `App` `boolFieldValue` deleted; `bootConfigRequestFrom`, `dry_run` read with `== "true" || == "1"`, `== "false" || == "0"`, else "<field> must be true or false."
- Lines: -12 / +8.
- Check here: curl `i2c:"on"` -> refused; `"true"` -> ok.
- Depends on: 1.

### 18. `core, web: Boot Config comments and card copy in the Apertar register`

- Files: `BCT` header essay to two lines, `// ----` banners and Cinemate references out, non-ASCII label glyphs out; `App:3651` banner; `WCP` comment banner (`WCP:19937-19940`), card copy to one sentence ("Sensor overlays, buses and display in config.txt; a change takes effect after a reboot."), RP1 text only in `bootConfigRp1Note`; `tools/boot_config_test.cpp` header line.
- Lines: about -60 / +8.
- Check here: builds; `grep -n -i cinemate src/hardware/BootConfigText.hpp` = 0.
- Depends on: 12.

### 19. `docs: the README says what the Boot Config card does in one paragraph`

- Files: `README.md:179-212` -> one paragraph and the recovery line ("If the camera does not come back, put the card in a reader and copy `config.txt.apertar.bak` over `config.txt`."), the socket-command list out, one line: "Core 1.6.x installed `/usr/local/libexec/apertar-boot-config`, `apertar-media-trim` and their sudoers files; they are no longer used and can be removed."
- Lines: about -30 / +4.
- Depends on: 6, 7, 8.

### 20. `core: the config.txt editor is src/hardware/BootConfig.{hpp,cpp}` (owner-optional)

- Files: `BootConfigText.hpp` -> `src/hardware/BootConfig.hpp` (types, declarations, `namespace apertar::bootconf`) + `BootConfig.cpp` (bodies), `.cpp` listed by name in `add_executable` (HW-23, PLT-1); `tools/boot_config_test.cpp` compile line names `src/hardware/BootConfig.cpp` (the runner reads it from the comment).
- Lines: about -1000 / +1010 (a move).
- Check here: both builds; host test links the `.cpp`.
- Depends on: 18, and on the hardware-inputs theme's decision for `HardwareConfigText.hpp` (same shape); do both or neither.

Order: 1-5 fix the doors and the free text first, so the security gap closes before anything else moves. 6-8 fix the helpers. 9-11 are board and sensor correctness. 12-20 are shape and size. After each the card still switches the sensor overlay on the dev copy and on the Pi.

## What stays as new ground

| Feature | Shape it keeps | Why that shape |
| --- | --- | --- |
| A WebUI card that edits `config.txt` sensor overlays | One settings card in the System pane, one command, one read route | The owner switches IMX585 options from the WebUI on the rig. Upstream only has the fan block; a fenced block cannot switch off an earlier sensor line, because every uncommented `dtoverlay` loads (App-1-F6 `rework_risk`). So edits stay in place |
| In-place comment / uncomment engine with read-back | `apertar::bootconf`, pure functions, no I/O, about 1000 lines | It does what the image's own comments tell the operator ("uncomment the dtoverlay for your sensor"). The read-back is the safety net that makes a generated write trustworthy |
| `revision` stale-write guard | One plain field, required on every save | Two tabs, or the fan mode, can change the file between load and save. It costs 3 lines. Not a security control |
| Dry-run review before a write | `dry_run:"true"` on the same command; the page shows the line diff | It is the confirm step for a boot file. Upstream confirms system actions with `window.confirm`; the review keeps that and shows what changes |
| `config.txt.apertar.bak` | One backup, same rule as `saveHardwareConfigFile`'s `.bak` | A bad overlay can stop the boot; the README names the recovery |
| `$APERTAR_BOOT_CONFIG` | A path override, as `APERTAR_HARDWARE_CONFIG` upstream | Host tests and `--simulate` on a dev machine. Not new ground in form |
| Host test `tools/boot_config_test.cpp` | Plain `g++`, outside CMake | Owner decision 9, shared with the port's other tests |

## For the owner

| # | Question | Options | Recommendation and cost |
| --- | --- | --- | --- |
| 1 | Keep whole-file text editing (Edit file, `text` field)? | A. Remove. B. Keep, refuse boot-chain keys (`kernel`, `cmdline`, `os_prefix`, `initramfs`, `start_file`, `device_tree`, ...) by diffing against the file. C. Keep, but a save needs a press on the touch screen | **A.** Hand edits go back to `ssh` or the card reader, as for every other root file in Apertar. Costs the convenience for lines the card has no row for. B keeps about 120 engine lines and 170 page lines, and a deny list is never complete. C is a second confirmation channel that upstream has nowhere |
| 2 | Keep Upload (fill the card from a `config.txt` on the laptop)? | A. Remove it and `/api/boot-config/parse`. B. Keep | **A.** With A of decision 1 it only copies the card's own values; about 45 lines |
| 3 | Which rows stay? | A. All: sensors, link frequency, RP1 clock, I2C/I2S/SPI/audio, DPI display. B. Sensors, link frequency and RP1 clock only | **A** keeps every feature. B removes about 200 engine lines and the DPI "dark screen" risk; the buses and display then need `ssh` again |
| 4 | How is `config.txt` replaced? | A. `sudo -n install` backup + staged copy + `sudo -n mv` (fixed tools). B. One `sudo -n install` exactly as upstream's fan mode. C. A C++ helper in `Apertar-UI/src` per R14, with literal verbs (for an image where `pi` lost `NOPASSWD: ALL`) | **A.** Keeps the "old or new file after a power cut" property the port's helper wanted, with upstream's shape. B is smaller by two lines and writes in place. C is a new binary, sudoers and install step for a property the stock image does not need |
| 5 | `include camera-selection.txt` on a stock image | A. Sensor rows read-only with one sentence. B. Picking a sensor comments the `include` line out and uncomments the overlay, as the image's own comment says | **A** now (commit 10). B after a fresh image shows what writes `camera-selection.txt` at boot, and whether it puts the include back. About 25 more lines |
| 6 | Keep the wait-for-reboot loop after Save and Reboot? | A. Remove; the page reconnects by its 1 Hz poll. B. Keep | **A.** About 45 lines and a third use of `/api/buffer` go |
| 7 | Link labels "up to 50 fps at 4K", "1440 Mbps/lane" | A. Drop; the label is MHz plus default/experimental/over RP1 spec. B. Keep a per-sensor fps hint in the page | **A.** The numbers hold for one sensor mode only |
| 8 | Touch UI fan mode goes through Core (fails while Core is down) | A. Keep. B. Restore the UI's own writer | **A.** With Boot Config editing the same file, one writer under `commandMutex_` is what keeps a fan change from undoing a card save. Document in the handoff; verify on the Pi |
| 9 | Host tests in `tools/` | Keep outside the build, or drop | Port-wide decision; this theme leaves 15 of 17 (the two shell tests go with their helpers) |
| 10 | Kernel tuning helper | A. Delete. B. Rebuild as an R14 helper | **A.** Off by default, never installed, never measured as helping |
| 11 | Split the engine into `.hpp/.cpp` | Yes with `HardwareConfigText.hpp`, or neither | Yes, together, after the hardware-inputs theme decides |

## Risks and what was not determined

- The stock Apertar 1.6.0 `config.txt` is not in this container. Whether it has an active `include camera-selection.txt`, and in which section, is probable from the fixture's comment (`tools/boot_config_test.cpp:56`). Settle with `grep -n '^include' /boot/firmware/config.txt` on a fresh image.
- What writes `camera-selection.txt` is unknown ("No writer in either repo", `working/controls/r3-apertar-readers-ui.md:207`). Decision 5 B waits for that.
- Commit 6 assumes `pi` has `NOPASSWD: ALL`, as upstream's `sudo -n mount` and `install` do. If the owner's CM5 has only the port's narrow sudoers rules, the card and the fan mode fail with "needs sudo permission". Check `sudo -n -l` before commit 6 lands.
- `mv` over `config.txt` on the FAT boot partition is a rename the kernel's vfat driver does as unlink + rename, not crash-atomic. It is still a much shorter window than an in-place write. Not measured.
- Commit 7: GNU `timeout` forwards SIGTERM to its child and `sudo` relays it to `fstrim`. This is probable from the tools' documentation; run `pgrep -a fstrim` during a forced stop on the Pi.
- `fstrim` is in util-linux on Raspberry Pi OS: probable, not checked here.
- `set_boot_config` now runs `sudo -n install` and `mv` under `commandMutex_`. That is milliseconds, like upstream's fan mode, but a hung `sudo` would hold every command. Upstream accepts the same for the fan mode; no timeout is added.
- Zero 2 W and `[pi3]` filters: unconfirmed (board-support T5). Commit 9 keeps today's filter rule.
- The IMX585 link options above 891 MHz on a Pi 4 / CM4 come from Cinemate's table; whether the stock imx585 driver accepts them is not checked here.
- Line estimates are from reading the code, not from a trial edit.
- Commits 13-15 touch page helpers (`configDiffLines`, `normalizeSelectEntries`) that the hardware-inputs and webui-state themes also touch. Merge order matters.

## Findings covered

| Finding | Commit |
| --- | --- |
| App-1-F4 | 1 |
| App-1-F6 | 3, 12, 18, 20 (size), new ground kept |
| App-1-F7 | 2, 3 |
| Boot-config-F1 | 1 |
| Boot-config-F2 | 6 |
| Boot-config-F3 | 2, 3 |
| Boot-config-F4 | 3, 12, 13, 18, 20; decision 3 for the 600-700 target |
| Boot-config-F5 | 10 |
| WCP-03-F2 | 2, 4, 18; the card stays as new ground |
| WCP-10-F1 | 1 |
| WCP-10-F2 | 14 |
| WCP-10-F3 | 2, 3 |
| WCP-10-F4 | 1 (revision on every door), 2, 3 |
| X-protocol-security-1 | 2, 3 (the text door is gone, so no deny list is needed) |
| X-board-support-3 | 10 |
| Build-scripts-docs-F4 | 6, 7, 8 |
| Media-buffer-split-F4 | 7 |
| Media-buffer-split-F5 | 7 |
| Media-fault-tune-F2 | 8 |
| X-knobs-10 | 8 (the `kernel_tune` key and `APERTAR_MEDIA_TUNE` parsing: storage-settings) |
| X-knobs-16 | 6, 7 |
| App-1-F8 | 4, 6 |
| App-1-F9 | 12, 13 |
| App-1-F11 | 6 |
| App-1-F12 | 6 |
| App-1-F16 | 18 (Boot Config part) |
| App-1-F18 | 17 |
| App-3-F1 | 1 |
| App-3-F4 | 1 |
| App-1-F5 | not covered: `errorReplyBody` belongs to command-plane; commit 1 stops using it here |
| Boot-config-F6 | 12 |
| Boot-config-F7 | not covered: kept, decision 8 |
| Boot-config-F8 | 6 |
| Boot-config-F9 | 9 |
| Boot-config-F10 | 17 (boolean part); the DPI reader in `HardwareConfigText` is hardware-inputs' |
| Boot-config-F11 | 11 |
| Boot-config-F12 | 6 |
| Boot-config-F13 | 18 |
| Boot-config-F14 | not covered: decision 9; the helper test goes in 6 |
| Boot-config-F15 | 19 (README); commit history: commit-clarity step |
| Build-scripts-docs-F5 | 6 |
| Build-scripts-docs-F6 | 8 |
| Build-scripts-docs-F12 | 6, 7, 19 (Boot Config and helper recipes only) |
| UI-bridges-F11 | not covered: kept, decision 8 |
| WCP-10-F5 | 4 |
| WCP-10-F8 | 13, 15 (Boot Config part) |
| WCP-10-F11 | 18 (Boot Config banner; T43 tags of the Config page: hardware-inputs) |
| WCP-10-F12 | not covered: Config page Save, hardware-inputs |
| WCP-03-F12 | 18 (Boot Config copy only) |
| X-board-support-4 | 9 |
| X-board-support-6 | 9 |
| X-board-support-11 | 6 |
| X-protocol-security-7 | 1 |
| X-protocol-security-9 | 6, 7, 8 (all three sudoers files go) |
| App-4-F11 | 8 |
| X-knobs-15 | 19 (helper recipes); knob table: storage-settings |
| X-stock-behaviour-11 | 7 (no helper to be missing; a sudo refusal is logged as "failed") |
| HW-config-text-store-F11 | not covered: hardware-inputs (the Controls validator's `config.txt` reader) |
| X-commits-core-1-5 | 8 (the helper); folding the history: commit-clarity step |
