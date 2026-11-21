# Sweep X4: wire compatibility and the privileged surface

Port: Core `/home/user/Apertar-Core` @cinemate-port (`01f170c`), UI `/home/user/Apertar-UI` @cinemate-port (`7ea9afc`).
Measuring stick: `/home/user/wt/core-upstream`, `/home/user/wt/ui-upstream` @upstream-1.6.0. Merge base: `/home/user/wt/core-main` @main.
`App` = `src/ApertarCoreApp.cpp`. Line numbers are @cinemate-port unless marked `@upstream-1.6.0` or `@main`.

## 0. Verdict in one table

| Question | Answer | Label |
| --- | --- | --- |
| Does a port reply or event break the 1.6.0 touch UI's parser? | No. The 1.6.0 UI parses with `QJsonDocument` (full JSON), not a flat parser (`ui-upstream src/ApertarControlBridge.cpp:1069`, `:1576` @upstream-1.6.0). Nested members parse. Unknown events fall through `applyCoreMessage` (`:1182-1258`) and are ignored (no `ok` key) | confirmed |
| Does a port broadcast flood the 1.6.0 UI? | No. New broadcasts: `buffer` (<= 4 Hz in a take or drain, else on change), `media` (on change), `controls` (per apply). Each is < 1 KiB | confirmed |
| Does a port line exceed a 1.6.0 buffer? | No. The only bounded reader is the preview client, 1 MiB per unterminated line (`ui-upstream src/ApertarPreviewSocketClient.cpp:232`); broadcast lines are small. Big replies (`get_controls`, `set_controls`) go only to their requester, and the 1.6.0 UI never sends those commands | confirmed |
| Line limit 64 KiB -> 1 MiB | Inbound to Core only (`src/ipc/ControlServer.cpp:16`, `:264`; was `:261` @upstream-1.6.0). Harmless to the 1.6.0 UI; only local socket clients can use it | confirmed |
| Is Core's inbound protocol still flat? | Yes. Every new command takes scalars; lists travel as one string (`values=v1,v2`, `resolutions=...`); `set_controls` uses dotted field names `set.<section>.<key>`; `POST /api/boot-config` flattens into the command parser | confirmed |
| Port UI against a 1.6.0 Core | Degrades on missing fields (every new state read is behind `contains()`), but two commands change meaning on an old Core and 7 commands answer "Unknown command" (section 2.3) | confirmed |
| New LAN-reachable root or code-execution paths | Two. (a) `set_boot_config text=` writes any text into `/boot/firmware/config.txt` as root, with no revision guard on `/api/command`. (b) `test_input` fires a configured action from the LAN, and `[run_script] pathN=` (writable from the LAN since upstream) runs any readable file with bash as user pi. Upstream needed a physical button press for (b) | confirmed (pieces), probable (chain) |
| Commands that run without `commandMutex_` | 6: `get_controls`, `controls_history`, `controls_last_input`, `scan_i2c`, `list_actions`, `test_input`. Data read is thread-safe; `get_controls` is not read-only (writes two atomics, erases from a map, spawns `systemctl`). It breaks the upstream rule "one lock for all commands" | confirmed |

## 1. Upstream baseline (what the original developer built)

| Item | Upstream | Evidence |
| --- | --- | --- |
| Command parser | Flat: one object, string or bare values; a bare value ends at `,` or `}`, so a nested `{}`/`[]` value breaks the parse | `core-upstream src/ipc/ControlProtocol.cpp:120-135`, `:204` @upstream-1.6.0 |
| Inbound line limit | 64 KiB, client dropped silently | `core-upstream src/ipc/ControlServer.cpp:261` @upstream-1.6.0 |
| Events | Every event goes to every socket client, preview clients included | `src/ipc/ControlServer.cpp:175-195` (unchanged) |
| UI reply/event parser | `QJsonDocument::fromJson(line)`; event socket reads every line on the GUI thread | `ui-upstream src/ApertarControlBridge.cpp:1064-1092`, `:1570-1586` @upstream-1.6.0 |
| UI preview parser | Hand-rolled `jsonStringValue` over a 1 MiB line buffer; only `preview_buffer`/`preview_frame` are acted on | `ui-upstream src/ApertarPreviewSocketClient.cpp:214-236`, `:334-345` @upstream-1.6.0 |
| WebUI auth | None. A same-origin check refuses cross-site browser requests (`Sec-Fetch-Site: cross-site`, or Origin != Host) | `core-upstream src/web/WebServer.cpp:156`, `:370` @upstream-1.6.0 |
| Root use | `sudo -n` for mount, mkfs, systemctl, timedatectl, hwclock, `sh -c "echo 1 > .../remove"`, and `sudo -n install` of a temp file over `config.txt` for the fan mode. No sudoers file ships; it relies on the stock Raspberry Pi OS `NOPASSWD: ALL` for the first user | `core-upstream App:3031`, `:3157`, `:3205`, `:3239-3292`, `:3353`, `:3373`, `:3609-3636`, `:3810-3816` @upstream-1.6.0; `ls core-upstream/config` = only `apertar-core-capture-priority.conf` |
| LAN writes upstream already allowed | `POST /api/config` replaces `apertar-hardware.conf` (any text, size and NUL check only), so a LAN client could already set `[run_script] path1=` and map it to a GPIO button. Execution still needed a physical press | `core-upstream App:7175-7195` @upstream-1.6.0 |
| Fan mode write | Fixed blocks for fixed modes; LAN chooses only the mode | `core-upstream App:10568-10577` @upstream-1.6.0 |

## 2. Socket protocol

### 2.1 Commands the port added (32; `list_sensor_modes` and `set_clear_hdr` are fork main, not the port)

| Command | App line | Args | Writes / acts | Reply shape (nested members) | Lock |
| --- | --- | --- | --- | --- | --- |
| `get_controls` | 12420 | none | writes `controlsErrors_`/`controlsWarnings_`, erases `pendingUnitSince_`, runs `systemctl show` per pending unit | `controls{issues[],model{},peripherals[{}],i2c_buses[],apply{pending[{}]},dpi_lines[]}`; carries the whole hardware file (<= 256 KiB) | none |
| `controls_history` | 12458 | `name` (allow-listed against the history list, `HardwareConfigStore.cpp:491-497`) | none | `history[{}]` or `text` | none |
| `controls_last_input` | 12476 | none | none | flat | none (`lastInputMutex_`) |
| `scan_i2c` | 12486 | `bus` 0..255 | opens `/dev/i2c-N`, `I2C_SLAVE` (not FORCE) + 1-byte read for 0x03..0x77 (`src/hardware/I2cProbe.cpp:13-37`); refused during a take | `found[{}]` | none |
| `list_actions` | 12534 | none | none | catalog object, `values{iso[],...}`, `gestures{button[],...}` | none |
| `test_input` | 12565 / body 12393 | `section`, `key` | fires the action the saved file assigns to that key, through `handleHardwareInputAction` (which takes the locks itself) | flat | none at entry |
| `list_sensor_modes` | 12724 | (fork main; port adds `binning`, `binning_source`) | none | `modes[{}]` | yes |
| `test_output` | 12745 | `which` = `recording_indicator`/`trigger_output` | one tally blink or one trigger pulse; refused in a take | flat | yes |
| `set_controls` | 12763 | `base` (required), `text` or `set.<s>.<k>`/`unset.<s>[.<k>]`, `restore`, `dry_run`, `force`, `confirm_merge`, `by` | writes `apertar-hardware.conf` (+`.bak`, history); wakes the controls worker, which restarts drivers | `issues[]`, `new_errors[]`, `conflicts[]` (also in the error reply via `errorReplyBody`, a port helper: 0 uses @upstream-1.6.0, 15 in the port) | yes |
| `set_buffer_mode` | 12829 | `value` frames/ram, `base` | `[storage] buffer` in the hardware file | flat | yes |
| `set_frames_per_folder`, `set_clip_merge` | 12857 | `value`, `base` | `[storage]` keys | flat | yes |
| `set_storage_preroll` | 12900 | `value` on/off | `[media] preroll` | flat | yes |
| `set_cdng_log` | 13079 | `value` | camera setting | settings body | yes |
| `set_clear_hdr` | 13150 | (fork main) | | | yes |
| `set_media_trim` | 13194 | `enabled` | camera setting; enables root `fstrim` runs | settings body | yes |
| `set_preview_tdn`, `set_fps_phase_lock`, `set_fps_speed_ramp`, `set_conform_fps` | 13205, 13214, 13223, 13270 | `enabled`/`value` | camera settings | settings body | yes |
| `set_clip_name_template` | 13241 | `value` | camera setting; template restricted to `[A-Za-z0-9._-]` and tokens (`src/util/ClipName.hpp:7`, `:240`, `:258`) | settings body | yes |
| `preview_clip_name` | 13258 | `value` | none | flat | yes |
| `set_recording_frame_enabled`, `set_frame_buffer_bar_enabled`, `set_recording_red_timecode_enabled`, `set_audio_recorded_outline_enabled` | 13505-13512 (`handleUiToggle`) | `enabled` | UI.conf | flat | yes |
| `get_mode_ladder`, `set_mode_ladder` | 14090, 14093 | `resolutions` (one string), `enabled`, `ramp_ready`, `dry_run` | camera setting | `mode_ladder{}` | yes |
| `set_value_steps` | 14110 | `name`, `values` (one string), `free`, `increment`, `flicker_free`, `mains_hz` | UI.conf | flat | yes |
| `get_boot_config` | 14586 | none | none | `boot_config{state{},drm,...}` | yes (+`bootConfigMutex()`) |
| `set_boot_config` | 14589 / body 3775 | toggles, `camN_sensor`, `camN_link_frequency`, `display`, `text` (whole file), `revision` (optional), `dry_run`, `confirm_display` | root write of `/boot/firmware/config.txt` | `changes[]`, `state{}`, `drm` | yes |
| `storage_preroll` | 14603 | `seconds` | records and deletes a throw-away clip on the medium | flat | yes |

### 2.2 Upstream commands whose arguments or reply changed

Diffed block by block against @main (script: `blocks.py` in the session scratchpad; it compares each `if (command.name == "...")` block).

| Command | Change | Effect on the 1.6.0 UI |
| --- | --- | --- |
| `get_state` | adds `recording_fault`, `recording_dropped_frames`, `controls_errors`, `controls_warnings`, sensor binning, `sensor_mono`, `media_alive`, `clip_merge_*`, and `media_state` **twice** (`App:12944` and `App:12961`) | none (Qt keeps the last key); duplicate key is a defect |
| `settings` body/event | 32 keys added, 0 removed (42 -> 74). One new nested member: `ladder_tops` (number array, `App:334`) | none |
| `set_iso_auto` | new optional `enabled`; absent = on (as before) | none |
| `set_timecode_mode` | new optional `target` = ui/files/both; absent = both (as before) | none |
| `record_start`, `record_stop` | reply adds `recording_dropped_frames`; `record_stop` during a storage pre-roll answers `"recording":false,"storage_preroll_stopped":true` | none |
| `format_media` | also starts a storage pre-roll afterwards | behaviour, not wire |
| `capture_photo`, `record_start`, `timelapse_start` and media actions | new guards: delete running, pre-roll running, trim/merge wait up to 5 s each (`App:12586-12620`) | new error sentences; the 1.6.0 UI shows them as `lastError` |
| `set_fan_mode` | now goes through `writeBootConfigText` (helper first, then `sudo -n install`) | none |
| `help` | lists the new commands | none |

### 2.3 Port UI against a 1.6.0 Core

| Port UI sends | 1.6.0 Core does | Result | Label |
| --- | --- | --- | --- |
| ISO "Lock": `set_iso_auto enabled=false` (`Apertar-UI src/ApertarControlBridge.cpp`, diff line `+if (!sendCoreCommand("set_iso_auto", {{"enabled","false"}}))`) | ignores `enabled`, calls `setIsoAuto()`, which sets `isoAuto = true` (`core-upstream App:9269-9273`, `src/camera/CameraController.cpp:7788-7794` @upstream-1.6.0) | Lock turns auto ISO **on**: the opposite | confirmed |
| `set_timecode_mode target=ui` (`Apertar-UI src/ApertarControlBridge.cpp:759`) | ignores `target`, changes the file timecode too (`core-upstream App:9424-9436`) | the files change when the operator meant the screen only | confirmed |
| `storage_preroll`, `set_storage_preroll`, `set_clip_name_template`, `preview_clip_name`, `set_buffer_mode`, `set_cdng_log`, `set_clear_hdr` | `Unknown command: <name>` | shown as `lastError`; nothing else breaks | confirmed |
| reads `media_state`, `buffer_*`, `storage_preroll_*`, `cdng_log*`, `clip_name_*`, `controls_errors`, `iso_max`, ... | absent | every read is behind `state.contains(...)`; defaults keep the old behaviour (`m_coreMediaAlive = true`, `MediaStatusBridge.hpp:140`) | confirmed |
| live poll 1 Hz while auto ISO or auto WB (`kLiveValuePollIntervalMs = 1000`, `:20`, used `:1016`; upstream steady poll is 30 s, `:18`) | answers | 30x more `get_state` under `commandMutex_`, twice if the HDMI process runs the same bridge | confirmed |
| fan mode through `set_fan_mode` (`Apertar-UI src/SystemActionBridge.cpp`) | supported since 1.6.0 | works; this is closer to upstream than the old UI's own file write | confirmed |

### 2.4 Events

| Event | Where | Rate | Members | 1.6.0 UI |
| --- | --- | --- | --- | --- |
| `buffer` | `App:11033`, `:11038`, `:11045` (thread `runBufferEvents`, `App:10992`) | on change, loop 250 ms in a take/drain/pre-roll (<= 4 Hz), 1 s idle | flat (`bufferMembers`, `App:301-311`; `bufferEventJson`, `App:10839`) | ignored |
| `media` | `App:10911` (`runMediaWatcher`) | on change of medium/state; loop 1 s idle, 250 ms recording | flat (`App:10824-10835`) | ignored |
| `controls` | `App:12346` | once per applied hardware-file change | flat | ignored |
| `recording` (sound only) | `App:10072`, `:10084` | per take | flat | handled as before |

All four are added to the broadcast list in `publishEvent` (`App:14883-14897`). The list is a chain of `find("\"event\":\"...\"")` on every event; the port lengthened it from 9 to 14 tests.

## 3. HTTP routes

### 3.1 Route table (port), changes against @upstream-1.6.0

| Method path | App line | Status | Reads / writes | Validation | Missing |
| --- | --- | --- | --- | --- | --- |
| GET `/api/buffer` | 8419 | new | `camera_.frameBufferStatus()` (atomics, one `try_lock`) | none needed | none |
| GET `/api/media/clip` | 8442 | new | clip facts of a folder under the media root | `resolveMediaLibraryPath` (`App:6626`: `isSafeMediaRelativeId` rejects `/`-leading, `\`, NUL, `.`/`..` segments; `pathIsInsideRoot` compares `weakly_canonical` paths, so symlinks out of the root are refused), `kind=folder`, `is_directory` | none |
| GET `/api/media/frame` | 8475 | new | decodes one DNG of a clip to JPEG | same id check; `n`, `w` digits only, `w` in an allow-list; playback hold; `v` token | decoder robustness against a crafted DNG on the medium is not in this sweep |
| GET `/api/media/file` | 8550 | new | streams `<clip>/<name>.wav` with Range | same id check; `name` ends `.wav`, no `/`, `\`, `..`, NUL; `symlink_status` must be a regular file (a symlinked WAV is refused) | none found |
| GET `/api/config` | 8613 | upstream | hardware file | | |
| POST `/api/config` | 8620 | changed | hardware file through the store (revision, merge, history, `.bak`); a browser without `X-Apertar-Revision` gets 409 | size 256 KiB, NUL, non-empty (`App:6231-6252`) | content is not restricted (upstream same) |
| GET `/api/media/download`, `/download-selected` | 8682, 8811 | changed | adds the playback hold; id checks unchanged | | |
| POST `/api/media/delete`, `/delete-selected` | 9004, 9087 | changed | adds `mediaDeleteActive_`, trim request; id checks unchanged | | |
| GET `/api/boot-config` | 9161 | new | reads `config.txt` | none needed | none |
| POST `/api/boot-config` | 9170 | new | root write of `config.txt` | body flattened into the command parser; browser must send a revision; `textProblem` (non-empty, <= 64 KiB, no NUL; `src/hardware/BootConfigText.hpp:1133-1139`) | no content check in Core; see X-protocol-security-1 |
| POST `/api/boot-config/parse` | 9200 | new | parses an uploaded `config.txt`, writes nothing | <= 64 KiB, no NUL | none |
| POST `/api/command` | 9214 | upstream | every socket command, including the new ones | none beyond each command | `set_boot_config` here has no revision requirement (`browser=false`, `App:14590`) |
| presets, icons, `/`, `/preview.mjpeg`, OPTIONS | | unchanged | | | |

Methods stay GET/POST/OPTIONS. The WebServer change is three reason phrases (206, 409, 416), `src/web/WebServer.cpp:61-71`.

### 3.2 Privileged and code-running surface reachable from the LAN

| Path | Entry from the LAN | Runs as | Port validation | Gap | Label |
| --- | --- | --- | --- | --- | --- |
| `config.txt` replace | `set_boot_config text=...` via `/api/command` or `POST /api/boot-config` | root (helper, else `sudo -n install`, `App:3571-3608`) | Core: non-empty, <= 64 KiB, no NUL. Helper: same, plus one line matching `^\s*\[(pi5\|pi4\|all)\]` (`scripts/apertar-boot-config:37-54`) | Any boot directive (`kernel=`, `cmdline=`, `os_prefix=`, `dtoverlay=`, `initramfs`) can be written; the helper's section check is skipped whenever the helper is missing or sudo refuses it, because Core then falls back to `sudo -n install`; `/api/command` needs no revision. Upstream let the LAN pick only one of fixed fan blocks | confirmed |
| Script run | `POST /api/config` or `set_controls` writes `[run_script] path1=<file>` and `[gpio_buttons] remote0=run_script1`; `test_input section=gpio_buttons key=remote0` fires it | user pi; with the stock `NOPASSWD: ALL`, root | `test_input` only checks the key exists and is mapped; `remoteN` rows skip the section-on check (`App:12404`, `ControlsModel.hpp:204-207`). The runner accepts any absolute, regular, readable file and runs `/bin/bash -- <file>` (`src/hardware/HardwareScriptRunner.cpp:86-90`, `:231-236`) | No allow-list of script directories, no executable bit, no owner check. A file the LAN can fill (for example `config.txt` above: bash skips `[all]` and `key=value` lines and runs the rest) becomes code | pieces confirmed; chain probable (not run on a Pi) |
| Media trim | automatic after deletes and mounts; switch via `set_media_trim` | root (`/usr/local/libexec/apertar-media-trim` via `sudo -n`, `App:6414-6432`) | argument from `options_.mediaRoot`, not from the client; helper: exactly one arg, under `/media/`, no `..`, `[A-Za-z0-9._/-]` only, canonical, a mount point, discard-capable, 20 s timeout (`scripts/apertar-media-trim:21-87`) | none found | confirmed |
| Media tune | automatic on mount/unmount when `kernel_tune = on` | root (`App:11423`) | args from Core; helper rejects `/`, `..`, empty root disk; class from a fixed table; writes only `/sys/block/<disk>/queue/*`, `/proc/sys/vm/dirty_*`, nvme APST (`scripts/apertar-media-tune:34-108`) | root disk name has no character class check (only `/` and `..`); harmless because the path is quoted | confirmed |
| `scan_i2c` | `/api/command` | pi | bus 0..255, not in a take; `I2C_SLAVE` (kernel-bound addresses return EBUSY, not read) | a 1-byte read of every free address on any bus, without the command lock: a take can start during the scan | confirmed |
| `test_output` | `/api/command` | pi | fixed `which`, not in a take, output must be on | none | confirmed |
| `test_input` | `/api/command` | pi | see Script run | it also fires `eject` and every other mapped action from the LAN | confirmed |
| `storage_preroll` | `/api/command` | pi | `seconds` parsed; gated with the capture guards | none | confirmed |

### 3.3 sudoers files the port ships

| File | Rule | Arguments | Abuse |
| --- | --- | --- | --- |
| `config/apertar-boot-config.sudoers` | `pi ALL=(root) NOPASSWD: /usr/local/libexec/apertar-boot-config ""` | none allowed (`""`) | stdin is the new `config.txt`; see the gap above |
| `config/apertar-media-trim.sudoers` | `pi ALL=(root) NOPASSWD: /usr/local/libexec/apertar-media-trim` | any (helper validates) | none found |
| `config/apertar-media.sudoers` | `pi ALL=(root) NOPASSWD: /usr/local/libexec/apertar-media-tune` | any (helper validates) | none found; `APERTAR_MEDIA_RUN_DIR` is dropped by sudo's `env_reset` |

The three rules only matter on a Pi where pi lost the stock `NOPASSWD: ALL`; upstream Core needs that rule anyway (mount, mkfs, systemctl, `sh -c`). Upstream ships no sudoers file. New ground: they are narrower than what upstream already requires, so they add no privilege, but they suggest a hardening that Core does not have.

## 4. Commands that answer before the command lock

`handleCommand` (`App:12559-12571`) calls `handleReadOnlyHardwareCommand` (`App:12418-12556`) and `testInputReply` before `std::lock_guard<std::mutex> commandLock(commandMutex_)`. Upstream: one lock, taken on the first line, no command body before it (`core-upstream App:9093` @upstream-1.6.0; conventions C1-S03).

| Command | Reads | Writes | Safe? |
| --- | --- | --- | --- |
| `get_controls` | config store (`info()`, own mutex), input/output `enabled()`/`lastError()` (each under `stateMutex_`, e.g. `GpioInput.cpp:247-251`), `/dev` listing, `config.txt` (replaced by rename, so a read sees one whole file) | `controlsErrors_`, `controlsWarnings_` (atomics); `pendingUnitSince_` erase under `controlsWorkerMutex_`; spawns `systemctl show` per pending unit | data race free; not read-only as named; parses the same text 8 times (`hwconf::parse(info.text)` repeated, `App:12434-12444`) |
| `controls_history` | store history | none | yes |
| `controls_last_input` | `lastInput_` under `lastInputMutex_` | none | yes |
| `scan_i2c` | config store, driver `enabled()`, `recordingGateActive()` | I2C reads | the take check and the scan are not atomic; a driver restarted by the controls worker can start on an address between the `held` set and the probe |
| `list_actions` | `readSharedUiSettings()`, `camera_.settings()` (controller mutex), sensor name | none | yes |
| `test_input` | store text | dispatches actions that take `hardwareInputSequenceMutex_` -> `commandMutex_` themselves | yes; it must stay outside the lock or it would deadlock |

## 5. Findings

| Id | Title | Sev | Category |
| --- | --- | --- | --- |
| X-protocol-security-1 | LAN client can write any text into `/boot/firmware/config.txt` as root | major | security |
| X-protocol-security-2 | LAN can run any readable file with bash through `test_input` + `[run_script]` | major | security |
| X-protocol-security-3 | Port UI "Lock" ISO turns auto ISO on against a 1.6.0 Core | minor | protocol |
| X-protocol-security-4 | `set_timecode_mode target=` silently ignored by a 1.6.0 Core | nit | protocol |
| X-protocol-security-5 | Six commands run before `commandMutex_`; `get_controls` is not read-only | minor | mismatch |
| X-protocol-security-6 | `get_state` emits `media_state` twice | minor | bug |
| X-protocol-security-7 | Two doors to `set_boot_config` with different guards; HTTP route wraps the command parser | minor | mismatch |
| X-protocol-security-8 | Port UI polls `get_state` at 1 Hz while auto ISO/WB is on | nit | protocol |
| X-protocol-security-9 | sudoers files are new ground and imply a hardening Core does not have | nit | new-ground |
| X-protocol-security-10 | Nested replies added beyond upstream's fixed list | nit | protocol |

Details and fixes are in the structured result; summary of fixes:

1. Build the new `config.txt` in Core from the card's fields only (the `bootconf::applyRequest` path) and drop `text=` from `set_boot_config`, or refuse a `text` whose directives are outside an allow-list (`dtoverlay`/`dtparam` names the card manages, `camera_auto_detect`, `display_auto_detect`, `[pi4]/[pi5]/[all]`). Never fall back to `sudo -n install` for the free-text path. Require `revision` on every save, as `POST /api/boot-config` does for browsers.
2. Keep `test_input` off `run_script*` (and off `eject`): refuse an action list that holds a script action, the way upstream refuses nothing because it had no remote trigger. Or restrict `[run_script]` paths to one directory owned by pi (for example `~/apertar-scripts/`), executable, not world-writable.
3. Port UI: send `set_iso` with the ISO in use for Lock, or check the reply's `iso_auto` and fall back.
4. Port UI: read `target` back from the reply, or accept that an old Core sets both.
5. Put the six commands under the lock, except `test_input`; move the I2C scan to a worker like the media speed test (C1-S20) if it is slow. Parse the hardware text once in `get_controls`; move the `systemctl` probe to the controls worker.
6. Delete `App:12944`.
7. Let `POST /api/boot-config` and `/api/command` share one guard set (revision required for any write).

## Skeptic

Re-read on both sides: port `/home/user/Apertar-Core` and `/home/user/Apertar-UI` @cinemate-port (`01f170c`, `7ea9afc`), original in `/home/user/wt/core-upstream` and `/home/user/wt/ui-upstream` @upstream-1.6.0.

| Id | Verdict | What changed |
| --- | --- | --- |
| X-protocol-security-1 | stands, corrected | Lines confirmed (`App:3775-3850`, `:3532-3608`, `:9170-9198`, `:14589-14590`; `BootConfigText.hpp:1133-1139`; helper `:37-54`). Upstream confirmed: `applyFanMode` builds the text from `fanModeBlock(mode)` (`core-upstream App:3142-3157`). Correction: the `revision` check is a stale-write guard, not a security control (any client can read the revision with `get_boot_config` first), so it moves to X-7. The "Edit file" text path is a deliberate card feature, so an allow-list of only card keys would remove it; the fix is a deny-list of boot-chain keys plus no `sudo -n install` fallback. Upstream also trusts the LAN by design (C1-N10), which is why this is major and not blocker |
| X-protocol-security-2 | stands, corrected | Confirmed: `testInputReply` (`App:12393-12415`) calls `handleHardwareInputAction` (`App:12410`); upstream calls it only from the GPIO/NeoRotary/PCF callbacks and the standby wake (`core-upstream App:6786-6792`, `:8613`). Runner checks unchanged from upstream (`core-upstream HardwareScriptRunner.cpp:88-89`, `:238`); the runner re-reads the file path at each request (`App:10333`), so a saved file is live at once. Correction: `eject` is no new reach (upstream has `eject_media` on `/api/command`), so it leaves the fix. Restricting runner paths changes stock behaviour that upstream already ships; it is a second, optional step, not the fix |
| X-protocol-security-3 | stands, corrected, minor -> nit | "Lock" is offered only while ISO is Auto (`Apertar-UI qml/CameraPage.qml:531`). Against a 1.6.0 Core `set_iso_auto` ignores `enabled` (`core-upstream App:9269-9273`), so Lock leaves auto on: a silent no-op, not "the opposite". The proposed fix "send `set_iso` with `iso_actual`" does not work against 1.6.0: upstream sends no `iso_actual` (`grep iso_actual core-upstream/src/ApertarCoreApp.cpp` = 0 hits). Mixed new-UI/old-Core install only |
| X-protocol-security-4 | stands, nit | Confirmed (`ApertarControlBridge.cpp:750-771`; `core-upstream App:9424-9436` sets both). The UI's state handler re-reads `timecode_mode` into `m_fileTimecodeMode` on the next `get_state` (`ApertarControlBridge.cpp:1698-1705`), so the wrong belief lasts until the next poll. Mixed install only |
| X-protocol-security-5 | stands, minor | Confirmed (`App:12559-12571`, `:12418-12556`, `:12353-12380`; `controlsErrors_`/`controlsWarnings_` are atomics `ApertarCoreApp.hpp:174-175`; `pendingUnitSince_` under `controlsWorkerMutex_`). No data race; the issue is the convention C1-S03 and the scan/take race. The comment at `App:12417` says the lock-free path is deliberate |
| X-protocol-security-6 | stands, minor -> nit | `App:12944` `media_state` from `mediaSnapshot()` and `App:12961` from `mediaState`, same `<<` chain. Upstream `get_state` has no `media_state` key at all (0 hits), so the key itself is port-added. Last key wins in Qt and JS; no consumer breaks: nit |
| X-protocol-security-7 | stands, minor | Confirmed. Takes over the `revision` part of X-1. Note: `/api/command` from a same-origin browser page also reaches `bootConfigSet(..., false)`, so the browser rule is bypassed by the WebUI's own other door |
| X-protocol-security-8 | stands, nit | Confirmed (`ApertarControlBridge.cpp:18-20`, `:1012-1018`). Fix unchanged |
| X-protocol-security-9 | stands, nit | Confirmed: 3 files, rules as quoted; upstream has only `config/apertar-core-capture-priority.conf` and calls `sudo -n` on fixed helpers and tools (`core-upstream App:1544`, `:1549`, `:3031`, `:3157`, `:3205`). Note: upstream itself already calls two root helpers in `/usr/local/libexec/` (`apertar-standby-usb`, `apertar-standby-low-power`), so the helper pattern is upstream's; only the sudoers files are new |
| X-protocol-security-10 | dropped | Premise wrong. Upstream's `settingsBody` already carries an array (`exposure_metering_modes`, conventions 5.5) and replies carry `modes` (array of objects), `favorites_order` (array), `state` (object). The "comma-separated string" rule (C1-I09) is for commands in, not replies. `ladder_tops` as a number array follows `exposure_metering_modes`. The WebUI-only nested replies follow `modes`/`state`. The one real addition, `errorReplyBody` with extra members in error replies (`App:173-181`, 15 call sites; upstream `errorReply` is `{ok,id,error}` only, `core-upstream App:120-126`), is a documentation item for the handoff, not a finding |

Nothing new and serious found beyond the list.

## Final findings

### X-protocol-security-1 [security, major, deliberate: yes, effort M] Any LAN client can write arbitrary text into /boot/firmware/config.txt as root
where: `src/ApertarCoreApp.cpp:3775-3850` (bootConfigSet); `src/ApertarCoreApp.cpp:3532-3608` (writeBootConfigText); `src/ApertarCoreApp.cpp:14589-14590`; `src/ApertarCoreApp.cpp:9170-9198`; `src/hardware/BootConfigText.hpp:1133-1139`; `scripts/apertar-boot-config:37-54`
detail: `set_boot_config text=` carries the whole file (the card's "Edit file"). Core checks only non-empty, <= 64 KiB, no NUL (`textProblem`), applies the card's choices on top (`applyRequest`), and writes as root through the helper; when the helper is missing or sudo refuses it, Core falls back to `sudo -n install` (`App:3594-3608`), which skips even the helper's one content check (a `[pi5]`/`[pi4]`/`[all]` line). Any directive can be written: `kernel=`, `cmdline=`, `os_prefix=`, `initramfs`, `start_file=`, `dtoverlay=`. Result: the LAN controls the boot chain persistently and can at least leave the Pi unbootable. Upstream @upstream-1.6.0: the LAN picks one of fixed fan modes and Core builds the block (`core-upstream App:3142-3157`, `:10568-10577`). Both versions trust the LAN (same-origin check only, `core-upstream src/web/WebServer.cpp:156-170`; C1-N10), so the gap is the new reach, not missing authentication. The `revision` check does not help: any client reads it with `get_boot_config` first (see X-7). Confirmed in code.
fix: In `bootConfigSet`, after `textProblem`, refuse `text` that sets a boot-chain key (`kernel`, `cmdline`, `os_prefix`, `initramfs`, `start_file`, `fixup_file`, `device_tree`, `overlay_prefix`, `boot_*`) unless the key's line is unchanged from the file on disk (`bootconf::lineChanges` already gives the changed lines): `return {400, errorReplyBody(command.id, "config.txt: " + key + " is not changed from the WebUI.", "\"code\":\"refused\"")};`. In `writeBootConfigText`, drop the `sudo -n install` fallback: no helper, no write, with the existing "Install the helper" message. Give `textProblem` the helper's section check so both refuse the same.

### X-protocol-security-2 [security, major, deliberate: no, effort S] test_input lets the LAN run any readable file with bash, without a button press
where: `src/ApertarCoreApp.cpp:12393-12415` (testInputReply); `src/ApertarCoreApp.cpp:12565-12566`; `src/ApertarCoreApp.cpp:10330-10334`; `src/hardware/ControlsModel.hpp:141-145`, `:204-207`; `src/hardware/HardwareScriptRunner.cpp:86-90`, `:231-238`; `src/ApertarCoreApp.cpp:8620` (POST /api/config)
detail: `test_input section=gpio_buttons key=remote0` runs what the saved file maps to that key through `handleHardwareInputAction` (`App:12410`); `remoteN` rows skip the section-on check (`App:12404`). A LAN client can save `[run_script] path1=<file>` and `[gpio_buttons] remote0=run_script1` with `POST /api/config` or `set_controls`; the runner re-reads the path on each request (`App:10333`), accepts any absolute, regular, readable file and runs `/bin/bash -- <file>` as pi, which is root through the stock `NOPASSWD: ALL`. With X-1 the LAN can fill `config.txt` with shell lines (bash skips `[all]` with an error and treats `key=value` as assignments). Upstream @upstream-1.6.0: the runner checks are the same (`core-upstream src/hardware/HardwareScriptRunner.cpp:88-89`, `:238`), but `handleHardwareInputAction` is called only from the GPIO, NeoRotary, PCF8574 callbacks and the standby wake (`core-upstream App:6786-6792`, `:8613`): a script ran only on a physical press. Each piece confirmed in code; the end-to-end chain is probable (not run on a Pi).
fix: In `testInputReply`, before `handleHardwareInputAction`, refuse an action list that holds a script action: `for (const auto &a : line.actions) if (hardware::scriptActionSlot(a) >= 0) return errorReply(command.id, "Scripts run from a button, not from the WebUI.");`. Optional second step (changes stock runner behaviour, discuss with the original developer): require the script to be executable and not group- or world-writable.

### X-protocol-security-3 [protocol, nit, deliberate: unknown, effort S] Port UI ISO "Lock" does nothing against a 1.6.0 Core
where: `Apertar-UI src/ApertarControlBridge.cpp:300-308` (applyIso, Lock branch); `Apertar-UI qml/CameraPage.qml:531`; `core-upstream src/ApertarCoreApp.cpp:9269-9273`
detail: Lock is offered only while ISO is Auto (`CameraPage.qml:531`) and sends `set_iso_auto enabled=false`. The port Core reads `enabled` (`App:12995-13001`); a 1.6.0 Core ignores it and calls `setIsoAuto()`, so ISO stays auto while the UI reports success and saves settings. Upstream sends no `iso_actual`, so the UI cannot know the gain in use from an old Core. Mixed install (new UI, old Core) only. Confirmed.
fix: After the Lock command, check the reply: `if (reply.value("iso_auto").toBool()) { setLastError(QStringLiteral("Lock needs a newer ApertarCore.")); return false; }` (pass `&reply` to `sendCoreCommand`). Or offer "Lock" in `CameraPage.qml` only when the state carries `iso_actual`.

### X-protocol-security-4 [protocol, nit, deliberate: unknown, effort S] set_timecode_mode target= is ignored by a 1.6.0 Core
where: `Apertar-UI src/ApertarControlBridge.cpp:750-771`; `core-upstream src/ApertarCoreApp.cpp:9424-9436`
detail: The port UI sends `target=ui` to change only the screen timecode. A 1.6.0 Core ignores `target` and changes the file timecode too; the UI keeps `m_fileTimecodeMode` unchanged until the next `get_state` corrects it (`ApertarControlBridge.cpp:1698-1705`). Mixed install only. Confirmed.
fix: Take the reply (`&reply`) and update `m_fileTimecodeMode` from its `timecode_mode`, the way the state handler at `:1698` does, instead of from `target`.

### X-protocol-security-5 [mismatch, minor, deliberate: yes, effort M] Six commands run before commandMutex_; get_controls is not read-only
where: `src/ApertarCoreApp.cpp:12559-12571`; `src/ApertarCoreApp.cpp:12418-12556`; `src/ApertarCoreApp.cpp:12353-12380` (controlsApplyJson)
detail: `get_controls`, `controls_history`, `controls_last_input`, `scan_i2c`, `list_actions` and `test_input` answer before the lock. Upstream takes the lock on the first line of `handleCommand` (`core-upstream App:9093`; C1-S03). No data race: `controlsErrors_`/`controlsWarnings_` are atomics (`ApertarCoreApp.hpp:174-175`), `pendingUnitSince_` is under `controlsWorkerMutex_`. But `get_controls` writes those counters, erases `pendingUnitSince_`, spawns `systemctl show` per pending unit, and parses the same text 8 times (`App:12439-12448`). `scan_i2c` checks for a take once, then probes up to 117 addresses unlocked, so a take can start mid-scan. `test_input` must stay outside the lock: its actions take it themselves.
fix: Move `get_controls`, `controls_history`, `controls_last_input`, `list_actions` and `scan_i2c` back into the locked `if` chain. If the scan is slow, run it as a worker with polled state like the media speed test (C1-S20). Parse the text once in `get_controls` (`const hwconf::Document doc = hwconf::parse(info.text);`). Move the `systemctl` probe into the controls worker. Keep only `test_input` before the lock, with its existing comment.

### X-protocol-security-6 [bug, nit, deliberate: no, effort S] get_state emits media_state twice
where: `src/ApertarCoreApp.cpp:12944`; `src/ApertarCoreApp.cpp:12961`
detail: The `get_state` reply streams `"media_state"` from a fresh `mediaSnapshot()` at `:12944` and again from `mediaState` at `:12961`: a duplicate JSON key and two snapshots that can differ. Qt and JS keep the last; nothing breaks. Upstream `get_state` has no `media_state` key. Confirmed.
fix: Delete line 12944.

### X-protocol-security-7 [mismatch, minor, deliberate: unknown, effort S] Two doors to set_boot_config with different guards; HTTP route wraps the command parser
where: `src/ApertarCoreApp.cpp:9170-9198`; `src/ApertarCoreApp.cpp:14589-14590`; `src/ApertarCoreApp.cpp:3790-3797`
detail: `POST /api/boot-config` splices `"cmd":"set_boot_config"` into the body, parses it with `parseControlCommand`, and calls `bootConfigSet` with `browser` = Origin present, so a browser save needs a revision. `/api/command` reaches the same function with `browser=false`, so a save without revision is accepted there, also from the WebUI page itself. The revision is a stale-write guard (the card's "reload the card" case), not a security control. Upstream has one command door plus resource routes that do not reuse the command parser (`core-upstream App:7392-7500`, `:7637`). Confirmed.
fix: Keep `set_boot_config` as a plain command behind `/api/command` and drop the `POST /api/boot-config` write route; in `bootConfigSet` require `revision` on every non-dry-run save (`if (!revision) return {409, ... "old_page"}`) and drop the `browser` parameter.

### X-protocol-security-8 [protocol, nit, deliberate: yes, effort M] Port UI polls get_state at 1 Hz while auto ISO or auto WB is on
where: `Apertar-UI src/ApertarControlBridge.cpp:18-20`, `:1012-1018`
detail: Upstream polls every 30 s (`kSteadyStatePollIntervalMs`). The port polls every 1 s while auto ISO or auto WB is on, to show the value in use. Each `get_state` takes `commandMutex_` and builds the full state; the HDMI process doubles the rate. Confirmed.
fix: Have Core send the ISO and WB in use with an existing event (the `settings` event on change), and keep the 30 s poll.

### X-protocol-security-9 [new-ground, nit, deliberate: yes, effort S] sudoers files are new ground and imply a hardening Core does not have
where: `config/apertar-boot-config.sudoers`; `config/apertar-media-trim.sudoers`; `config/apertar-media.sudoers`
detail: Upstream ships no sudoers file (`core-upstream config/` holds only `apertar-core-capture-priority.conf`). It relies on the stock `NOPASSWD: ALL` for pi and calls `sudo -n` on tools and on its own helpers (`core-upstream App:1544`, `:1549`, `:3031`, `:3157`, `:3205`). The helper pattern is upstream's; the three narrow rules are new. Core still needs full sudo for the upstream paths, so the rules add nothing on a stock image and do not confine Core.
fix: Say in the handoff that the rules are optional and do not confine Core. Or drop the files and call the helpers with plain `sudo -n`, as upstream calls `apertar-standby-usb`.

Dropped: X-protocol-security-10 (see Skeptic).
