# Build and deploy on the Pi

Detail per target (CMake options, dependencies, installed copies) is in `architecture/build.md`.
This page is the everyday loop.

## Everyday loop

| Component | Build | Restart | Logs |
| --- | --- | --- | --- |
| Core | `cmake --build ~/ApertarCore-build -j2` | `sudo systemctl restart apertar-core` | `sudo journalctl -u apertar-core -f` |
| UI | `cmake --build ~/ApertarUI/build -j2` | `sudo systemctl restart apertar-ui-direct` | `sudo journalctl -u apertar-ui-direct -f` |

Same commands exist as VS Code tasks in `~/apertar.code-workspace` (Terminal > Run Task).

**C++ IntelliSense in VS Code (Remote-SSH), set up 2026-10-25.** Extensions installed on the Mac do not run on the Pi: `ms-vscode.cpptools` is installed on the Pi side (`~/.vscode-server/cli/servers/Stable-*/server/bin/code-server --install-extension ms-vscode.cpptools`). Core's build dir exports `compile_commands.json` (`cmake -S ~/ApertarCore -B ~/ApertarCore-build -DCMAKE_EXPORT_COMPILE_COMMANDS=ON`, kept in the CMake cache), and `~/.vscode-server/data/Machine/settings.json` sets `C_Cpp.default.compileCommands` to it, so no `.vscode/` lands in the repo. UI has no `compile_commands.json` yet. A distribution image should drop `~/.vscode-server` like `~/.claude` (`distribution-image.md`).

- Both build dirs were configured by the image as `Release`, `Unix Makefiles`. Don't reconfigure
  them casually; CMake Tools is told not to (`cmake.configureOnOpen: false`).
- `-j2` is upstream's advice (`Apertar-Core/README.md:205-210`, `Apertar-UI/README.md:248-255`); `-j1` if
  the compiler is killed for lack of memory.
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
