# Handoff: Apertar Boot Config (config.txt) — finish, verify on the Pi, follow-ups

You are the lead in a VS Code Claude Code session. Do the coordination and the risky steps yourself. Hand the bounded pieces to **Sonnet workers**: `Agent` tool, `model: "sonnet"`, one worker per independent task, and run independent workers in parallel. Brief each worker fully, because it sees only its prompt. Give it the repo, the files, the goal, what is already done, how to check its work, and what not to touch. Review every worker's diff yourself before anything is committed or pushed.

## State (2026-11-01)

- **Repo:** `Tiramisioux/Apertar-Core`, branch `claude/cool-volta-y7fiw7`, based on `drop-frames` (base at `92d0970`, head at `496817f`).
- **Draft PR:** https://github.com/Tiramisioux/Apertar-Core/pull/1. It merges cleanly. The repo has no CI and there are no reviews yet.
- **What it does:** it ports Cinemate's settings-editor config.txt mechanics (`cinemate/src/module/app/boot_config.py` and the config.txt tab) to Apertar. The file keeps the **Apertar standard layout**.
  - Apertar's `/boot/firmware/config.txt` is sectioned: `[pi4]` `[cm4]` `[cm5]` `[pi5]` `[all]`, then a DPI display list at the end.
  - Core edits it the way the file's own comments say: it comments or uncomments the line already there, or changes its parameters. It adds a line, next to its kind, only when none exists.
  - Every other byte stays the same, the `# BEGIN/END APERTAR FAN MODE` block included.
  - After an edit the new text is parsed again. A result that doesn't match the request is refused, naming the line that still decides it.
- **Files:**
  - `src/hardware/BootConfigText.hpp`: the pure engine (board and filter rules, sensor table, link-frequency menus, display table, parse, apply, read back, JSON).
  - `tools/boot_config_test.cpp`: 63 checks. Its fixture is the dev Pi's real config.txt.
  - `scripts/apertar-boot-config` and `config/apertar-boot-config.sudoers`: the root helper. It takes no arguments, reads the new text on stdin, keeps `config.txt.apertar.bak`, then syncs and renames.
  - `tools/boot_config_helper_test.sh`: 10 checks for the helper.
  - `src/ApertarCoreApp.cpp`:
    - `writeBootConfigText()` is the one writer. It writes directly when allowed, else through the helper, else with `sudo -n install`. The fan mode now uses it too, under `bootConfigMutex()`.
    - `bootConfigGet` / `bootConfigSet` back `GET/POST /api/boot-config` (with `dry_run`, the `X-Apertar-Revision` check that returns 409 when stale, and `confirm_display`), `POST /api/boot-config/parse`, and the socket commands `get_boot_config` / `set_boot_config`.
  - `src/web/WebControlPage.cpp`: the **Boot Config** card in the **System** pane.
    - Controls: a sensor per connector; the IMX477/IMX585 link frequency (greyed out until the RP1 overclock is on); the RP1 overclock (`rp1-clk-333mhz`); I²C, I²S, SPI and onboard audio; the display (HDMI only, Waveshare 4" DPI, or Hyperpixel 4" DPI).
    - Save & Reboot shows the changed lines first. A display change needs a tick. Then it saves, sends `restart_system` and waits for the camera.
    - It also has View file, Download and Upload.
  - `README.md`: a "Boot Config (config.txt)" section.
- **Tested so far:** both host tests pass. `ApertarCoreApp.cpp` compiles against libcamera headers. The card was driven in Chromium against a mock server that used the real engine. **It has never run on a Pi.**

## Tasks

### 1. Verify on the Pi (you, not a worker: it touches the camera and reboots it)

1. On the Pi, get the branch into `~/ApertarCore`, build it (`cmake --build ../ApertarCore-build -j2`), and restart `apertar-core`.
2. Install the helper:
   ```bash
   sudo install -m 0755 -o root -g root ~/ApertarCore/scripts/apertar-boot-config /usr/local/libexec/apertar-boot-config
   sudo install -m 0440 ~/ApertarCore/config/apertar-boot-config.sudoers /etc/sudoers.d/apertar-boot-config
   sudo visudo -cf /etc/sudoers.d/apertar-boot-config
   ```
3. Back up first: `sudo cp /boot/firmware/config.txt /boot/firmware/config.txt.handoff-$(date +%Y%m%d-%H%M%S)`.
4. Open WebUI → Settings → System → Boot Config. Expect IMX585 on cam0 at 891 MHz, RP1 on, I²C on, I²S and SPI off, audio on, HDMI only. Also run `printf '{"cmd":"get_boot_config"}\n' | socat - UNIX-CONNECT:/tmp/apertar-core.sock`.
5. Turn I²S on and choose **Save Only**. `diff /boot/firmware/config.txt.apertar.bak /boot/firmware/config.txt` should show only line 31 uncommented. The Core journal should read `boot config: wrote … via helper`. Then switch I²S back off and check the file is byte-identical to the backup from step 3.
6. Change the fan mode in the WebUI and check that its block is still written correctly (it now saves through the shared writer).
7. Optional: try one full **Save & Reboot** with a harmless change and confirm the card reports the camera is back.
8. Do **not** change the display or the sensor on a rig where you can't reach the camera to recover. If a reboot goes wrong, copy `config.txt.apertar.bak` back with a card reader.
9. Fix anything that fails, rerun both host tests, push to the branch, and tick the Pi checklist in the PR description.

### 2. Sonnet worker A: update the KB pages (repo `Tiramisioux/apertar-kb`, published from the Mac)

- **Goal:** the KB still says "Apertar never edits config.txt" (`working/controls/design-controls.md` ~1079–1099, `working/controls/design-controls-v1.md` ~699, `working/controls/critique-operator.md` §7). Update those pages and `architecture/config.md` §1 (the `/boot/firmware/config.txt` row: writers are now Core's Boot Config card and the fan mode, through `apertar-boot-config`). Add a short entry describing the card, its lines, the helper and the rollback via `config.txt.apertar.bak`.
- **Rules:** match the KB's style (short, factual, "unconfirmed" where untested). Mark the Pi verification from task 1 as unconfirmed until you have done it. The worker edits files only; you review, then commit from the Mac.

### 3. Sonnet worker B: make Core the only config.txt writer (repo `Tiramisioux/Apertar-UI`)

- **Goal:** `src/SystemActionBridge.cpp` (~lines 23–25, 70–132, 431–470) holds a second fan-block writer that bypasses Core's lock. Replace it with a call to Core's `set_fan_mode` socket command, following the KB's T37 "core owns the hardware file" pattern (`tutorials/inbox/…T37 core-owns-the-hardware-file.md`). Keep the UI's error messages.
- **Rules:** keep the change small. Build the UI, have the worker report its diff and how it was tested, and you review before any push. Leave `DeviceInfoBridge`'s read-only config.txt scan alone.

### 4. Sonnet worker C: fix the no-libcamera build (repo `Apertar-Core`, a separate branch from `drop-frames`)

- **Goal:** `cmake -DAPERTARCORE_ENABLE_LIBCAMERA=OFF -DAPERTARCORE_ENABLE_LIBAV=OFF` fails in `src/camera/CameraController.cpp`. The errors are `SensorFamily` undeclared, `sessionSettingsMutex_`, `settings_`, `validateTuningFilePath`, `applyProcessTuningFile`, `sanitizeSettingsForSensor` and `kLadderOwnsMode` (around lines 7617–7744 and 9983–10109). The simulate path uses helpers that are declared only in the libcamera half.
- **Done when:** `apertar-core` links without libcamera and `./apertar-core --simulate --web-port 8000` serves the WebUI. The libcamera build must not change.
- **Rules:** separate PR. Don't touch the Boot Config files.

## Rules for everyone

- Never commit or push from the Pi; it has no GitHub credentials, so publish from the Mac. Don't put credentials, Wi-Fi names or the Claude login into any repo.
- Follow the Apertar standard: never wrap config.txt in a new fence, and never regenerate it from a template.
- Before any push, rerun the fast checks:
  ```bash
  g++ -std=c++20 -O2 -Wall -Wextra -I src -I include tools/boot_config_test.cpp -o /tmp/bct && /tmp/bct
  sh tools/boot_config_helper_test.sh
  ```
- Report at the end: what passed on the Pi, what each worker changed (with commits and PR links), and anything still open.
