# Build and deploy on the Pi

Detail per target (CMake options, dependencies, installed copies) is in `architecture/build.md`.
This page is the everyday loop.

## Everyday loop

| Component | Build | Restart | Logs |
| --- | --- | --- | --- |
| Core | `cmake --build ~/ApertarCore-build -j3` | `sudo systemctl restart apertar-core` | `sudo journalctl -u apertar-core -f` |
| UI | `cmake --build ~/ApertarUI/build -j3` | `sudo systemctl restart apertar-ui-direct` | `sudo journalctl -u apertar-ui-direct -f` |

Same commands exist as VS Code tasks in `~/apertar.code-workspace` (Terminal > Run Task).

- Both build dirs were configured by the image as `Release`, `Unix Makefiles`. Don't reconfigure
  them casually; CMake Tools is told not to (`cmake.configureOnOpen: false`).
- `-j3`, not `-j4`: a 4 GB Pi 5 with the camera running can run out of memory on the big
  translation units (`ApertarCoreApp.cpp`, `CameraController.cpp`). **Unconfirmed**; drop to `-j2`
  if the build is killed.
- `sudo` asks for the Pi password (default image: `1`). Claude cannot type it, so restarts are
  yours to run.

## UI runtime mirror

`run_pi_direct.sh:13-40` can run the UI from a copy in `~/.cache/apertar-runtime`. It only uses the
copy when the copy's signature matches the freshly built binary's size and mtime, so after a
rebuild it falls back to `build/Apertar-UI` automatically. No extra step needed.

## Installed copies (rebuild alone does not update these)

| Running file | Built from | Update with |
| --- | --- | --- |
| `/usr/local/libexec/apertar-cfe-automounter` | Apertar-UI target `ApertarCfeAutomounter` | see `architecture/build.md` |
| `/usr/local/libexec/apertar-standby-*` | Apertar-UI targets `ApertarStandby*` | see `architecture/build.md` |
| `/usr/local/libexec/apertar-wait-ui-core-start` | `wait_for_ui_core_start.sh` | see `architecture/build.md` |
