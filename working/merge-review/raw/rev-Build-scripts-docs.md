# Review: Build-scripts-docs (stage 2)

Refs: port = `cinemate-port` `01f170c`, base = `origin/main` `f60e301`, upstream = `upstream-1.6.0` `35dbe67` (Core), `43888e5` (UI).
Scope: `CMakeLists.txt README.md .gitignore scripts config src/ipc src/web/WebServer.cpp src/ApertarCoreApp.hpp src/main.cpp include third_party/liblj92/{README.apertar.md,LICENSE}`, plus `tools/`.
Diff: 19 files, +1240/-3. `.gitignore`, `src/main.cpp`: no diff.
Yardstick: `apertar-conventions.md` (rule ids below). Upstream code opened for every mismatch. Related sweeps: `sweep-knobs.md` (X-knobs-6, 9, 10, 11), `rev-App-1.md` (boot config), `rev-App-4.md` (workers).

## 1. Verdict in one table

| Id | Title | Category | Severity | Deliberate |
| --- | --- | --- | --- | --- |
| F1 | Media tuning file family + `apertar-tune` + `/run` override beside upstream's `.apertar-tuning` | mismatch | major | yes |
| F2 | README env-knob table and A/B instructions | mismatch | major | yes |
| F3 | RT scheduling: `APERTAR_RT` block in start script, `LimitRTPRIO=80` under a "non-real-time" comment | mismatch | major | yes |
| F4 | Root helpers as `/bin/sh` scripts + sudoers + tmpfiles in the Core repo | mismatch | major | yes |
| F5 | Three write routes for config.txt; helper's raw stderr shown to the operator | duplication | minor | yes |
| F6 | `apertar-media-tune`: root-owned state dir under a pi-owned `/run` dir; sudoers pin path only | security | minor | no |
| F7 | Ticket numbers, Cinemate hashes, KB paths and history narration in code, config and README | slop | minor | no |
| F8 | `ApertarCoreApp.hpp` layout: methods among members, split member groups, commented header | mismatch | minor | no |
| F9 | Host tests in `tools/` outside CMake, inconsistent build lines, test lines in operator README | new-ground | minor | unknown |
| F10 | Socket request line 64 KiB -> 1 MiB for whole-file `set_controls` | protocol | minor | yes |
| F11 | Preview temporal denoise off by default (upstream: tuning file decides, tdn on) | removed-upstream-behaviour | minor | yes |
| F12 | README growth: install recipes, socket lists, measurements, misplaced sections | mismatch | minor | yes |
| F13 | `third_party/liblj92/README.apertar.md` says "in the UI" in Core | slop | nit | no |

## 2. Findings

### F1 Media tuning file family (mismatch, major, deliberate yes)

- Port: `config/apertar-media-tune.conf:1-54` (INI, sections `[default] [exfat] [ext4] [<class>] [<class>.<fs>]`, own key names `dontneed writeback sync_ms raw_buffers kernel_tune workers queue extra_raw_buffers`), `/run/apertar-media/media-tune.override.conf`, `scripts/apertar-tune` (Python, 487 lines, `show/set/unset/clear/init`), `config/apertar-media.tmpfiles.conf`. Four layers per knob: env > override > base file > default (`apertar-tune:11-12`). Reader `src/util/MediaTune.hpp` (318 lines, X-knobs-6).
- Upstream: one bench file, `/home/pi/.apertar-tuning`, `NAME=VALUE` with the same `APERTAR_*` names as the env vars, env wins, re-read at clip open, absent in production: `src/prores/ProresEncoder.cpp:771-813@upstream-1.6.0`:
  `static std::string tuningOverride(const char *name) { if (const char *env = std::getenv(name)) return ...; std::ifstream in("/home/pi/.apertar-tuning");`
  CAM-24: "A bench knob is an env var ... not a setting, not a command, not in README"; violation listed: "A tuning config file ... for an internal knob". CAM-19: "internal tuning stays out of operator files and the README". Section 5: no Python tool beside Core, no tmpfiles.
- Why: three new files, a new INI dialect with its own key names, a Python CLI and a tmpfiles entry for what upstream solves with one 40-line function. The original developer meets a second tuning mechanism for the same purpose.
- Rework: move `tuningOverride` from `ProresEncoder.cpp` to a shared header (e.g. `src/util/TuningOverride.hpp`, the only refactor needed) and read each write-path knob as `tuningOverride("APERTAR_DNG_DONTNEED")` at take start, same names as the env vars. Delete `config/apertar-media-tune.conf`, `scripts/apertar-tune`, `src/util/MediaTune.hpp`, `config/apertar-media.tmpfiles.conf` (its `eject` dir has no reader, X-knobs-11). Per-medium defaults (exFAT workers/queue) stay as code in `MediaProfile` (a table in C++, like `CC:3323-3340`). Echo effective values in the existing `ApertarCore recording clip:` line (R8 step 4).
- Effort M. Risk: the owner asked for the file (2026-11-02, `sweep-knobs.md` X-knobs-6); his decision. Per-medium sections are lost; the fix keeps per-medium code defaults.

### F2 README env-knob table (mismatch, major, deliberate yes)

- Port: `README.md` "Write-path knobs for A/B tests", 14-row table of `APERTAR_*` vars with defaults, file keys, KB references (README.md:337-358@cinemate-port, section after "Split clips").
- Upstream: 43 `APERTAR_*` knobs in Core, none in README (conventions section 5). STY-14: "tables stop at CLI launch flags"; violation "A table of every env knob". CAM-24 / R8: "Not in ... README". Upstream README tables: only launch options `README.md:248-257@upstream-1.6.0`.
- Why: the README is for the camera builder. A table of A/B levers with "the behaviour before ..." makes experiments look like product features.
- Rework: delete the section. Knobs that survive X-knobs-9/10 stay in code with `unsignedEnvValue`/`boolEnvValue` and appear in the take-start log line. If the owner wants them documented, one KB page, not the README.
- Effort S.

### F3 RT scheduling (mismatch, major, deliberate yes)

- Port: `scripts/start-apertar-core.sh:20-41@cinemate-port` builds `chrt -f ${APERTAR_RT_PRIORITY:-70} ionice -c2 -n0 taskset -c ${APERTAR_RT_CPUS-1-3}` and `exec ${PREFIX[@]+"${PREFIX[@]}"} "$CORE_BIN"`. `config/apertar-core-capture-priority.conf` gains `LimitRTPRIO=80` under the kept upstream line `# Permit only a bounded, non-real-time boost for the camera callback thread.` `CC:9109-9122` adds `APERTAR_RT_CAPTURE_PRIORITY` (`sched_setscheduler(..., SCHED_FIFO, ...)`).
- Upstream: `config/apertar-core-capture-priority.conf@upstream-1.6.0` = `LimitNICE=-5` only; start script ends `exec "$CORE_BIN" --socket ... --media ...` (`scripts/start-apertar-core.sh:21@upstream-1.6.0`). PLT-14: "no affinity, no RT scheduling, only bounded nice"; section 5: `SCHED_FIFO|sched_setaffinity` = 0 hits.
- Evidence of outcome: `APERTAR_RT_CAPTURE_PRIORITY` measured "no effect" (`lessons/hardware-log.md:954`); `APERTAR_RT` never measured, judged "wrong shape ... control arm only" (`working/dng-chain/F/F3.md:166`). Port README: "An A/B instrument, not a recommendation."
- Why: the drop-in now contradicts its own comment; an experiment with no positive result stays in the launcher. `taskset -c 1-3` assumes four cores (pi-compat nit: true on every supported Pi, but a bad `APERTAR_RT_CPUS` makes `exec` fail and Core does not start, against PLT-22).
- Rework: restore upstream start script (drop lines 20-41, restore `exec "$CORE_BIN" ...`), restore upstream drop-in (drop `LimitRTPRIO=80` and its 3 comment lines), delete the `APERTAR_RT_CAPTURE_PRIORITY` block in `CC`. Effort S.

### F4 Root helpers in Core as shell scripts (mismatch, major, deliberate yes)

- Port: `scripts/apertar-boot-config` (sh, stdin -> `/boot/firmware/config.txt`), `scripts/apertar-media-trim` (sh, `fstrim` of a mount under `/media/`), `scripts/apertar-media-tune` (sh, `vm.dirty_*`, scheduler, `nr_requests`, NVMe APST); `config/apertar-boot-config.sudoers`, `config/apertar-media-trim.sudoers`, `config/apertar-media.sudoers`, `config/apertar-media.tmpfiles.conf`. All `#!/bin/sh`, `set -u`, `[ ]`.
- Upstream, two patterns:
  - PLT-5: simple privileged tools called directly from App: `"sudo -n install -m 644 " + shellQuote(tempPath) + " " + shellQuote(kBootConfigPath)` (`App:3157@upstream-1.6.0`), `sudo -n mount` (`App:3623`), `sudo -n blockdev --flushbufs` (`App:3353`), `sudo -n sh -c "echo 1 > " + removePath` (`App:3373`, a sysfs write).
  - PLT-4: a real root program = single Qt-free C++ file in the UI repo (`UI/src/StandbyLowPower.cpp`), CMake target, sudoers in `UI/systemd/` listing every verb: `pi ALL=(root) NOPASSWD: /usr/local/libexec/apertar-standby-usb off, /usr/local/libexec/apertar-standby-usb on` (`UI/systemd/apertar-standby-usb.sudoers@upstream-1.6.0`); Core calls `/usr/bin/timeout 6s /usr/bin/sudo -n /usr/local/libexec/apertar-standby-usb <verb>` (`App:1544`).
  - Section 5: "Root helpers inside the Core repo" absent; "Helper script files beside Core (only `scripts/start-apertar-core.sh`)". PLT-8: Core ships no helper script files. STY-16: `#!/bin/bash`, `set -euo pipefail`, `[[ ]]`.
- Why: a third shape for root work (sh scripts in Core, sudoers in Core `config/`), three install recipes in the README. Upstream already relies on `sudo -n` for `mount`, `mkfs`, `install` and sysfs writes, so on the image the narrow sudoers rules add files without adding a boundary.
- Rework, per helper:
  - `apertar-media-trim`: replace with a direct call in the trim worker: `/usr/bin/timeout 20s /usr/bin/sudo -n /usr/sbin/fstrim -v <shellQuote(media root)>` (PLT-5); the discard check (`/sys/block/<disk>/queue/discard_max_bytes`) and mount check move into App, where they need no root. Delete script, sudoers, `tools/media_trim_test.sh`. Keep the worker (rev-App-4 verdict keep).
  - `apertar-media-tune`: delete with `kernel_tune`/`APERTAR_MEDIA_TUNE` (never installed, off by default, numbers "taken from Cinemate ... T29 measures them before they are trusted"; X-knobs-10).
  - `apertar-boot-config`: one route only (F5). Either upstream's `sudo -n install` with the checks (size, NUL, `[pi5]/[pi4]/[all]`, backup) done in App before the call, or, if the owner wants the narrow sudoers rule, rewrite as `UI/src/BootConfigWriter.cpp` per R14 steps 5-6. rev-App-1 #13 keeps the sh helper as "narrower than upstream"; this review accepts that only as the single route.
- Effort M.

### F5 Three config.txt write routes (duplication, minor, deliberate yes)

- Port: `writeBootConfigText` (`App:3530-3609@cinemate-port`): direct write when writable (root, or `APERTAR_BOOT_CONFIG` copy), then the helper, then `sudo -n install` twice (backup, file). On helper refusal the helper's stderr is the operator error: `if (helper.output.find("apertar-boot-config:") != npos) return fail(helper.output);` -> e.g. "apertar-boot-config: input has no [pi5], [pi4] or [all] section: not the Apertar config.txt".
- Upstream: one route, `sudo -n install`, and a missing rule becomes "Changing the fan mode needs sudo permission." (`App:3157-3170@upstream-1.6.0`). PLT-5; STY-10 (one sentence, capital, full stop).
- Rework: one route (F4); map helper exit codes 2/3 to sentences ("The new config.txt has no [pi5], [pi4] or [all] section."); drop `APERTAR_BOOT_CONFIG` (test-only env path, rev-App-1 F3). Effort S.

### F6 `apertar-media-tune` state dir (security, minor, deliberate no)

- Port: `config/apertar-media.tmpfiles.conf:3-5` creates `/run/apertar-media 0755 pi pi` and inside it `/run/apertar-media/tune 0755 root root`. The root helper writes `cat "$2" > "${STATE_DIR}/${1}"` (`scripts/apertar-media-tune:save_once`) and later reads those files back into `/proc/sys/vm/*` (`restore_one`). `STATE_DIR="${APERTAR_MEDIA_RUN_DIR:-/run/apertar-media}/tune"` comes from the environment. `config/apertar-media.sudoers` and `apertar-media-trim.sudoers` pin the path only, any arguments.
- Failing input (probable, not run): as pi, `rmdir /run/apertar-media/tune` (empty after a restore; pi owns the parent), `ln -s /etc/sudoers.d /run/apertar-media/tune`, then `sudo -n /usr/local/libexec/apertar-media-tune apply nvme0n1 pi-nvme exfat` -> root creates `/etc/sudoers.d/queue_scheduler` with "[mq-deadline] none", a sudoers syntax error that disables sudo. A pi-owned replacement dir instead lets pi choose the values `restore` writes into `vm.dirty_bytes`. `APERTAR_MEDIA_RUN_DIR` is stripped by sudo's default `env_reset` (probable; settle with `sudo -n env` on the image).
- Upstream: PLT-4 "root-owned `/run/apertar-<name>`", sudoers listing every verb; section 1 line 9 "Root access is narrow".
- Rework: removed with the helper (F4). If kept: root-owned parent, no env var, sudoers listing `apply`/`restore` forms. Effort S.

### F7 Internal numbers and narration (slop, minor)

| Where @cinemate-port | Text |
| --- | --- |
| `src/ApertarCoreApp.hpp` | `// T50, Q23: a media delete is running`, `// T37: ...`, `// T39: the controls worker ...`, `// T42: the last control that moved (Listen)`, `// Storage pre-roll (CineMate's warm-up)` |
| `include/apertar/core/Types.hpp` | `// Speed ramping (T31)`, 7 x `// Runtime (T34): ...`, `conformFps` "nothing derives from it yet" (dead setting, X-knobs-12) |
| `scripts/apertar-media-tune:8,11` | "(Cinemate c8f06c9)", "T29 measures them on this rig before they are trusted" |
| `scripts/start-apertar-core.sh:21-24` | "the way cinemate starts cinepi-raw (src/module/cinepi_multi.py run())", "the A/B in the kb (working/dng-chain) decides whether it stays" |
| `config/apertar-core-capture-priority.conf` | "as cinemate runs cinepi-raw" |
| `src/ipc/ControlServer.cpp:15` | "64 KiB used to drop the client without a word" (history) |
| `README.md` | "measured 2026-11-04, probable", "Apertar knowledge base `working/drop-frames/nvme-campaign/probe-exfat-dir.md`", "Apertar-UI `7ea9afc` (local branch `clip-split`)", "the NVMe campaign's A/B" |

- Upstream: STY-9 (no ticket numbers or other projects' hashes, 0 hits in both trees), STY-8 (no history narration), STY-14 README honest limits without lab notes.
- Rework: delete the ids and references; keep one present-tense why-line where a hazard needs it (`// A set_controls text carries the whole hardware file.`). Effort S.

### F8 `ApertarCoreApp.hpp` layout (mismatch, minor)

- Port: method declarations inside the member section (`void runControlsWorker(); ... std::thread controlsThread_;`, `void noteInputSeen(...)` next to `lastInputMutex_`); the media-trim group is split by the clip-merge group (`mediaTrimBackoffRounds_ ... mediaTrimLastUnix_` after `clipMergeBlockUntilMs_`); `enum class ClipMergeOutcome` declared in the method list; ~40 trailing or block comments on members.
- Upstream: CMD-20 "owned components by value first, then state groups split by blank lines, mutex first" (`AppH:110-124@upstream-1.6.0`); STY-8 "headers uncommented".
- Rework: move all new methods into the private method block after `joinMediaSpeedTest()`; one contiguous group per worker (`std::thread`, atomic flag, mutex, cv, state), mutex first; keep at most one comment per group naming a lock rule. `handleReadOnlyHardwareCommand` goes with its rework in rev-App-4 (second dispatcher before `commandMutex_`, CMD-2/CMD-3). Effort S.

### F9 Host tests in `tools/` (new-ground, minor, deliberate unknown)

- Port: 15 `tools/*_test.cpp`, 3 `*.sh`, 2 Python files. Build line in each header comment; not CMake targets. Lines differ: `g++ -std=c++20 -O2 -Wall -Wextra -I src -I include` (most), `c++ -std=c++17` (`clip_merge_test.cpp:2`, `frame_path_test.cpp:3`), `g++ -std=c++20 -I src` without warnings (`imx585_modes_test.cpp:2`), libyaml via pkg-config (`tuning_tdn_strip_test.cpp:2`). README embeds test build lines in operator sections ("Preview temporal denoise", "Split clips"). `tools/` also holds an operator tool (`flatten_clip.py`) and a generator (`gen_log_curve.py`). `src/util/MediaTune.hpp:5` names `tools/media_tune_test.cpp`, which does not exist (X-knobs-6).
- Upstream: no tests, no `tools/` (section 5; PLT-12: "No test targets and no CI"). Core is C++20 (PLT-15).
- Verdict: keep, simplify. Outside CMake is the least foreign shape (no test target, no CI). Make every header line `g++ -std=c++20 -O2 -Wall -Wextra -I src -I include tools/<name>.cpp -o /tmp/<name> && /tmp/<name>`; remove test lines from operator README sections; one sentence in README "For Developers": "`tools/*_test.cpp` are host tests of the header-only logic; each file's first lines say how to build it." Fix or drop the dangling `media_tune_test.cpp` reference. Effort S.

### F10 1 MiB socket line (protocol, minor, deliberate yes)

- Port: `src/ipc/ControlServer.cpp:15-16,264`: `constexpr size_t kMaxRequestLineBytes = 1024 * 1024;` replaces `64 * 1024`.
- Upstream: socket line 64 KiB (`ControlServer.cpp:261@upstream-1.6.0`); whole hardware-file text travels over HTTP `POST /api/config` (`App:7175-7193@upstream-1.6.0`) under `WebServer.cpp:23` `kMaxRequestSize = 1024 * 1024`.
- Protocol: no break; an unmodified UI sends short lines; an original Core still drops a >64 KiB line from a port client, which only matters for `set_controls` with `text` (WebUI sends it via `POST /api/command`, not the socket; the touch UI does not send `set_controls`: no hit in `Apertar-UI/src`).
- Why: the raise exists because a whole file travels inside a command (CMD-8 shape stretched). Memory per stalled client 16x.
- Rework: follows the HW-config-text-store / App-4 decision. If `set_controls text` is replaced by upstream `/api/config`, revert to the literal `64 * 1024`. If kept, keep the constant (its form matches `kMaxRequestSize`) with a one-line why. Effort S.

### F11 Preview temporal denoise off by default (removed-upstream-behaviour, minor, deliberate yes)

- Port: `Types.hpp` `bool previewTdn = false;`; README: "It is off by default"; Core hands libcamera a `_notdn.json` copy of the tuning file.
- Upstream: libcamera loads the selected tuning file as is (`scripts/start-apertar-core.sh:15-18@upstream-1.6.0`, `DefaultTuningSelection.hpp`), so tdn runs as the tuning file says.
- Why: an operator updating to this Core sees a noisier preview with no change on their side; the cause (ISP back-end load at 4K Clear HDR 16-bit) is rig- and mode-specific (measured once, 2026-11-04).
- Rework: owner decision. Upstream-faithful option: default `previewTdn = true` (no copy, upstream behaviour) and turn it off on the rig; or keep off and state the reason in the commit and the handoff. Effort S.

### F12 README growth (mismatch, minor, deliberate yes)

- Port: +90 lines. `## Boot Config (config.txt)` between Hardware Controls and Building; three `### ...` sections (trim, TDN, split clips) plus the knob table under "Where Are Recordings Saved?"; three `sudo install` recipes; a `Socket commands:` line listing 14 fields; measurements and dates.
- Upstream: STY-14 (camera-builder voice, tables stop at launch flags, one short For Developers section). No install recipe for helpers: UI README says only "depend on the installed panel drivers, helpers and permissions" (`UI/README.md:199@upstream-1.6.0`); PLT-6/PLT-24 (install is by the image or by hand).
- Rework: keep one short operator paragraph per feature (Boot Config card, split clips with the "Resolve imports one folder" warning, trim on/off). Move install recipes, socket field lists, measurements and A/B notes to the handoff notes or KB. Delete the knob table (F2). Effort S.

### F13 liblj92 README text (slop, nit)

- Port: `third_party/liblj92/README.apertar.md` is byte-identical to `UI/third_party/liblj92/README.apertar.md@upstream-1.6.0`, so it says "Used to decode lossless JPEG tiles in the UI". In Core the users are `src/playback/DngFrameReader.hpp` and `src/playback/DngTags.hpp`.
- Rework: change the purpose sentence to "Used by Core playback (`src/playback/`) to decode lossless JPEG tiles of recorded DNGs." Keep the rest (PLT-17 satisfied). Effort S.

## 3. Abstraction verdicts (inventory section 5)

| Abstraction | Verdict | Reason |
| --- | --- | --- |
| `apertar-boot-config` helper + sudoers | simplify | Narrow (no args, fixed dest) and careful; keep as the single route or fall back to upstream `sudo -n install` with App-side checks (F4, F5). Shape (sh in Core) is new |
| `apertar-media-trim` helper + sudoers | rework-to-upstream-pattern | Direct `timeout 20s sudo -n fstrim -v <media root>` from the trim worker (PLT-5) |
| `apertar-media-tune` helper + sudoers | simplify (remove) | Never installed, off by default, unmeasured numbers; F6 |
| `apertar-tune` (Python CLI) | simplify (remove) | Edits a file that F1 removes; no Python tools beside Core upstream |
| `apertar-media-tune.conf` + `/run` override | rework-to-upstream-pattern | `tuningOverride()` / `/home/pi/.apertar-tuning` (`ProresEncoder.cpp:771-813@upstream-1.6.0`) |
| `apertar-media.tmpfiles.conf` | simplify (remove) | Serves the override, the tune helper and an `eject` dir with no reader |
| `HardwareConfigStore` / `HardwareConfigText` | out of unit (see rev-HW-config-text-store) | Build listing conforms (PLT-1) |
| `GpioChipInfo`, `I2cProbe` | keep (from this unit) | Listed by hand next to `src/hardware/*`; judged in HW units |
| `PlaybackFrames` + `third_party/liblj92` | keep | Vendoring follows PLT-17 and UI precedent byte for byte; `LANGUAGES C CXX` + `lj92.c` in sources mirrors `UI/CMakeLists.txt:2,123@upstream-1.6.0`; F13 text fix |
| header-only modules (`MediaProfile` ... `ClipFrames`) | keep (from this unit) | Header-only logic has precedent (`DefaultTuningSelection.hpp`); judged in owning units |
| 7 worker threads in `ApertarCoreApp` | keep shape | `std::thread` members + atomic flags + mutex/cv per group follow CMD-19; layout F8; per-worker verdicts in rev-App-4 |
| `handleReadOnlyHardwareCommand` | rework-to-upstream-pattern | Second dispatcher before `commandMutex_` (CMD-2, CMD-3); rev-App-4 |
| `CdngLog` enum + inline helpers | keep | Upstream `Types.hpp` holds rule helpers too (`usesStillBracketing` `Types.hpp:164`, `timelapseExposureLimitUs` `:178@upstream-1.6.0`); drop "T" ids (F7) |
| Host tests `tools/*_test.cpp` | keep, simplify | F9 |
| Env-var knob layer (20+ vars) | simplify | Upstream form (CAM-24) for the few that stay; remove RT (F3), media-tune (F4), README table (F2); full list X-knobs |

## 4. What conforms

| Item | Where @cinemate-port | Rule |
| --- | --- | --- |
| New `.cpp` files listed by hand next to their area; no glob, no new library target | `CMakeLists.txt:77-96` | PLT-1 |
| `LANGUAGES C CXX` and `lj92.c` in the main target, as the UI does | `CMakeLists.txt:6,78`; `UI/CMakeLists.txt:2,123@upstream-1.6.0` | PLT-1, PLT-17 |
| Vendored decoder under `third_party/liblj92/` with LICENSE and `README.apertar.md` naming upstream commit, licence, local fix; byte-identical to the UI copy | `third_party/liblj92/` | PLT-17, PLT-11 (per-repo copy) |
| `reasonPhrase` extended in place (206, 409, 416) | `src/web/WebServer.cpp:64-71` | STY-12 (extend in place) |
| Named constant `kMaxRequestLineBytes` in the anonymous namespace, same form as `kMaxRequestSize` | `src/ipc/ControlServer.cpp:15-16` | STY-3 |
| Start script stays bash, `set -euo pipefail`, `${APERTAR_X:-default}`, falls back to a normal start with one stderr line | `scripts/start-apertar-core.sh` | PLT-9, STY-16, PLT-22 |
| `CaptureSettings` members appended with in-class defaults; "Runtime ..., not persisted" comments in upstream's own form | `include/apertar/core/Types.hpp` | STY-2; upstream `whiteBalanceAvailable` comment |
| Worker threads as `std::thread` members with atomic run flags, mutex + cv per group | `src/ApertarCoreApp.hpp` | CMD-19, CMD-20 (shape) |
| `handleCommand` signature unchanged; no protocol version added | `src/ApertarCoreApp.hpp:82` | CMD-30 |
| No test target, no CI, no `.gitignore`, no `main.cpp` change | tree | PLT-12, PLT-13, CMD-23 |
| Boot-config helper: no arguments, fixed destination, input checks, backup, tmp + sync + rename | `scripts/apertar-boot-config` | PLT-23 (narrow root access) |
| Trim helper validates its one argument (under `/media/`, canonical, mount point, discard) and has a 20 s limit | `scripts/apertar-media-trim` | PLT-23, PLT-4 (bounded timeout) |

## 5. Protocol check

| Change | Original UI vs port Core | Port UI/WebUI vs original Core |
| --- | --- | --- |
| Socket line 1 MiB | no effect | `set_controls` with `text` > 64 KiB dropped by original Core; command unknown there anyway |
| HTTP 206/409/416 phrases | no effect (original WebUI does not call the new routes) | n/a |
| New state fields in `CaptureSettings` | extra keys ignored (CMD-30) | missing fields default |

## Skeptic

Checked at `cinemate-port` `01f170c` against `upstream-1.6.0`. Every port line was opened; every upstream counter-example was opened.

| Id | Verdict | Why |
| --- | --- | --- |
| F1 | stands | Confirmed: `config/apertar-media-tune.conf`, `scripts/apertar-tune` (487 lines), `src/util/MediaTune.hpp` (318), tmpfiles entry. Upstream `tuningOverride()` (`src/prores/ProresEncoder.cpp:771-813@upstream-1.6.0`) is a bench file for the same stated reason ("a restart between arms ... makes an A/B untrustworthy"), so the rework keeps the feature (no drop-in, no restart, except dontneed/writeback which the port also fixes per process). Owner asked for the file (`fork-log.md:142-143`, `sweep-knobs.md:402`). |
| F2 | corrected | Table has 13 rows, not 14. "43 upstream knobs" replaced by the checkable claim: `grep -c APERTAR_ README.md@upstream-1.6.0` = 0. |
| F3 | stands | Script, drop-in and `CC:9109-9122` confirmed. `chrt` is probed with `/bin/true`, `taskset` is not, so a bad `APERTAR_RT_CPUS` makes the final `exec taskset` fail and Core does not start. `lessons/hardware-log.md:954` "92 (6.1 %): no effect" confirmed. Commit c57c284 body: "keeps it as a test, not a default". |
| F4 | corrected | Pattern and rework stand (upstream has no sh root helper in either tree; UI root helper is C++ with per-verb sudoers). Corrected: README carries two helper install recipes (boot-config, trim); the third README recipe installs the capture-priority drop-in; the media-tune/tmpfiles recipes sit in the config file headers. Added: the media-tune helper is called from Core (`App:11393-11411`) although never installed (26da30e: "added but not installed ... Core's sudo -n call fails and logs"). |
| F5 | corrected | Confirmed (`App:3530-3609`, `fail(helper.output)` at 3589-3590). Added: the denied-path error at 3604-3607 puts two shell install commands into the operator message, the second STY-10 break. |
| F6 | corrected | Mechanism confirmed (`/run/apertar-media 0755 pi pi`, `tune 0755 root root`, `save_once` writes, `restore_one` writes back and `rm -f`). Two claims softened: `APERTAR_MEDIA_RUN_DIR` is stripped by sudo's default `env_reset` (probable), so the env path is not the attack; the attack is pi renaming or removing `tune` in its own parent and planting a symlink. "Disables sudo" is unconfirmed (recent sudo can skip a bad sudoers.d file; settle with `sudo -V` and a test on the image). Real only once the helper and tmpfiles are installed. |
| F7 | stands | All quoted texts found at the named places (`AppH:173-195`, `Types.hpp:141,181-189`, `apertar-media-tune:8,11`, `start-apertar-core.sh:20-24`, drop-in `:4-6`, `ControlServer.cpp:15`, README 320, 331, 335). |
| F8 | stands | `AppH:179-200` methods among members, `ClipMergeOutcome` at 145, trim members at 324 after `clipMergeBlockUntilMs_` (323). Upstream header has 1 `//` line, port 37. |
| F9 | stands | 15 `*_test.cpp`, 3 `*.sh`, 2 `.py` counted. Build lines differ as stated; also `buffer_budget_test.cpp` and `storage_buffer_conf_test.cpp` omit `-I include`, `dng_payload_write_test.cpp` has none (its `.sh` drives it). Upstream Core has no `tools/` (`ls` of the worktree). |
| F10 | stands | `ControlServer.cpp:15-16,264` vs `64 * 1024` at `:261@upstream-1.6.0`; upstream `/api/config` POST at `App:7175`; no `set_controls` in `Apertar-UI/src`. |
| F11 | stands | `Types.hpp:139` `bool previewTdn = false;`; README 315-323. Upstream has no tdn handling. |
| F12 | stands | +90 lines (`git diff --stat`); 14 socket fields counted at README 211; three `sudo install` blocks (boot-config 199-203, trim 307-312, drop-in inside the knob table). |
| F13 | stands | `diff` with `UI/third_party/liblj92/README.apertar.md@upstream-1.6.0`: identical; users are `src/playback/DngTags.hpp`, `DngFrameReader.hpp`. |

## Final findings

### Build-scripts-docs-F1 [mismatch, major] Media tuning file family beside upstream's `.apertar-tuning`
- Where: `config/apertar-media-tune.conf:1-54`, `scripts/apertar-tune:1-487`, `config/apertar-media.tmpfiles.conf:1-5`, `src/util/MediaTune.hpp:1-318` @cinemate-port
- Port: four layers per write-path knob (env > `/run/apertar-media/media-tune.override.conf` > `~/apertar-media-tune.conf` > default), own key names (`dontneed writeback sync_ms raw_buffers workers queue extra_raw_buffers kernel_tune`), per-medium INI sections, a 487-line Python editor, a tmpfiles entry.
- Apertar way: `tuningOverride(name)` (`src/prores/ProresEncoder.cpp:771-813@upstream-1.6.0`): env wins, else `NAME=VALUE` from `/home/pi/.apertar-tuning`, same `APERTAR_*` names, re-read at clip open, absent in production; written for the same reason (A/B arms without a restart). CAM-24, CAM-19.
- Why it matters: the original developer meets a second tuning mechanism with its own dialect and a Python tool, for a job his 40-line function already does.
- Rework: move `tuningOverride()` to `src/util/TuningOverride.hpp`; read the write-path knobs at take start by their `APERTAR_*` names; per-medium defaults stay as a C++ table in `MediaProfile`; echo effective values in the `ApertarCore recording clip:` line. Delete `config/apertar-media-tune.conf`, `scripts/apertar-tune`, `src/util/MediaTune.hpp`, `config/apertar-media.tmpfiles.conf`.
- Effort M. Deliberate yes: owner asked for the file 2026-11-02 (`fork-log.md:142-143`, `sweep-knobs.md:402`); removal is his call. Risk: per-medium override sections are lost.

### Build-scripts-docs-F2 [mismatch, major] README table of env knobs and A/B instructions
- Where: `README.md:337-358@cinemate-port`
- Port: section "Write-path knobs for A/B tests": file/override instructions and a 13-row table of `APERTAR_*` vars with defaults, file keys and KB references.
- Apertar way: README tables stop at launch options (`README.md:248-257@upstream-1.6.0`); `grep -c APERTAR_ README.md@upstream-1.6.0` = 0. STY-14, CAM-24, recipe R8 ("Not in ... README").
- Why it matters: the README is for camera builders; experiment levers read like product features.
- Rework: delete the section. Surviving knobs keep the `unsignedEnvValue`/`boolEnvValue` form and appear in the take-start log line. Documentation, if wanted, on a KB page.
- Effort S. Deliberate yes: c57c284 "The README gets a table of the write-path knobs for A/B tests".

### Build-scripts-docs-F3 [mismatch, major] RT scheduling in the start script; `LimitRTPRIO=80` under the "non-real-time" comment
- Where: `scripts/start-apertar-core.sh:20-44`, `config/apertar-core-capture-priority.conf:4-7`, `src/camera/CameraController.cpp:9109-9122` @cinemate-port
- Port: `APERTAR_RT=1` prefixes `exec` with `chrt -f 70 ionice -c2 -n0 taskset -c 1-3`; the drop-in gains `LimitRTPRIO=80` (unconditional); `APERTAR_RT_CAPTURE_PRIORITY` puts the completion thread on `SCHED_FIFO`.
- Apertar way: drop-in = `LimitNICE=-5` under "# Permit only a bounded, non-real-time boost for the camera callback thread." (`config/apertar-core-capture-priority.conf@upstream-1.6.0`); script ends `exec "$CORE_BIN" --socket ... --media ...` (`scripts/start-apertar-core.sh:21@upstream-1.6.0`). PLT-14.
- Why it matters: the drop-in contradicts its own comment. Capture-thread FIFO measured "no effect" (`lessons/hardware-log.md:954`); whole-process RT never measured. `chrt` is probed, `taskset` is not: a bad `APERTAR_RT_CPUS` makes the `exec` fail and Core does not start (PLT-22).
- Rework: restore the upstream start script and drop-in; delete the `APERTAR_RT_CAPTURE_PRIORITY` block in `CC`.
- Effort S. Deliberate yes: c57c284 "keeps it as a test, not a default"; README "An A/B instrument, not a recommendation".

### Build-scripts-docs-F4 [mismatch, major] Three root helpers as `/bin/sh` scripts with sudoers and tmpfiles inside the Core repo
- Where: `scripts/apertar-boot-config`, `scripts/apertar-media-trim`, `scripts/apertar-media-tune`, `config/apertar-boot-config.sudoers`, `config/apertar-media-trim.sudoers`, `config/apertar-media.sudoers`, `config/apertar-media.tmpfiles.conf`, callers `src/ApertarCoreApp.cpp:3580-3590,11393-11435` @cinemate-port
- Port: POSIX sh helpers (`set -u`, `[ ]`) in Core `scripts/`, sudoers in Core `config/`; README install recipes for boot-config and trim; media-tune and tmpfiles recipes in the config file headers. Core calls the media-tune helper although it is never installed (26da30e).
- Apertar way: simple privileged steps are `sudo -n` from App: `sudo -n install -m 644` (`App:3157`), `sudo -n mount` (`App:3623`), `sudo -n blockdev --flushbufs` (`App:3353`), `sudo -n sh -c 'echo 1 > sysfs'` (`App:3373`) @upstream-1.6.0 (PLT-5). A real root program is Qt-free C++ in the UI repo with a sudoers file listing every verb, e.g. `UI/systemd/apertar-standby-usb.sudoers@upstream-1.6.0`, called as `/usr/bin/timeout 6s /usr/bin/sudo -n /usr/local/libexec/apertar-standby-usb <verb>` (`App:1544`) (PLT-4). Neither upstream tree has a `#!/bin/sh` file; Core has only `scripts/start-apertar-core.sh`. STY-16.
- Why it matters: a third shape for root work, in the repo that has none. The image already relies on broad `sudo -n`, so narrow rules add files without adding a boundary.
- Rework: trim: in the trim worker call `/usr/bin/timeout 20s /usr/bin/sudo -n /usr/sbin/fstrim -v <shellQuote(media root)>`; discard and mount checks in App (no root needed); delete script, sudoers, `tools/media_trim_test.sh`. Media-tune: delete with `kernel_tune` and `APERTAR_MEDIA_TUNE`. Boot config: one route only, either upstream `sudo -n install` with App doing the checks and backup first, or the helper rewritten as `UI/src/BootConfigWriter.cpp` per R14 steps 5-6.
- Effort M. Deliberate yes: dda1713 "Same shape as apertar-media-trim"; 26da30e "added but not installed".

### Build-scripts-docs-F5 [duplication, minor] Three write routes for config.txt; raw helper stderr and shell commands in operator errors
- Where: `src/ApertarCoreApp.cpp:3530-3609@cinemate-port`
- Port: `writeBootConfigText` tries a direct write (root, or the `APERTAR_BOOT_CONFIG` copy), then the helper on stdin, then `sudo -n install` twice (backup, file). A helper refusal returns `helper.output` (3589-3590), e.g. "apertar-boot-config: input has no [pi5], [pi4] or [all] section: not the Apertar config.txt". A sudo refusal returns a message holding two `sudo install ...` command lines (3604-3607).
- Apertar way: one route, `sudo -n install`, and a missing rule becomes "Changing the fan mode needs sudo permission." (`App:3157-3170@upstream-1.6.0`). PLT-5, STY-10.
- Why it matters: three routes to test for one file write; operator errors break the one-sentence style.
- Rework: keep one route (F4); map helper exit codes 2 and 3 to sentences; one-sentence permission error ("Writing config.txt needs sudo permission."); drop `APERTAR_BOOT_CONFIG`.
- Effort S. Deliberate yes: the comment above `writeBootConfigText` lists the order.

### Build-scripts-docs-F6 [security, minor] `apertar-media-tune` keeps root state in a pi-owned `/run` dir; sudoers pin the path only
- Where: `config/apertar-media.tmpfiles.conf:3-5`, `scripts/apertar-media-tune:30,47-63`, `config/apertar-media.sudoers:3`, `config/apertar-media-trim.sudoers:4` @cinemate-port
- Port: `/run/apertar-media` is `0755 pi pi` and holds `tune/` (`root root`). As root the helper runs `cat "$2" > "${STATE_DIR}/${1}"` and later writes those values to `/proc/sys/vm/*` and `rm -f`s them. Sudoers rules allow any arguments.
- Apertar way: PLT-4: root-owned `/run/apertar-<name>`, sudoers listing every verb (`UI/systemd/apertar-standby-low-power.sudoers@upstream-1.6.0`).
- Why it matters (probable, not run; real only once helper and tmpfiles are installed): pi owns the parent, so pi can rename or (after a restore) remove `tune` and put `ln -s /etc/sudoers.d /run/apertar-media/tune`; the next `sudo -n apertar-media-tune apply nvme0n1 pi-nvme exfat` makes root create `/etc/sudoers.d/queue_scheduler` containing "[mq-deadline] none" (a sudoers parse error; whether sudo then refuses depends on the sudo version, unconfirmed). A pi-owned replacement dir lets pi choose the values `restore` writes to `vm.dirty_*`. `STATE_DIR` from `APERTAR_MEDIA_RUN_DIR` is stripped by sudo's default `env_reset` (probable; `sudo -n env` on the image settles it).
- Rework: removed with the helper (F4). If kept: root-owned parent, no env var, sudoers listing the `apply`/`restore` forms.
- Effort S. Deliberate no.

### Build-scripts-docs-F7 [slop, minor] Ticket ids, Cinemate hashes, KB paths and history narration in code, config and README
- Where: `src/ApertarCoreApp.hpp:173-195` (T37, T39, T42, T50, Q23); `include/apertar/core/Types.hpp:141,181-189` (T31, 7 x T34); `scripts/apertar-media-tune:8,11`; `scripts/start-apertar-core.sh:20-24`; `config/apertar-core-capture-priority.conf:4-6`; `src/ipc/ControlServer.cpp:15`; `README.md:320,331,335,341` @cinemate-port
- Port: "// T50, Q23: ...", "(Cinemate c8f06c9)", "T29 measures them", "the A/B in the kb (working/dng-chain) decides", "64 KiB used to drop the client without a word"; README "measured 2026-11-04, probable", KB file paths, "Apertar-UI 7ea9afc (local branch clip-split)".
- Apertar way: STY-9 (no ticket numbers or other projects' hashes; 0 hits in both upstream trees), STY-8 (no history narration).
- Why it matters: the ids mean nothing to the original developer; the text reads as lab notes.
- Rework: delete ids and references; keep a present-tense why-line only where it names a hazard (e.g. "// A set_controls text carries the whole hardware file.").
- Effort S. Deliberate no.

### Build-scripts-docs-F8 [mismatch, minor] `ApertarCoreApp.hpp` layout: methods among members, split groups, commented header
- Where: `src/ApertarCoreApp.hpp:145,171-200,255-330@cinemate-port`
- Port: method declarations among data members (`runControlsWorker` 179, `noteInputSeen` 196); media-trim members (324) split from their group by the clip-merge group (323); `enum class ClipMergeOutcome` in the method list (145); 37 `//` comment lines.
- Apertar way: CMD-20 owned components first, then state groups split by blank lines, mutex first (`AppH:110-124@upstream-1.6.0`); upstream header has 1 `//` line (STY-8).
- Why it matters: the header no longer reads like upstream's; lock ownership is hard to see.
- Rework: all new methods into the private method block after `joinMediaSpeedTest()`; each worker one contiguous group (mutex first, thread, flag, cv, state); at most one lock-rule comment per group; `handleReadOnlyHardwareCommand` follows the rev-App-4 rework.
- Effort S. Deliberate no.

### Build-scripts-docs-F9 [new-ground, minor] Host tests in `tools/` outside CMake; build lines disagree; test lines in the operator README
- Where: `tools/*_test.cpp` header comments, `tools/clip_merge_test.cpp:2`, `tools/frame_path_test.cpp:3`, `tools/imx585_modes_test.cpp:2`, `src/util/MediaTune.hpp:5`, `README.md:325,335` @cinemate-port
- Port: 15 C++ tests, 3 sh tests, 2 Python tools. Build lines mix `g++`/`c++`, `-std=c++17`/`c++20`, with and without warnings and `-I include`; `MediaTune.hpp:5` names `tools/media_tune_test.cpp`, which does not exist.
- Apertar way: no precedent: upstream Core has no tests and no `tools/` (PLT-12, section 5). Core is C++20 (PLT-15).
- Why it matters: outside CMake is the least foreign shape; the inconsistency and the README placement make it look accidental.
- Rework: keep, simplify. One header line form `g++ -std=c++20 -O2 -Wall -Wextra -I src -I include tools/<name>.cpp -o /tmp/<name> && /tmp/<name>`; test lines out of operator README sections, one sentence in "For Developers"; fix or drop the dangling `media_tune_test` reference (goes with F1).
- Effort S. Deliberate unknown.

### Build-scripts-docs-F10 [protocol, minor] Socket request line raised from 64 KiB to 1 MiB for whole-file `set_controls`
- Where: `src/ipc/ControlServer.cpp:15-16,264@cinemate-port`
- Port: `constexpr size_t kMaxRequestLineBytes = 1024 * 1024;` because a `set_controls` text carries the whole hardware file.
- Apertar way: socket line limited to 64 KiB (`ControlServer.cpp:261@upstream-1.6.0`); whole hardware-file text travels over `POST /api/config` (`App:7175@upstream-1.6.0`) under `WebServer.cpp:23` `kMaxRequestSize = 1024 * 1024`.
- Why it matters: no break for an unmodified UI (touch UI never sends `set_controls`: 0 hits in `Apertar-UI/src`); the raise serves only external socket clients; memory per stalled client 16x.
- Rework: follow the HW-config-text-store decision. If `set_controls` text gives way to `/api/config`, revert to `64 * 1024`; otherwise keep the constant with a one-line why.
- Effort S. Deliberate yes: 5395fa4 "the socket takes 1 MiB lines".

### Build-scripts-docs-F11 [removed-upstream-behaviour, minor] Preview temporal denoise off by default
- Where: `include/apertar/core/Types.hpp:139`, `README.md:315-325` @cinemate-port
- Port: `bool previewTdn = false;`; Core hands libcamera a `_notdn.json` copy of the tuning file.
- Apertar way: libcamera loads the selected tuning file unchanged (`scripts/start-apertar-core.sh:15-18`, `src/camera/DefaultTuningSelection.hpp@upstream-1.6.0`), so tdn runs as the file says.
- Why it matters: after an update the operator sees a noisier preview without changing anything; the reason was measured once, on one rig and mode.
- Rework: owner decision. Default `true` (upstream behaviour) and switch it off on the rig, or keep `false` and state the reason in the commit and the handoff.
- Effort S. Deliberate yes: README cites the 2026-11-04 measurement.

### Build-scripts-docs-F12 [mismatch, minor] README growth: install recipes, socket field lists, measurements, misplaced sections
- Where: `README.md:179-211,303-358@cinemate-port`
- Port: +90 lines: a Boot Config section, three operator sections under "Where Are Recordings Saved?" plus the knob table, three `sudo install` recipes (boot-config, trim, capture-priority drop-in), a "Socket commands:" list of 14 fields, dated measurements.
- Apertar way: STY-14 camera-builder voice, tables stop at launch flags; helpers get no install recipes: "depend on the installed panel drivers, helpers and permissions" (`UI/README.md:199@upstream-1.6.0`). PLT-6, PLT-24.
- Why it matters: the README becomes a lab manual.
- Rework: one short operator paragraph per feature (Boot Config card, split clips with the import warning, trim on/off); install recipes, socket lists, measurements and A/B notes to the handoff or KB; knob table deleted (F2).
- Effort S. Deliberate yes: c57c284 and the feature commits add the sections on purpose.

### Build-scripts-docs-F13 [slop, nit] Core's liblj92 `README.apertar.md` says "in the UI"
- Where: `third_party/liblj92/README.apertar.md:7-8@cinemate-port`
- Port: byte-identical to `UI/third_party/liblj92/README.apertar.md@upstream-1.6.0`: "Used to decode lossless JPEG tiles in the UI".
- Apertar way: PLT-17: `README.apertar.md` names the purpose (`UI/third_party/liblj92/README.apertar.md:1-11@upstream-1.6.0`).
- Why it matters: in Core the users are `src/playback/DngFrameReader.hpp` and `DngTags.hpp`; the stated purpose is wrong.
- Rework: "Used by Core playback (src/playback/) to decode lossless JPEG tiles of recorded DNGs."
- Effort S. Deliberate no.
