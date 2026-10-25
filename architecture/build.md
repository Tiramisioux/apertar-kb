# Build and deploy

How each repo builds, what it outputs, and what to run on the Pi to rebuild and restart one component.

Paths are repo-relative (`Apertar-Core/...`, `Apertar-UI/...`). Pi paths are absolute.

## Quick reference

| Component | Source on Pi | Build dir on Pi | Rebuild | Restart |
| --- | --- | --- | --- | --- |
| Core | `/home/pi/ApertarCore` | `/home/pi/ApertarCore-build` (out of tree) | `cmake --build /home/pi/ApertarCore-build -j2` | `sudo systemctl restart apertar-core` |
| UI | `/home/pi/ApertarUI` | `/home/pi/ApertarUI/build` (in tree) | `cmake --build /home/pi/ApertarUI/build -j2` | `sudo systemctl restart apertar-ui-direct` |
| Network helper | `/home/pi/ApertarUI` | same UI build dir | same UI build | `sudo systemctl restart apertar-network` |
| CFE automounter | `/home/pi/ApertarUI` | same UI build dir | same UI build, then copy to `/usr/local/libexec` (see below) | `sudo systemctl restart apertar-cfe-automounter` |
| imx585 driver | `/home/pi/drivers/imx585-v4l2-driver` | DKMS (`/usr/src/imx585-0.0.1`) | `./setup.sh` (DKMS remove/add/build/install) | reboot |

## Apertar-Core

### CMake

| Item | Value | Ref |
| --- | --- | --- |
| Minimum CMake | 3.20 | `Apertar-Core/CMakeLists.txt:1` |
| Language | C++20, no extensions | `Apertar-Core/CMakeLists.txt:21-23` |
| Default build type | `Release` is forced when none is given (single-config generators) | `Apertar-Core/CMakeLists.txt:12-15` |
| `APERTARCORE_ENABLE_LIBCAMERA` | `ON`. Links libcamera when pkg-config finds it | `Apertar-Core/CMakeLists.txt:17`, `:37-41` |
| `APERTARCORE_ENABLE_LIBAV` | `ON`. Builds the two encoder plugins when libav is found | `Apertar-Core/CMakeLists.txt:18`, `:43-67` |
| `APERTARCORE_PRORES_FFMPEG_PREFIX` | Optional private FFmpeg prefix used only for the ProRes plugin. Needs `libavcodec>=62` | `Apertar-Core/CMakeLists.txt:19`, `:46-65` |
| `-mtune=native` | Added in Release when not cross-compiling | `Apertar-Core/CMakeLists.txt:182-188` |

Required packages: pkg-config `yaml-0.1`, `alsa`, Threads (`Apertar-Core/CMakeLists.txt:25-28`). Optional: JPEG / TurboJPEG (`:29-31`, `:120-131`), libcamera (`:39`), libavcodec/libavformat/libavutil (`:45`).

**Trap: CMake configures even without libcamera or libav.** Then `APERTARCORE_HAS_LIBCAMERA=0` (`Apertar-Core/CMakeLists.txt:137`) and no plugins are built (`:171-172`). Check the configure output for `ApertarCore H.264 libav backend: lazy plugin enabled` (`:151`).

### Targets and outputs

| Target | Type | Output file | Sources | Ref |
| --- | --- | --- | --- | --- |
| `apertar-core` | executable | `apertar-core` | 26 `.cpp` files listed | `Apertar-Core/CMakeLists.txt:69-96` |
| `apertar-h264-libav` | MODULE, no `lib` prefix | `apertar-h264-libav.so` | `src/video/LibavH264EncoderPlugin.cpp` | `Apertar-Core/CMakeLists.txt:143-149` |
| `apertar-prores-libav` | MODULE, no `lib` prefix | `apertar-prores-libav.so` | `src/prores/ProresPlugin.cpp`, `ProresEncoder.cpp`, `ProresColor.cpp`, `ProresRepair.cpp` | `Apertar-Core/CMakeLists.txt:152-169` |

`install()` puts the binary in `bin/` and plugins in `lib/apertar-core/` (`Apertar-Core/CMakeLists.txt:190-196`). **The install layout does not match the plugin search path** (below): Core never looks in `../lib/apertar-core`. The Pi does not use `make install`; the service runs straight from the build dir.

### How Core finds its plugins at runtime

| Plugin | Search order | Ref |
| --- | --- | --- |
| H.264 | `$APERTAR_H264_LIBAV_PLUGIN`, then `<dir of /proc/self/exe>/apertar-h264-libav.so`, then `/home/pi/ApertarCore-build/apertar-h264-libav.so`, then bare name (dlopen search path) | `Apertar-Core/src/video/LibavH264EncoderClient.cpp:17-30`, `dlopen` at `:105` |
| ProRes | `$APERTAR_PRORES_PLUGIN`, then `<exe dir>/apertar-prores-libav.so`, then `/home/pi/ApertarCore-build/apertar-prores-libav.so`. Checks `apertar_prores_abi()` against `kApertarProresAbi` | `Apertar-Core/src/prores/ProresRecorder.cpp:25-50` |

Plugins are `dlopen`ed lazily, the first time the format is used (`Apertar-Core/README.md:221`). A stale `.so` next to a fresh binary fails the ProRes ABI check and logs `ProRes requires apertar-prores-libav.so` (`Apertar-Core/src/prores/ProresRecorder.cpp:48`).

### WebUI icons

The WebUI serves PNG icons from disk, not from the binary. Search order (`Apertar-Core/src/ApertarCoreApp.cpp:2420-2440`):

1. `$CWD/src/web/icons` (the service sets `WorkingDirectory=/home/pi/ApertarCore`, per the live Pi)
2. `<exe dir>/../src/web/icons`
3. `<exe dir>/../ApertarCore/src/web/icons` (matches `/home/pi/ApertarCore-build` → `/home/pi/ApertarCore`)
4. `<exe dir>/../../src/web/icons`, `<exe dir>/../../ApertarCore/src/web/icons`

Moving the build dir elsewhere can break WebUI icons. The HTML/JS itself is compiled in (`Apertar-Core/src/web/WebControlPage.cpp`, listed in `Apertar-Core/CMakeLists.txt:94`), so WebUI changes need a Core rebuild.

### Rebuild Core on the Pi

```bash
ssh pi@apertar.local
cd /home/pi/ApertarCore
git status                               # see what you changed
# First time only, or after CMakeLists.txt changes:
cmake -S . -B ../ApertarCore-build -DCMAKE_BUILD_TYPE=Release
cmake --build ../ApertarCore-build -j2   # -j1 on 2 GB boards (README:210)
sudo systemctl restart apertar-core
journalctl -u apertar-core -f            # watch startup
```

Build commands: `Apertar-Core/README.md:205-208`. Manual run (stop the service first, two processes would fight for the camera): `Apertar-Core/README.md:237-242`.

### The start script and service

`Apertar-Core/scripts/start-apertar-core.sh`:

| Line | What |
| --- | --- |
| `:4` | `CORE_BIN=${APERTAR_CORE_BIN:-/home/pi/ApertarCore-build/apertar-core}` |
| `:5` | `MEDIA_ROOT=${APERTAR_MEDIA_ROOT:-/media/RAW}` |
| `:6` | `SOCKET_PATH=${APERTAR_SOCKET_PATH:-/tmp/apertar-core.sock}` |
| `:16-18` | `APERTAR_TUNING_FILE` → `LIBCAMERA_RPI_TUNING_FILE` |
| `:21` | `exec $CORE_BIN --socket $SOCKET_PATH --media $MEDIA_ROOT` |

**Finding: the `APERTAR_TUNING_FILE` export has no effect.** At every camera open Core calls `applyProcessTuningFile()` (`Apertar-Core/src/camera/CameraController.cpp:5271`), which either `unsetenv`s or overwrites `LIBCAMERA_RPI_TUNING_FILE` (`:1111-1121`). Use the saved custom tuning setting instead.

The live Pi runs `/home/pi/start-apertar-core.sh`, a copy outside the repo. **Confirmed** (Pi, 2026-10-25, `cmp`): byte-identical to `scripts/start-apertar-core.sh`.

`Apertar-Core/config/apertar-core-capture-priority.conf` is a systemd drop-in: `[Service] LimitNICE=-5` (`:1-3`). It allows the camera callback thread a bounded nice boost. **Confirmed** installed (Pi, 2026-10-25: `systemctl cat apertar-core` shows `LimitNICE=-5`).

`apertar-core.service` itself is not in either repo. Its contents (User=pi, WorkingDirectory, ExecStartPre gate) come from the live Pi.

## Apertar-UI

### CMake

| Item | Value | Ref |
| --- | --- | --- |
| Minimum CMake | 3.21 | `Apertar-UI/CMakeLists.txt:1` |
| Languages | C and C++17 | `Apertar-UI/CMakeLists.txt:2-5` |
| Qt modules | Core DBus Gui Network Qml Quick QuickControls2 | `Apertar-UI/CMakeLists.txt:10` |
| Other deps | OpenGL, Threads, TIFF; links `EGL`, `GLESv2` | `Apertar-UI/CMakeLists.txt:11-13`, `:207-219` |
| `APERTAR_QML_AOT` | `ON` natively, `OFF` when cross-compiling. ON → `qt_add_qml_module` (QML compiled in); OFF → `qml.qrc` | `Apertar-UI/CMakeLists.txt:56-61`, `:184-200` |
| Display power | `APERTAR_HAS_DISPLAY_POWER=1` only if `Qt6::GuiPrivate` headers exist (`qt6-base-private-dev`) | `Apertar-UI/CMakeLists.txt:223-242` |
| Lazy binding | `-z,lazy` to speed cold boot | `Apertar-UI/CMakeLists.txt:247-249` |

**QML is compiled into the binary.** With AOT on, every QML edit needs a rebuild. There is no hot reload from `qml/`.

**Trap: the executable name depends on the host.** `OUTPUT_NAME "Apertar-UI"` is only set inside `if(EXISTS "/usr/lib/qt6/libexec/moc")` (`Apertar-UI/CMakeLists.txt:252-261`). Without that file the binary is called `ApertarUI`, and `run_pi_direct.sh`, `sync_pi_runtime.sh` and the service will not find it.

### Targets and outputs (all land in `build/`)

| CMake target | Output | Purpose | Ref |
| --- | --- | --- | --- |
| `ApertarUI` | `Apertar-UI` | Touch UI | `Apertar-UI/CMakeLists.txt:63-130`, name at `:257` |
| `apertar-video-libav` | `apertar-video-libav.so` | Lazy FFmpeg movie decoder (ProRes/H.264 playback). Built only if libavcodec/libavformat/libavutil/libswscale are found | `Apertar-UI/CMakeLists.txt:134-147` |
| `ApertarCfeAutomounter` | `apertar-cfe-automounter` | CFexpress hat mount daemon | `Apertar-UI/CMakeLists.txt:149`, `:159-167` |
| `ApertarStandbyUsbPower` | `apertar-standby-usb` | Root helper: USB power off/on in standby | `Apertar-UI/CMakeLists.txt:150`, `:154-155` |
| `ApertarStandbyLowPower` | `apertar-standby-low-power` | Root helper: CPU/NVMe/Bluetooth low power | `Apertar-UI/CMakeLists.txt:151-153` |
| `ApertarNetworkHelper` | `apertar-network-helper` | Hotspot fallback daemon, Qt Core only | `Apertar-UI/CMakeLists.txt:156-158` |
| `ApertarDirectProxy` | `apertar-runtime/libproxy.so.1` | Stub `libproxy` that keeps Debian's proxy-discovery stack out of QtNetwork's cold start | `Apertar-UI/CMakeLists.txt:172-182` |

Movie plugin lookup: `<app dir>/apertar-video-libav.so`, then `<app dir>/../lib/apertar-ui/apertar-video-libav.so` (`Apertar-UI/src/VideoPlayback.cpp:26-27`).

### Where the helper binaries actually run from

| Binary | Run from | By | Ref |
| --- | --- | --- | --- |
| `apertar-network-helper` | `/home/pi/ApertarUI/build/` (build dir directly) | `apertar-network.service` | `Apertar-UI/systemd/apertar-network.service:14` |
| `apertar-standby-usb` | `/usr/local/libexec/` via `sudo -n` | Core | `Apertar-Core/src/ApertarCoreApp.cpp:1544`; sudoers `Apertar-UI/systemd/apertar-standby-usb.sudoers:1` |
| `apertar-standby-low-power` | `/usr/local/libexec/` via `sudo -n` | Core | `Apertar-Core/src/ApertarCoreApp.cpp:1549`; sudoers `Apertar-UI/systemd/apertar-standby-low-power.sudoers:1` |
| `apertar-cfe-automounter` | `/usr/local/libexec/` | `apertar-cfe-automounter.service` (live Pi) | not in repo |
| `apertar-wait-ui-core-start` | `/usr/local/libexec/` | `ExecStartPre` of `apertar-core` and of the network drop-in | `Apertar-UI/systemd/apertar-network-start-gate.conf:4`; source is `Apertar-UI/wait_for_ui_core_start.sh` (**confirmed** byte-identical, Pi 2026-10-25) |

**Rebuilding the UI does not update anything in `/usr/local/libexec`.** After changing `CfeAutomounter.cpp`, `StandbyUsbPower.cpp`, `StandbyLowPower.cpp` or `wait_for_ui_core_start.sh`, copy by hand. The sudoers rules name the exact path, so the file must stay root-owned there.

### Rebuild the UI on the Pi

```bash
ssh pi@apertar.local
cd /home/pi/ApertarUI
# First time only:
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DAPERTAR_QML_AOT=ON
cmake --build build -j2
sudo systemctl restart apertar-ui-direct
journalctl -u apertar-ui-direct -f
```

Build commands: `Apertar-UI/README.md:248-253`. Manual run: stop the service, then `bash ./run_pi_direct.sh ./build/Apertar-UI` (`Apertar-UI/README.md:283-293`).

If the image uses the runtime mirror, refresh it (next section). If you do not, `run_pi_direct.sh` notices the signature mismatch and falls back to the build-dir binary (`Apertar-UI/run_pi_direct.sh:32`), so a stale mirror is not dangerous, only slower.

After a helper change:

```bash
cmake --build build -j2
sudo install -m 755 -o root -g root build/apertar-cfe-automounter /usr/local/libexec/   # installed copies are root:root 755 (Pi, 2026-10-25)
sudo systemctl restart apertar-cfe-automounter
sudo systemctl restart apertar-network     # network helper runs from build/, restart is enough
```

### The runtime mirror (`sync_pi_runtime.sh`)

Optional copy of the UI and its libraries to `~/.cache/apertar-runtime`, meant for a faster cold boot from separate storage.

| Step | Ref |
| --- | --- |
| Args: project root (default script dir), destination (default `$APERTAR_RUNTIME_ROOT`, `$APERTAR_NVME_RUNTIME_ROOT`, then `$HOME/.cache/apertar-runtime`) | `Apertar-UI/sync_pi_runtime.sh:6-7` |
| Refuses a destination under `/media/RAW` | `Apertar-UI/sync_pi_runtime.sh:16-19` |
| Copies `build/Apertar-UI` → `bin/`, `mesa-minimal/`, `build/apertar-runtime/` | `Apertar-UI/sync_pi_runtime.sh:21-33` |
| Copies system Qt plugins and QML from `/usr/lib/aarch64-linux-gnu/qt6` | `Apertar-UI/sync_pi_runtime.sh:35-37` |
| Copies every `ldd` dependency of the UI, the movie plugin and selected Qt plugins into `lib/` | `Apertar-UI/sync_pi_runtime.sh:41-80` |
| Strips the mirrored binary | `Apertar-UI/sync_pi_runtime.sh:84-86` |
| Writes `ui-build.signature` = `size:mtime` of the source binary | `Apertar-UI/sync_pi_runtime.sh:88` |

`run_pi_direct.sh` uses the mirror only when: not disabled (`APERTAR_USE_RUNTIME_MIRROR=0`), the mirror binary and signature exist, the signature matches the build binary, and (in `auto` mode) the mirror is on a **different filesystem** than the build (`Apertar-UI/run_pi_direct.sh:13-39`). On a single-SD image the mirror is ignored in `auto` mode (`:27-29`).

Run it as `pi`: `bash ./sync_pi_runtime.sh .` (`Apertar-UI/README.md:299-303`).

### `mesa-minimal/`

A checked-in, trimmed Mesa (VC4/V3D only). `run_pi_direct.sh` prefers it when `lib/aarch64-linux-gnu/libgbm.so.1` and `share/glvnd/egl_vendor.d/50_mesa.json` exist and sets `LD_LIBRARY_PATH`, `GBM_BACKENDS_PATH`, `LIBGL_DRIVERS_PATH`, `__EGL_VENDOR_LIBRARY_FILENAMES` (`Apertar-UI/run_pi_direct.sh:41-71`). Deleting the directory falls back to system Mesa (`:41-44`). A system Mesa upgrade does not touch it.

### The committed `build/` tree

Upstream Apertar-Studio/Apertar-UI commits its `build/` directory (CMake cache generated on the Pi: `CMAKE_CACHEFILE_DIR=/home/pi/ApertarUI/build`, `Unix Makefiles`, `APERTAR_QML_AOT=ON`, Release). The Tiramisioux fork stops tracking it (commit `66d6d19`, `.gitignore`). On the Pi, `git pull` of upstream can overwrite build artefacts. The local tree has both `Makefile` and `build.ninja`; the cache says `Unix Makefiles`, so `cmake --build` uses make.

## imx585 driver

| File | Role | Ref |
| --- | --- | --- |
| `Makefile` | `obj-m += imx585.o`, builds against `/lib/modules/$(uname -r)/build` | `imx585-v4l2-driver/Makefile:1-9` |
| `dkms.conf` | Package `imx585-dkms` 0.0.1, module into `/updates`, `AUTOINSTALL=yes`, runs `dkms.postinst` | `imx585-v4l2-driver/dkms.conf:1-8` |
| `dkms.postinst` | Compiles `imx585-overlay.dts` → `imx585.dtbo`, installs to `/boot/overlays/` | `imx585-v4l2-driver/dkms.postinst:3-5` |
| `setup.sh` | `dkms remove --all`, copy tree to `/usr/src/imx585-0.0.1`, `dkms add/build/install` | `imx585-v4l2-driver/setup.sh:9-17` |

Rebuild on the Pi: `cd /home/pi/drivers/imx585-v4l2-driver && ./setup.sh && sudo reboot`. DKMS rebuilds automatically on a kernel upgrade (`AUTOINSTALL`). See [drivers.md](drivers.md).

## Startup order after a reboot

See [overview.md](overview.md#startup-order-and-readiness-files). Short form: UI starts, writes `core-start-ready`; Core's `ExecStartPre` gate waits for it (8 s max); the UI writes `main-ui-ready` on first frame; the network helper's gate waits for that.

## Things that are not in any repo

Known only from the live Pi. Check them with `systemctl cat <unit>` before relying on them.

- `apertar-core.service`, `apertar-ui-direct.service`, `apertar-cfe-automounter.service`.
- `/home/pi/start-apertar-core.sh`.
- `/usr/local/libexec/*` binaries.
- The environment of `apertar-ui-direct.service`: the UI only writes `core-start-ready` when `APERTAR_CORE_START_READY_FILE` is set (`Apertar-UI/src/main.cpp:405-420`). **Confirmed** (Pi, 2026-10-25): the unit sets `Environment=APERTAR_CORE_START_READY_FILE=/run/apertar-ui/core-start-ready`.
- Plymouth handoff wiring: `finish_plymouth_handoff.sh` exists (`Apertar-UI/finish_plymouth_handoff.sh`) and nothing in the repos calls it. **Confirmed** (Pi, 2026-10-25): the unit runs it as `ExecStartPost=+/home/pi/ApertarUI/finish_plymouth_handoff.sh /run/apertar-ui/main-ui-ready`.

## Build-dir state on the Pi (2026-10-25, `make -n`)

- `~/ApertarCore-build`: nothing to rebuild; the binary matches the source.
- `~/ApertarUI/build`: only `StandbyUsbPower.cpp.o` and `StandbyLowPower.cpp.o` would compile. The running
  copies are separate files in `/usr/local/libexec` (dated 2026-10-14), so the image's helpers were built
  elsewhere. The UI binary itself is current. Generator is Unix Makefiles (no `build.ninja`), `APERTAR_QML_AOT=ON`.
