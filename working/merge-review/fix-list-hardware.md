# Fix list: Hardware inputs, Controls, hardware file, Boot Config

Editor's list for the merge review. Units: HW-config-text-store, HW-controls-model, HW-input-classes, Boot-config, WCP-09; plus the domain's findings from the sweeps protocol-security, stock-behaviour, board-support, knobs. Port refs `@cinemate-port` (Core `01f170c`, UI `7ea9afc`); `@04fe197` is the improvement branch. Rule ids are from `apertar-conventions.md` (HW-n, CMD-n, WEB-n). Sources: `raw/FINDINGS.json` and the unit and sweep reports.

## Already done on the improvement branches

| Commit | What | Closes |
| --- | --- | --- |
| Core `04fe197` | GPIO chip and poll_ms back on the Controls page; claims per chip; DPI and I2C bus 1 checks on the header chip only | HW-controls-model-F1 (most), X-board-support-1 |
| Core `7dc6f7a` | Core's default template is the 720x720 square screen again | App-2-F1, X-knobs-2 (Core half), X-stock-behaviour-1 (Core half) |
| UI `6a59d83` | UI display fallback is 720x720 square, hdmi_external_only=false again | UI-bridges-F1, X-board-support-2, X-stock-behaviour-1 |

## Summary

| Id | Sev | Kind | Rec | Effort | Title |
| --- | --- | --- | --- | --- | --- |
| HW-1 | blocker | security | ask-owner | M | Boot Config writes free text into config.txt as root for any LAN client |
| HW-2 | blocker | removed | fix-now | S | Config page text save is refused on validator errors the readers accept |
| HW-3 | major | security | ask-owner | S | Scripts: the browser cannot set [run_script] paths, yet can run mapped scripts without a press |
| HW-4 | major | mismatch | fix-now | M | Boot Config has its own write route with cmd splicing, a revision header, 403/409 and an Origin rule |
| HW-5 | major | mismatch | fix-now | S | config.txt root write has three routes, a stdin root helper and a sudoers file in Core |
| HW-6 | major | bug | fix-now | S | Boot Config ignores include camera-selection.txt and adds a second sensor overlay |
| HW-7 | major | removed | fix-now | S | A Standby wake press still fires click and Hold gestures |
| HW-8 | major | removed | fix-now | S | A button that reads pressed at start is inverted for the session, overriding active_low |
| HW-9 | major | stock | fix-now | S | No first-run hardware file is written (display defaults already restored) |
| HW-10 | major | new-ground | keep-and-document | M | hwconf is a second table-driven model of every reader in one 1141-line header, and it has drifted |
| HW-11 | major | new-ground | keep-and-document | L | Boot Config engine: 1355-line header-only framework that writes wire JSON |
| HW-12 | major | mismatch | fix-now | M | ActionCatalog replaces the drivers' flat alias chains with a CSV table and a second action parser |
| HW-13 | major | mismatch | fix-now | M | Controls page keeps its own store (controlsState) and its own fetch wrapper (controlsCall) |
| HW-14 | major | mismatch | fix-now | S | Remote controls card on the main page with hold-to-repeat and a load-time retry loop |
| HW-15 | major | new-ground | ask-owner | L | 2100-line structured hardware editor: chip box, pin-claim cascade, review re-derivation, one-entry dropdown |
| HW-16 | minor | removed | fix-now | S | set_controls refuses keys the readers use, hides others, and accepts hold_ms/double_ms nobody reads |
| HW-17 | minor | bug | fix-now | S | A key edit on a duplicated section writes the copy the readers ignore |
| HW-18 | minor | bug | fix-now | S | An IMU write on a /boot-only rig creates a partial /home/pi file that hides the /boot file |
| HW-19 | minor | protocol | fix-now | M | Whole-file text through set_controls skips the upstream empty/size/NUL checks |
| HW-20 | minor | protocol | fix-now | M | Hardware-file replies carry machine codes, issue arrays, a merge-review path with no client and an Origin rule |
| HW-21 | minor | mismatch | fix-now | M | Six hardware commands run before commandMutex_, and get_controls writes state |
| HW-22 | minor | duplication | fix-now | S | Two config.txt readers with different section filters; the Controls one reads as a Pi 5 |
| HW-23 | minor | bug | fix-now | S | Sensor list of the Boot Config card lacks IMX283 |
| HW-24 | minor | board | fix-later | S | Boot Config board model: unknown read as Pi 5, Zero 2 W as pi3, link cap only for pi4 |
| HW-25 | minor | board | fix-later | S | Core's free-pin list and output line limit stay fixed to the 40-pin header |
| HW-26 | minor | board | fix-later | S | Any DPI line greys GPIO 0-27, in the page and in Core's validator |
| HW-27 | minor | bug | fix-now | S | Saving one Controls card silently drops the other card's unsaved edits |
| HW-28 | minor | bug | fix-now | S | Tally card: switching off erases the pin |
| HW-29 | minor | bug | fix-now | S | Pins recovered by regex from Core's display text |
| HW-30 | minor | mismatch | fix-now | S | JSON built in hardware headers with string + and its own escaper; defaults repeated |
| HW-31 | minor | new-ground | keep-and-document | S | GPIO edge-event loop: keep, but stop by eventfd, drain fully, and use member functions |
| HW-32 | minor | new-ground | fix-later | S | Switch positions apply toggle actions at start and on every Controls save |
| HW-33 | minor | new-ground | fix-later | M | Remote-only buttons stored as remote<N> in [gpio_buttons] |
| HW-34 | minor | bug | fix-later | S | Status probes and scan_i2c read chips the UI process polls |
| HW-35 | minor | mismatch | fix-later | S | Listen is a second 300 ms network poll loop |
| HW-36 | minor | duplication | fix-later | S | Storage keys: three copies of the store.edit block and two refresh policies |
| HW-37 | minor | removed | keep-and-document | S | Touch-UI fan mode now needs Core |
| HW-38 | minor | slop | fix-later | S | Comments and README carry Cinemate references, ticket numbers, names and history |
| HW-39 | minor | new-ground | keep-and-document | S | Host tests for the Boot Config engine and helper |
| HW-40 | minor | mismatch | fix-later | S | Controls page idioms: two feedback channels, duplicated helpers, inline style, loader naming |
| HW-41 | nit | duplication | fix-later | S | gpioChipScore half-shared |
| HW-42 | nit | mismatch | fix-later | S | Listen wiring: seen callback by setter, gesture suffix arrays in three copies |
| HW-43 | nit | bug | fix-later | S | Store: `by` written raw into hardware-state.conf; 100 ms sleep under the store mutex |

## HW-1. Boot Config writes free text into config.txt as root for any LAN client

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| security | blocker | M | yes | ask-owner | Boot-config-F3, X-protocol-security-1 |

**Where.** `src/ApertarCoreApp.cpp:3800-3812@cinemate-port`; `src/hardware/BootConfigText.hpp:1133-1139@cinemate-port`; `scripts/apertar-boot-config:51-54@cinemate-port`; `src/web/WebControlPage.cpp (Boot Config card: Edit file / Use This Text)@cinemate-port`

**Problem.** set_boot_config takes a text field (the card's Edit file), checks only textProblem (non-empty, <= 64 KiB, no NUL), lays the card's choices on top (applyRequest) and writes the result to /boot/firmware/config.txt as root (App:3802-3812, confirmed). kernel=, os_prefix=, initramfs, start_file= and any overlay pass. One unauthenticated request can leave the camera unbootable or boot another kernel. The revision check is no guard: any client reads it with get_boot_config first.

**Apertar way.** Root writes carry generated content only: the fan mode is one of fixed values and Core builds the block (fanModeBlock App:3042, install App:3155-3158@upstream-1.6.0). 'Fixed executable and arguments only; never accept paths from WebUI/config.' (App:1543@upstream-1.6.0). The free-text editor upstream is apertar-hardware.conf, written as pi (App:5323-5385@upstream-1.6.0). WEB-6: the LAN is trusted, but never with root free text.

**Rework.**

1. bootConfigSet (App ~3775-3846): delete the command.string("text") branch, the textProblem call and the before/changes/displayChanged recompute for edited text.
2. BootConfigText.hpp: delete textProblem, lineChanges (LCS), displayDiffers and the managed[] list that only the text editor uses; keep parse, readState, applyRequest with read-back.
3. WebControlPage.cpp Boot Config card: delete Edit file, Use This Text and the line-diff review; keep View file and Download as read-only (a GET like GET /api/config).
4. Delete POST /api/boot-config/parse.
5. README: drop the Edit file paragraph.

**Owner decision.** Drop the card's free-text editor (recommended: only lines built from validated fields reach config.txt, about 300 lines less, matches the fan-mode pattern; cost: hand edits of config.txt go back to ssh), or keep it and refuse boot-chain keys (kernel, cmdline, os_prefix, initramfs, start_file, fixup_file, device_tree, overlay_prefix, boot_*) plus no install fallback (cost: a deny-list the original developer must maintain and a root free-text path he will likely refuse)?

**Risk.** Removes a feature the owner added himself (3b87d99).

**Check here.** Build /home/user/build/core-port (-DAPERTARCORE_ENABLE_LIBCAMERA=OFF); run apertar-core --simulate with APERTAR_BOOT_CONFIG=<scratch copy>; send {"cmd":"set_boot_config","text":"kernel=x"} over /tmp/apertar-core.sock: must be refused or ignored; tools/boot_config_test.cpp still passes.

**Needs the Pi.** None for the refusal. After the cut: one card save on a Pi 5 and a Pi 4, then sudo cat /boot/firmware/config.txt and reboot.

## HW-2. Config page text save is refused on validator errors the readers accept

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| removed | blocker | S | yes | fix-now | HW-config-text-store-F1, HW-controls-model-F7 |

**Where.** `src/hardware/HardwareConfigStore.cpp:336-342@cinemate-port`; `src/ApertarCoreApp.cpp:8640-8642@cinemate-port`; `src/hardware/HardwareConfigText.hpp:756-1009@cinemate-port`; `src/hardware/ActionCatalog.hpp:134-246@cinemate-port`

**Problem.** saveLocked refuses a whole-text save when hwconf::validate finds new errors and flags.force is not set (Store.cpp:336-341, confirmed). POST /api/config never sets force and the page has no 'save anyway'. Error rules cover cases the C++ readers accept (duplicate_key: the later line wins; unknown_action from classify(); gpio_twice; address_range). The original developer's Config textarea now answers 400 to files 1.6.0 saved and ran.

**Apertar way.** saveHardwareConfigFile saves any text that is non-empty, <= 256 KiB and NUL-free (App:5323-5385@upstream-1.6.0). HW-12: unknown keys are ignored, unknown actions only logged at run time (App:8954@upstream-1.6.0). HW-19: the raw text is the operator's surface.

**Rework.**

1. HardwareConfigStore::saveLocked: for the text path (text != nullptr) skip the newErrors refusal; write, then return issues in the ok reply. The page already lists issues after a successful save (WCP:18938-18940).
2. Keep the newErrors refusal only for key edits (edits != nullptr, the Controls cards).
3. hwconf::validate: unknown_action becomes a warning, not an error (HW-12).
4. Delete StoreFlags.force once no caller needs it.

**Owner decision.** None.

**Risk.** Low. Easy-mode cards keep their guard.

**Check here.** --simulate with APERTAR_HARDWARE_CONFIG=<scratch file>; in the browser Config page save a file with a duplicate key and an unknown action: saved, issues shown. A Controls key edit that adds a pin clash is still refused.

**Needs the Pi.** Nothing.

## HW-3. Scripts: the browser cannot set [run_script] paths, yet can run mapped scripts without a press

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| security | major | S | yes | ask-owner | HW-config-text-store-F2, X-protocol-security-2, HW-controls-model-F11 |

**Where.** `src/hardware/HardwareConfigStore.cpp:34-42,330-335@cinemate-port`; `src/ApertarCoreApp.cpp:12392-12415@cinemate-port`; `src/hardware/HardwareScriptRunner.cpp:86-90@cinemate-port`

**Problem.** Two halves of one trust question. (a) Every save whose [run_script] path* keys differ is refused ('Script paths are changed over ssh, not here.'), Undo and restore included (Store.cpp:330-335, confirmed); upstream let the WebUI write them. (b) test_input runs whatever a key holds through handleHardwareInputAction (App:12410), and remoteN rows skip the section-on check, so a LAN client can map remote0=run_script1 and run a script with no physical press. Correction to X-protocol-security-2: at cinemate-port the path half of its chain is blocked by (a), so today only scripts set over ssh can be run; if (a) is undone alone, the full chain opens.

**Apertar way.** WebUI writes the whole file, [run_script] included (App:7175-7193@upstream-1.6.0; WEB-6 trusted LAN). handleHardwareInputAction is called only from input callbacks and the standby wake (App:6786-6792, :8613@upstream-1.6.0): a script ran only on a physical press.

**Rework.**

1. ApertarCoreApp::testInputReply: before handleHardwareInputAction, refuse an action list holding a script action: for each token, if hardware::scriptActionSlot(token) >= 0 return errorReply(command.id, "Scripts run from a button, not from the WebUI.").
2. HardwareConfigStore: delete scriptPaths() and its check in saveLocked (upstream trust model), so Undo and restore work again.
3. README: one line that scripts run only from a physical control.

**Owner decision.** Your decision Q2 (script paths ssh-only) differs from 1.6.0. Recommended: restore upstream (the browser edits paths) and refuse scripts in test_input; cost: a LAN client can point a button at any readable file, as in 1.6.0, but it only runs on a press. Alternative: keep Q2, then exempt Undo and restore from the path check and document Q2 in the README; cost: a rule the original developer does not have.

**Check here.** --simulate; save [run_script] path1=/tmp/x.sh and [gpio_buttons] remote0=run_script1; test_input section=gpio_buttons key=remote0 must reply with the refusal; Undo after an ssh path edit succeeds.

**Needs the Pi.** Nothing.

## HW-4. Boot Config has its own write route with cmd splicing, a revision header, 403/409 and an Origin rule

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| mismatch | major | M | yes | fix-now | Boot-config-F1, X-protocol-security-7 |

**Where.** `src/ApertarCoreApp.cpp:9170-9196@cinemate-port`; `src/ApertarCoreApp.cpp:3775-3836@cinemate-port`; `src/ApertarCoreApp.cpp:14586-14590@cinemate-port`; `src/web/WebControlPage.cpp:20004-20016@cinemate-port`

**Problem.** POST /api/boot-config splices "cmd":"set_boot_config" into the body, parses it with parseControlCommand, reads x-apertar-revision, and requires the revision only when an Origin header is present. bootConfigSet returns BootConfigReply{status, body} with 200/400/403/409/500 under its own bootConfigMutex(). /api/command reaches the same setter with browser=false and no revision need. One setter, two doors, two guard sets.

**Apertar way.** Commands go handleWebCommand -> parseControlCommand -> handleCommand (App:7085-7091@upstream-1.6.0); the page's fan mode is sendCommand({cmd:"set_fan_mode", value}) (WCP:11093) handled in handleCommand (App:10568-10577@upstream-1.6.0). No upstream route reads custom headers or returns 403/409. CMD-1, CMD-3, CMD-9, WEB-3.

**Rework.**

1. Delete the POST /api/boot-config write route, BootConfigReply, the browser/Origin parameter and the x-apertar-revision header.
2. get_boot_config and set_boot_config become ordinary blocks in the handleCommand chain, under commandMutex_, replying okReply/errorReply; delete bootConfigMutex() (commandMutex_ now serialises them with set_fan_mode).
3. revision, dry_run, confirm_display stay flat string fields (CMD-8); a missing revision on a non-dry-run save is refused with an operator sentence.
4. WCP bootConfigPost -> sendCommand({cmd:"set_boot_config", ...}) in try/catch with showToast (WEB-14). A read-only GET for the file text may stay, as GET /api/config.

**Depends on.** HW-1

**Owner decision.** None.

**Risk.** The page reads ok/error instead of HTTP status.

**Check here.** Build; --simulate with APERTAR_BOOT_CONFIG=<scratch>; drive the card in a browser: dry run, save, stale revision refused; grep -n 'api/boot-config' src returns only the read route.

**Needs the Pi.** Nothing.

## HW-5. config.txt root write has three routes, a stdin root helper and a sudoers file in Core

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| mismatch | major | S | yes | fix-now | Boot-config-F2, Boot-config-F8, Boot-config-F12, X-board-support-11, X-knobs-16, X-protocol-security-9 |

**Where.** `src/ApertarCoreApp.cpp:3533-3611@cinemate-port`; `scripts/apertar-boot-config:1-71@cinemate-port`; `config/apertar-boot-config.sudoers:4@cinemate-port`; `tools/boot_config_helper_test.sh@cinemate-port`; `README.md:199-207@cinemate-port`

**Problem.** writeBootConfigText tries a direct write (access W_OK, temp + fsync + rename), then sudo -n /usr/local/libexec/apertar-boot-config < staged (a POSIX sh helper that takes content on stdin and refuses a file without [pi5]/[pi4]/[all]), then sudo -n install. Fan mode now goes through it too. The permission error prints install commands and is wrong when the helper exists without sudoers. The README calls the helper optional.

**Apertar way.** One call: "sudo -n install -m 644 " + shellQuote(tempPath) + " " + shellQuote(kBootConfigPath) and 'Changing the fan mode needs sudo permission.' (App:3155-3164@upstream-1.6.0). Upstream root helpers live in the UI repo as C++ with a fixed verb in sudoers and a timeout (UI systemd/apertar-standby-usb.sudoers; App:1544-1549@upstream-1.6.0). PLT R14 steps 5-6; conventions section 5: no root helpers or helper scripts in Core.

**Rework.**

1. writeBootConfigText: stage a temp file, sudo -n install -m 644 <dest> <dest>.apertar.bak, sudo -n install -m 644 <tmp> <dest>; on failure 'Writing config.txt needs sudo permission.' Keep a plain write only for the APERTAR_BOOT_CONFIG test path.
2. Delete scripts/apertar-boot-config, config/apertar-boot-config.sudoers, tools/boot_config_helper_test.sh, kBootConfigHelper, fsyncPath (if no other caller) and the README install block.
3. applyFanMode keeps calling writeBootConfigText (now the upstream route), so the [all] header rule goes away.

**Depends on.** HW-1

**Owner decision.** None.

**Risk.** Loses fsync+rename on FAT; upstream install has the same property.

**Check here.** Build; grep -rn 'apertar-boot-config' src scripts config README.md is empty; --simulate fan-mode change against a scratch APERTAR_BOOT_CONFIG.

**Needs the Pi.** Card save and fan-mode change on a stock image (pi has NOPASSWD sudo): sudo -n true; then check /boot/firmware/config.txt and config.txt.apertar.bak.

## HW-6. Boot Config ignores include camera-selection.txt and adds a second sensor overlay

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| bug | major | S | unknown | fix-now | Boot-config-F5, X-board-support-3 |

**Where.** `src/hardware/BootConfigText.hpp:289-293,616-622@cinemate-port`; `tools/boot_config_test.cpp:56@cinemate-port`

**Problem.** lineFrom gives a line without '=' no key, so 'include camera-selection.txt' never counts. On such a file the card shows no sensor; choosing IMX585 uncomments a second dtoverlay while the included file still loads one, and the read-back agrees because it reads the file the same way. The fixture keeps the image comment about the include, with the include itself removed. Probable: the stock image config.txt is not in this container.

**Apertar way.** 'Apertar's camera-selection file is authoritative' (UI src/DeviceInfoBridge.cpp:213-215@upstream-1.6.0).

**Rework.**

1. bootconf::readState: an uncommented include line in a section that applies to this board sets editable=false for the camera rows and adds the sentence 'config.txt includes camera-selection.txt: the sensor comes from that file.' in the same shape as state.problem.
2. Add a fixture to tools/boot_config_test.cpp with the include line present.

**Owner decision.** None.

**Check here.** g++ tools/boot_config_test.cpp with the new fixture; --simulate card shows camera rows read-only.

**Needs the Pi.** On a fresh Apertar-Beta 1.6.0 image: grep -n '^include' /boot/firmware/config.txt; cat /boot/firmware/camera-selection.txt.

## HW-7. A Standby wake press still fires click and Hold gestures

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| removed | major | S | no | fix-now | HW-input-classes-F1 |

**Where.** `src/hardware/ButtonGesture.hpp:21-55@cinemate-port`; `src/hardware/GpioInput.cpp:641-653@cinemate-port`; `src/hardware/Pcf8574Input.cpp:454-467@cinemate-port`; `src/hardware/NeoRotary4Input.cpp:632-650@cinemate-port`; `src/ApertarCoreApp.cpp:10312-10318@cinemate-port`

**Problem.** handleHardwareInputAction turns the first press in Standby into wake and returns (App:10312-10318, confirmed), but it returns void, so ButtonGesture keeps counting. Single/Double/Triple/Hold fire later with the camera awake. d17_hold=standby: holding d17 in Standby wakes and sleeps again; d17_double=photo wakes and takes a photo.

**Apertar way.** HW-5: in Standby a press only wakes and is consumed. StandbyPowerButtonInput.cpp:66-71@upstream-1.6.0 'gesture.consume(); // A wake press cannot seed another sleep.' with a std::function<bool(bool)> callback (StandbyPowerButtonInput.hpp:8,14).

**Rework.**

1. ButtonGesture.hpp: add consume() (clear clicks, mark the press as long/held so release fires nothing), as PowerButtonGesture::consume does.
2. ApertarCoreApp::handleHardwareInputAction returns bool: true when it dispatched wake.
3. GpioInput, Pcf8574Input, NeoRotary4Input: the button ActionCallback becomes std::function<bool(const std::string &)>; emitAction returns the result (false for an empty action); on true call button.gesture.consume(). The rotation callback stays void.
4. Cover the case with no Press mapped: the first gesture that reaches App in Standby is the wake and is consumed the same way.

**Owner decision.** None.

**Check here.** Build; a scratch g++ harness that drives ButtonGesture through press, wake-consume, release, 3 s hold: no Single or Hold after consume (not committed: upstream has no tests).

**Needs the Pi.** d17=record_toggle, d17_hold=standby, d17_double=photo; put the camera in Standby; hold d17 3 s and double-click: camera wakes and stays awake, no photo. journalctl -u apertar-core.

## HW-8. A button that reads pressed at start is inverted for the session, overriding active_low

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| removed | major | S | yes | fix-now | HW-controls-model-F2, HW-input-classes-F2 |

**Where.** `src/hardware/GpioInput.cpp:620-629@cinemate-port`; `src/hardware/Pcf8574Input.cpp:423-432@cinemate-port`

**Problem.** On the first sample GpioInput sets button.inverted = level and Pcf8574Input builds invertedMask ('Like Cinemate: ... a 1-0-1 button', confirmed). A button held while Core starts, while the controls worker restarts GPIO after a save, or at a reopen after an I2C read error, is inverted until the next restart: every release then fires its action. A stuck contact is silently flipped.

**Apertar way.** Polarity is stated by the operator per section with active_low (GpioInput.cpp:433-434, Pcf8574Input.cpp:372@upstream-1.6.0); no guessing (HW-12, HW-19). Reopen only re-seeds observed/stable state (GpioInput.cpp:643-679@upstream-1.6.0).

**Rework.**

1. GpioInput::run: delete haveSample/inverted and the start-sample branch; pressed = level as upstream.
2. Pcf8574Input::run: delete invertedMask and its start-sample branch.
3. Keep NeoRotary4Input heldAtStartMask (NeoRotary4Input.cpp:611,626-630): it only ignores a push held at open until release, as upstream.
4. If per-pin normally-closed buttons are wanted, add a per-pin key in the header Config and loadConfig (R11), e.g. d17_active_low=false / pin3_active_low=false; not part of this fix.

**Owner decision.** Drop the start-up guess (recommended; cost: a rig with a normally-closed button must set active_low or a new per-pin key) or keep it as documented new ground (cost: held buttons get inverted at every save of the GPIO group)?

**Check here.** Build; diff GpioInput.cpp and Pcf8574Input.cpp against core-upstream for the polarity lines.

**Needs the Pi.** Hold d17 while sudo systemctl restart apertar-core; release; press again: one action per press, and no 'taken as inverted' line in journalctl.

## HW-9. No first-run hardware file is written (display defaults already restored)

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| stock | major | S | yes | fix-now | X-stock-behaviour-2, X-stock-behaviour-1, X-board-support-2, X-knobs-2 |

**Where.** `Apertar-UI src/DisplayConfigBridge.cpp (ensureDefaultHardwareConfigFile removed, c9d841f)@cinemate-port`; `Apertar-UI src/Ina219Bridge.cpp (writer removed)@cinemate-port`; `src/ApertarCoreApp.cpp:6200-6201@cinemate-port`

**Problem.** Done: the HDMI-rig display fallback is back to 720x720 / square / hdmi_external_only=false in Core's template (Core 7dc6f7a) and in the UI constants, loadConfiguration and header (UI 6a59d83), both on the improvement branches. Open: 1.6.0's UI writes its template when /home/pi/apertar-hardware.conf is missing; the port removed both UI writers (c9d841f) because a file moved away came back. On a fresh camera no file appears, the WebUI editor shows Core's template, and the UI runs on compiled fallbacks; Core's template lacks chip=auto, the input tuning and [mpu6050] (App-2-F2).

**Apertar way.** UI DisplayConfigBridge.cpp:41,:577-587@upstream-1.6.0 ensureDefaultHardwareConfigFile; HW-7: the template lives in three places by hand (Core defaultHardwareConfigTemplate, UI DisplayConfigBridge, UI Ina219Bridge).

**Rework.**

1. Restore ensureDefaultHardwareConfigFile in UI DisplayConfigBridge.cpp and the Ina219Bridge writer from upstream-1.6.0, writing only when no candidate path (env, /home/pi, /boot/firmware, /boot) has a file.
2. Core HardwareConfigStore keeps its replaced-file check (014fa22) for later starts, so a moved file is reported, not silently replaced.
3. Bring Core's defaultHardwareConfigTemplate back in step with the UI template for chip=auto, input tuning and [mpu6050] (HW-7).

**Owner decision.** Restore the UI's first-run writer as in 1.6.0 (recommended; cost: the 'moved file comes back' case returns, softened by the store's replaced-file report) or make Core the single first-run writer through HardwareConfigStore (cost: new ground, and the UI's template copy must still match)?

**Risk.** Same problem as UI-bridges-F1/F2 and App-2-F1/F2 in other domains: fix once.

**Check here.** Build UI (/home/user/build/ui-port) and Core; run UI with HOME pointing to a scratch dir and no file: the file appears with 720x720 square.

**Needs the Pi.** Fresh SD card: ls -l /home/pi/apertar-hardware.conf after first boot; touch UI visible on the 720x720 panel.

## HW-10. hwconf is a second table-driven model of every reader in one 1141-line header, and it has drifted

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| new-ground | major | M | yes | keep-and-document | HW-config-text-store-F3, HW-config-text-store-F10 |

**Where.** `src/hardware/HardwareConfigText.hpp:5-6,27-69,157-208@cinemate-port`; `src/hardware/HardwareConfigText.hpp:800-815@cinemate-port`

**Problem.** kSections[] holds per-section aliases and value rules; canonicalSection/canonicalKey map channel/i2c_bus/bus_number/pcf_bus to bus and addr/pcf_address to address for every section (HCT:169-170). The readers differ: Pcf8574Input.cpp:273 takes only bus/channel/i2c_bus, so for [pcf8574] pcf_bus=10 the validator checks bus 10 while the reader uses bus 1. The header also includes util/BufferBudget.hpp and util/StoragePreroll.hpp (CinemaDNG and capture code) to check [storage]/[media].

**Apertar way.** HW-2: each class parses its own section, no shared parser; HW-11: aliases are flat key == chains per reader (Pcf8574Input.cpp:366-371@upstream-1.6.0); HW-6: src/hardware includes only std, Linux and hardware headers; HW-23: .cpp listed in add_executable. The store itself (HardwareConfigStore) replacing saveHardwareConfigFile is accepted new ground (App-2-F11).

**Rework.**

1. Split into src/hardware/HardwareConfigText.hpp (types, declarations) and HardwareConfigText.cpp, listed by name in CMakeLists add_executable (HW-23).
2. canonicalKey becomes per section only: one flat key == chain per section with a comment naming the reader line it mirrors; delete the global alias lines 169-170.
3. validate(): delete the [storage]/[media] branches and the two util includes; App appends bufferConfProblem/prerollConfProblem issues after hwconf::validate, next to refreshBufferRequest.
4. Keep parse, join, applyEdit, diff, validate (advisory for text saves, HW-2).
5. Handoff note: the validator mirrors the readers; a new key goes into the reader and into its canonicalKey branch.

**Depends on.** HW-2

**Owner decision.** None.

**Check here.** Build both configurations; a scratch host check: [pcf8574] pcf_bus=10 is reported as an unknown key, not as bus 10.

**Needs the Pi.** Nothing.

## HW-11. Boot Config engine: 1355-line header-only framework that writes wire JSON

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| new-ground | major | L | yes | keep-and-document | Boot-config-F4, Boot-config-F6 |

**Where.** `src/hardware/BootConfigText.hpp:1-1355@cinemate-port`; `src/hardware/BootConfigText.hpp:1225-1340@cinemate-port`; `src/ApertarCoreApp.cpp:3651-3846@cinemate-port`

**Problem.** apertar::bootconf holds the board model, sensor and link tables with Mbps and 4K fps labels, Document/Editor, a 315-line applyRequest with read-back, an LCS lineChanges, stateJson/changesJson/jsonString (its own escaper, nested objects and arrays) and an FNV-1a revisionOf, plus about 195 App and 730 WCP lines. Most of the size serves the free-text editor (HW-1) and decoration.

**Apertar way.** Upstream has the fan block only (fanModeBlock/stripManagedFanBlock/detectManagedFanMode, App:3042-3117@upstream-1.6.0). Header-only hardware modules are small (ButtonActionList.hpp 121 lines); larger logic is a .hpp/.cpp pair (HW-23). CMD-9: JSON written in App with ostringstream and escapeJson; HW-6: no wire format in src/hardware.

**Rework.**

1. Keep the in-place edit approach (BCT:8-13 weighs it against a fenced block) and applyRequest with read-back for sensor, link, toggles, RP1 and display.
2. With HW-1: delete lineChanges, displayDiffers, textProblem, managed.
3. Delete mbpsPerLane, fps4k, linkOptionLabel; keep a list of Hz values; labels go to the page.
4. Move stateJson/changesJson/jsonString to App as bootConfigBody(state) using escapeJson; one "boot_config":{...} object of scalars plus the fixed option lists; drm[] becomes a count.
5. Make it src/hardware/BootConfig.{hpp,cpp}, .cpp in add_executable. Target 600-700 lines.
6. Handoff: document the read-back safety (a result that differs from the request is not written).

**Depends on.** HW-1, HW-4

**Owner decision.** None.

**Risk.** The read-back must survive the cut.

**Check here.** tools/boot_config_test.cpp links the new .cpp and passes; build; card driven against --simulate.

**Needs the Pi.** One sensor change and one display toggle on a Pi 5, then reboot.

## HW-12. ActionCatalog replaces the drivers' flat alias chains with a CSV table and a second action parser

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| mismatch | major | M | yes | fix-now | HW-controls-model-F5, HW-controls-model-F6, HW-controls-model-F7, HW-controls-model-F8 |

**Where.** `src/hardware/ActionCatalog.hpp:18-358@cinemate-port`; `src/hardware/GpioInput.cpp:114@cinemate-port`; `src/hardware/Pcf8574Input.cpp:144@cinemate-port`; `src/hardware/NeoRotary4Input.cpp:125@cinemate-port`; `src/hardware/TriggerOutput.cpp:131-143@cinemate-port`; `src/hardware/GroveAnalogInput.cpp:126-129@cinemate-port`; `src/ApertarCoreApp.cpp:1645-1655,10090,12534-12554@cinemate-port`

**Problem.** kSpecs[] rows {id, group, label, 'a,b,c' aliases, sources, ui, Arg, token} matched with listHas; the three drivers, TriggerOutput, GroveAnalogInput and App call into it. classify() re-parses the parametric grammar (ev/fps/resolution/iso/shutter/wb) beside App's executing parser. list_actions serves values, values_for, gestures (wrong: buttons have more than press), analog_targets and trigger_events that no client reads.

**Apertar way.** HW-15: each input has its own normalizeSingleAction (flat || chains, GpioInput.cpp:108-202, Pcf8574Input.cpp:140, NeoRotary4Input.cpp:121@upstream-1.6.0) passed to normalizeButtonMapping (ButtonActionList.hpp:80,113); parametric names parsed only in the handler (App:1342-1370@upstream-1.6.0). TriggerOutput.cpp:130-148 and GroveAnalogInput.cpp:125-145@upstream-1.6.0 map tokens directly.

**Rework.**

1. Restore the three normalizeSingleAction bodies verbatim from upstream and add the port's new names (clear_hdr, ev_up/ev_down, ...) as || terms in each.
2. Restore TriggerOutput eventFromToken, GroveAnalogInput normalizeTarget and App's analog-target normaliser from upstream (zero diff in those two driver files).
3. Restore App hardwareActionSuffix/parseHardwareActionNumber from upstream; delete classify, Classified, compact, number, numberAfter, suffixAfter, kTriggerEvents, canonicalTriggerEvent, kAnalogTargets, canonicalAnalogTarget, normalizeToken.
4. Reduce kSpecs to {id, group, label, sources} for the page; the validator warns on a token that is neither a catalog id nor starts with iso/fps/wb/ev/shutter/res.
5. list_actions replies "actions" (plus max_per_mapping if the page uses it) only.

**Owner decision.** None.

**Risk.** Alias sets must match across the three copies; diff against upstream.

**Check here.** Build; git diff core-upstream -- src/hardware/TriggerOutput.cpp src/hardware/GroveAnalogInput.cpp is empty; a scratch check that every alias of 1.6.0 still maps to the same action in all three drivers.

**Needs the Pi.** Nothing.

## HW-13. Controls page keeps its own store (controlsState) and its own fetch wrapper (controlsCall)

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| mismatch | major | M | unknown | fix-now | WCP-09-F1, WCP-09-F2, WCP-09-F7 |

**Where.** `src/web/WebControlPage.cpp:16633,16698-16705,16798,16881,17216,18183-18189,18516-18528,18577-18648@cinemate-port`

**Problem.** const controlsState = {loading, saving, revision, model, ...} beside module-level controlsChipLines, controlsSeparateTurns, controlsReplaced, controlsListenTimer/Seq. controlsCall posts /api/command and 15 sites test result.ok by hand; 7 have no try/catch. Scan stays at 'Scanning...' after one failed request until reload; Listen overlaps; Undo has no busy flag.

**Apertar way.** WEB-12: all client state on the one state object (WCP:4204-4266@upstream-1.6.0), timers state.<x>Timer, busy state.<x>InFlight (config editor :10265-10359). WEB-3/WEB-14: sendCommand (WCP:9109-9145) throws new Error(result.error); handlers try/catch with showToast. Plain fetch only for background traffic (user_activity :11509).

**Rework.**

1. Move every controlsState field to flat state fields (state.controlsModel, controlsRevision, controlsCatalog, controlsPeripherals, controlsEdits, controlsButtons, controlsRemoved, controlsAdded, hardwareEdits, controlsLoadInFlight, controlsSaveInFlight, controlsListenTimer, controlsListenInFlight, controlsChipLines, controlsSeparateTurns, controlsReplaced); delete controlsState and the module-level lets.
2. Label tables move to the option-list block near const fpsPresets (WEB-8).
3. sendCommand: attach the reply: const error = new Error(result.error || "Command failed."); error.result = result; throw error; (as the port's /api/config save already does, WCP:18930-18931).
4. User actions (save, undo, scan, test, history, get_controls, list_actions) use sendCommand in try/catch/finally; saves read error.result.issues; loading flags cleared in finally; Undo sets controlsSaveInFlight.
5. The Listen poll stays a plain fetch (sendCommand schedules an /api/state refresh) with controlsListenInFlight. Delete controlsCall.

**Owner decision.** None.

**Risk.** Mechanical rename across about 300 references.

**Check here.** --simulate; headless Chromium: load Controls, kill Core mid-Scan, restart: Scan button usable again; console has no unhandled rejection; grep -c 'controlsState\|controlsCall' WCP = 0.

**Needs the Pi.** Nothing.

## HW-14. Remote controls card on the main page with hold-to-repeat and a load-time retry loop

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| mismatch | major | S | yes | fix-now | WCP-09-F3 |

**Where.** `src/web/WebControlPage.cpp:4569-4580,17995-18112,20870-20878@cinemate-port`

**Problem.** A 'Remote controls' card sits under Camera settings in the main grid; pills call test_input; knob arrows repeat while held (pointer capture, 450 ms delay, 140 ms interval); bootstrap retries get_controls every 5 s until Core answers. The owner chose to keep the feature (fork-log.md:163-164).

**Apertar way.** WEB-2: the main grid holds only camera-critical cards (preview, Camera settings, System, Current capture, WCP:2456-2726@upstream-1.6.0); everything else is a settings-card in a panel, data loaded in setSettingsPanel (:6164-6166). No hold-to-repeat upstream.

**Rework.**

1. Move the card to the Controls settings panel as a settings-card; build pills with buildOptionButtons; one test_input per click.
2. Load its data from setSettingsPanel("controls"); delete the main-page card markup and the 5 s bootstrap retry.
3. Delete hold-to-repeat, or keep it as the one documented new-ground widget (owner).

**Depends on.** HW-13

**Owner decision.** Keep hold-to-repeat on the knob arrows (cost: a widget behaviour no other control has, to be documented) or drop it (recommended; cost: a turn needs one tap per step)?

**Risk.** Operators lose one-tap access from the main page.

**Check here.** --simulate; main page shows the four upstream cards only; Controls panel shows Remote controls; no get_controls request before the panel opens (browser network log).

**Needs the Pi.** Nothing.

## HW-15. 2100-line structured hardware editor: chip box, pin-claim cascade, review re-derivation, one-entry dropdown

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| new-ground | major | L | yes | ask-owner | WCP-09-F4, WCP-09-F9, WCP-09-F17 |

**Where.** `src/web/WebControlPage.cpp:16622-18740@cinemate-port`; `src/web/WebControlPage.cpp:16799-16872@cinemate-port`; `src/web/WebControlPage.cpp:17312-17343,17821,17859-17870,18452-18486@cinemate-port`

**Problem.** 74 functions: per-device cards, gesture dropdowns, a duck-typed fake select with draggable chips (Object.defineProperty, '__several__' sentinel), Turn-adjusts pairing by _up/_down id and label regex, a pin claim that removes another control after a confirm, a review that re-derives moved rows, a one-option Function dropdown. Larger than any upstream WebUI feature; pin ownership rules duplicated from Core's validator.

**Apertar way.** No precedent: upstream edits apertar-hardware.conf as text via POST /api/config (WCP:10330-10359@upstream-1.6.0); a feature is 20-40 lines in 3-5 places. WEB-15: pills or native selects, no custom dropdown components; WEB-19: unavailable choices disabled.

**Rework.**

1. Keep: rows, action dropdown from list_actions, gesture dropdown, add/remove, pin dropdowns with disabled 'used by' options, revision-checked set_controls save, Hardware card fields.
2. Drop the chip box: a multi-action line shows '(as written in the file)' (buildControlsSelect already does, WCP:16785-16790) and is edited in Config text.
3. Drop controlsClaimPin's cascade (a disabled option is the rule), the moved-row re-derivation in renderControlsReview, and controlsOutputFunctions (title the row 'Tally light').
4. Keep Turn adjusts only if Core's catalog sends the pair.
5. Handoff: one page describing what stays as new ground.

**Depends on.** HW-13

**Owner decision.** Approve cutting the chip box, the pin-claim cascade and the review re-derivation (recommended; cost: multi-action lines are edited as text, a used pin must be freed by hand), or keep them all as documented new ground (cost: about 2100 lines of page code the original developer must maintain)?

**Risk.** Owner-visible feature reduction.

**Check here.** --simulate; headless Chromium: add a button, map an action, save, reload; a used pin shows disabled; a multi-action line shows '(as written in the file)'.

**Needs the Pi.** Nothing.

## HW-16. set_controls refuses keys the readers use, hides others, and accepts hold_ms/double_ms nobody reads

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| removed | minor | S | unknown | fix-now | HW-controls-model-F3, HW-controls-model-F4, X-knobs-1, X-knobs-12 |

**Where.** `src/hardware/HardwareConfigText.hpp:456-478@04fe197`; `src/hardware/ControlsModel.hpp:81-84,132-201,264-303@cinemate-port`; `src/hardware/ButtonGesture.hpp:16-18@cinemate-port`

**Problem.** knownKey (checked at 04fe197) accepts only enabled and encoderN_* in [gpio_encoders], so chip/active_low/pull/poll_ms/debounce_ms there are refused with "'poll_ms' is not a key of [gpio_encoders] that Apertar reads" though GpioInput reads them (GpioInput.cpp:431-445@upstream-1.6.0) and the 1.6.0 UI template wrote them. The outputs accept active_high but not active_low or pin. open_drain, pulse_ms, events, Grove aN rows are not on the page. hold_ms and double_ms are accepted for three sections but the gesture times are constexpr.

**Apertar way.** TriggerOutput.cpp:311-337 and RecordingIndicatorOutput.cpp:347-370@upstream-1.6.0 read chip, line, pin, open_drain, active_high, active_low, pulse_ms, events; UI DisplayConfigBridge.cpp:172-176@upstream-1.6.0 writes poll_ms and debounce_ms into [gpio_encoders]. HW-19: behaviour timing fixed in code, no dead keys.

**Rework.**

1. knownKey: gpio_encoders accepts chip, active_low, pull, poll_ms, debounce_ms; recording_indicator and trigger_output accept active_low and pin.
2. knownKey: remove hold_ms and double_ms from gpio_buttons, pcf8574, neorotary4.
3. ControlsModel peripheralSettings: add open_drain to both outputs, pulse_ms and events to the trigger.
4. Grove analog: either rows in controlRows or one sentence on the page that [grove_analog] channels are edited in Config.
5. A button row with an output action (dN=recindicatorled) shows the action as read-only text.

**Owner decision.** None.

**Check here.** --simulate; set_controls set.gpio_encoders.poll_ms=3 is written; set.gpio_buttons.hold_ms=1000 is refused.

**Needs the Pi.** Nothing.

## HW-17. A key edit on a duplicated section writes the copy the readers ignore

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| bug | minor | S | no | fix-now | HW-config-text-store-F4 |

**Where.** `src/hardware/HardwareConfigText.hpp:537-550@cinemate-port`; `src/hardware/Mpu6050RecordingSession.cpp:605-623@cinemate-port`; `src/ApertarCoreApp.cpp:12829-12925@cinemate-port`

**Problem.** applyEdit Set replaces the key only in the first copy of a section and stops at the second header (HCT:538-545, confirmed: 'a second copy of the section: leave it'). Readers use the later line. Trusted writes skip checkEdits' duplicate refusal: IMU calibration and orientation, set_buffer_mode, set_frames_per_folder, set_clip_merge, set_storage_preroll. calibrate_gyro replies ok and the old bias stays in effect: a setting is lost.

**Apertar way.** writeHardwareConfigValue re-enters the section at every header of that name and rewrites the key in each copy (Mpu6050RecordingSession.cpp:628-668@upstream-1.6.0). HW-8.

**Rework.**

1. hwconf::applyEdit Set: walk every copy of the section and replace the key in each; insert a new line (in the last copy) only when no copy has the key.
2. Unset already removes in all copies; leave it.

**Owner decision.** None.

**Check here.** Scratch host check: text with [mpu6050] twice, the second holding gyro_bias_x=12; applyEdit gyro_bias_x=5: both copies read 5.

**Needs the Pi.** Nothing.

## HW-18. An IMU write on a /boot-only rig creates a partial /home/pi file that hides the /boot file

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| bug | minor | S | yes | fix-now | HW-config-text-store-F6, HW-input-classes-F9 |

**Where.** `src/hardware/Mpu6050RecordingSession.cpp:603-628@cinemate-port`; `src/hardware/HardwareConfigStore.cpp:118-123,154-163@cinemate-port`

**Problem.** IMU writes go through configStore().edit on the editable path. When that file is missing, the store starts from empty text and creates /home/pi/apertar-hardware.conf with only the [mpu6050] keys. Every reader takes the first existing candidate, so on the next start the /boot/firmware sections (buttons, IMU, displays) are gone. Rare: the UI first-run writer usually created /home/pi first (see HW-9).

**Apertar way.** HW-9: write only to the editable path (upstream App writes WebUI saves to editableHardwareConfigPath, App:4271-4276@upstream-1.6.0); the upstream IMU wrote the file the loader read (Mpu6050RecordingSession.cpp:1297-1300@upstream-1.6.0), so nothing was lost.

**Rework.**

1. HardwareConfigStore::saveLocked (or refreshLocked): when the editable file does not exist and a later candidate (/boot/firmware, /boot) does, start current from that file's text. buildHardwareConfigFileJson already uses this rule (App:6187-6200).
2. The write still goes only to the editable path.

**Owner decision.** None.

**Check here.** --simulate with APERTAR_HARDWARE_CONFIG pointing to a missing file and a scratch /boot copy via the candidate list; send an IMU orientation command; the new file holds every section.

**Needs the Pi.** Nothing.

## HW-19. Whole-file text through set_controls skips the upstream empty/size/NUL checks

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| protocol | minor | M | yes | fix-now | HW-config-text-store-F5, WCP-09-F12 |

**Where.** `src/ApertarCoreApp.cpp:12763-12799@cinemate-port`; `src/ApertarCoreApp.cpp:6227-6248@cinemate-port`; `src/web/WebControlPage.cpp:18588,18795@cinemate-port`

**Problem.** checkHardwareConfigText runs only in POST /api/config. set_controls text= (Undo, and Check with dry_run) goes straight to store.replace: {"cmd":"set_controls","base":"<rev>","text":""} writes an empty file and every reader falls back to defaults. Two doors with different checks for the same file.

**Apertar way.** WEB-4: whole-file work is a route, POST /api/config (WCP:10336-10340, App:7175-7195@upstream-1.6.0); the three checks guard that one write (App:5325-5343@upstream-1.6.0). Key-level command writes are precedented (set_imu_*).

**Rework.**

1. Move the empty/size/NUL checks into HardwareConfigStore::replace so every caller gets them; delete checkHardwareConfigText.
2. WCP Undo posts the history text through POST /api/config with its revision; Check uses the same route with a dry-run query flag (?dry_run=1).
3. set_controls drops the text field; key-level set_controls stays.
4. With text gone, the socket line cap raised to 1 MiB for whole-file set_controls (Build-scripts-docs-F10) can return to 64 KiB.

**Depends on.** HW-20

**Owner decision.** None.

**Check here.** --simulate; set_controls with text= is refused as an unknown field or ignored; Undo and Check work in the browser; an empty POST /api/config is 400.

**Needs the Pi.** Nothing.

## HW-20. Hardware-file replies carry machine codes, issue arrays, a merge-review path with no client and an Origin rule

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| protocol | minor | M | unknown | fix-now | HW-config-text-store-F7, HW-config-text-store-F8, HW-config-text-store-F9 |

**Where.** `src/hardware/HardwareConfigStore.hpp:21-38@cinemate-port`; `src/hardware/HardwareConfigText.hpp:1103-1139@cinemate-port`; `src/ApertarCoreApp.cpp:8628-8654,12801-12843@cinemate-port`; `src/web/WebControlPage.cpp:18233,18661,18948@cinemate-port`

**Problem.** Refusals carry code (locked, being_written, stale, conflict, edits, errors, script_paths, backup, write) plus issues/new_errors/conflicts arrays via errorReplyBody; WCP branches on code in three places. A stale text save that changed only values becomes key edits (textToEdits) and needs confirm_merge, which no client sends. POST /api/config without X-Apertar-Revision gets 409 old_page only when an Origin header is present (App:8632-8637, confirmed).

**Apertar way.** CMD-9: replies only via okReply/errorReply with an operator sentence; upstream App has no "code" member. CMD-28: the refusal is shown as written. A fallible helper returns bool and writes std::string *errorMessage (saveHardwareConfigFile, App:5323@upstream-1.6.0). Upstream POST /api/config is last-writer-wins with a .bak, no headers.

**Rework.**

1. HardwareConfigStore::saveLocked returns bool, writes std::string *errorMessage and a bool *stale out-flag; delete StoreResult.code/merged/needsReview, StoreFlags.confirmMerge and hwconf::textToEdits. A stale text save is just stale; keep per-key conflicts() for key edits.
2. App: stale maps to HTTP 409 on the route, with the 'your text stays in the box' sentence inside the message; every other refusal is errorReply. Issues travel only in ok replies and get_controls.
3. POST /api/config: a missing revision header means base = current revision for every client; check only when the header is present (delete the Origin test).
4. WCP: delete the three code branches; show the message.

**Owner decision.** None.

**Check here.** Build; grep -n '"code\\"' src/ApertarCoreApp.cpp in the config/controls paths is empty; --simulate: two tabs save in turn, the second gets 409 with the sentence.

**Needs the Pi.** Nothing.

## HW-21. Six hardware commands run before commandMutex_, and get_controls writes state

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| mismatch | minor | M | yes | fix-now | X-protocol-security-5, HW-controls-model-F16 |

**Where.** `src/ApertarCoreApp.cpp:12418-12556@cinemate-port`; `src/ApertarCoreApp.cpp:12559-12571@cinemate-port`; `src/ApertarCoreApp.cpp:12439-12447@cinemate-port`

**Problem.** handleReadOnlyHardwareCommand answers get_controls, controls_history, controls_last_input, scan_i2c, list_actions before the lock (App:12562-12563, confirmed); test_input also runs before it. get_controls writes controlsErrors_/controlsWarnings_, erases pendingUnitSince_, spawns systemctl show per pending unit, and parses the same text 8 times. scan_i2c checks for a take once, then probes up to 117 addresses unlocked.

**Apertar way.** CMD-3: one lock on the first line of handleCommand (App:9093@upstream-1.6.0). CMD-21: a slow job becomes a worker with polled state (media speed test). CMD-25: repeated work reused locally.

**Rework.**

1. Move get_controls, controls_history, controls_last_input, list_actions and scan_i2c into the locked if chain; delete handleReadOnlyHardwareCommand.
2. Keep only test_input before the lock, with its comment (its actions take the lock themselves).
3. get_controls: const hwconf::Document doc = hwconf::parse(info.text); once, passed to each peripheral.
4. Move the systemctl probe and the counter updates into the controls worker.
5. If scan_i2c is slow under the lock, make it a worker with polled state (CMD-21).

**Owner decision.** None.

**Risk.** Same area as App-4-F1 (other domain): fix once.

**Check here.** Build; --simulate: Controls panel loads, Scan works; a record_start sent during scan_i2c waits or is refused cleanly.

**Needs the Pi.** Time scan_i2c on bus 1 and 10 under the lock: time echo '{"cmd":"scan_i2c","bus":"1"}' | socat - UNIX:/tmp/apertar-core.sock.

## HW-22. Two config.txt readers with different section filters; the Controls one reads as a Pi 5

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| duplication | minor | S | no | fix-now | HW-config-text-store-F11, HW-config-text-store-F12, Boot-config-F10, X-board-support-5 |

**Where.** `src/hardware/HardwareConfigText.hpp:1029-1101@cinemate-port`; `src/ApertarCoreApp.cpp:4976@cinemate-port`; `src/hardware/BootConfigText.hpp:102-117,248-253@cinemate-port`; `src/ApertarCoreApp.cpp:3709-3718@cinemate-port`

**Problem.** hwconf::parseConfigTxt applies only [all] and [pi5] (HCT:1037); BootConfigText::filterApplies is board-aware. On a Pi 4 or CM5 the Controls validator and the Boot Config card give different DPI answers; with HW-2 open, false gpio_dpi errors block saves. dpiCommands, BootFacts.i2cArm and BootFacts.dpiOverlays have no caller. boolFieldValue accepts on/yes/off/no as a tri-state.

**Apertar way.** Upstream reads each file one way; booleans are == "true" || == "1" (CMD-8, App:9486@upstream-1.6.0). Conventions section 6: board by SoC compatible, no Pi-5-only path.

**Rework.**

1. Delete parseConfigTxt, BootFacts and dpiCommands from HardwareConfigText.
2. hardwareConfigFacts() (App:4976) takes the DPI lines from bootconf::readState(bootconf::parseDocument(text, board), board).displayLines with the detected board.
3. boolFieldValue becomes the upstream test.

**Owner decision.** None.

**Check here.** Scratch host check: a config.txt with dtoverlay=vc4-kms-dpi-... under [pi4] gives DPI lines on a pi4 board and none on pi5.

**Needs the Pi.** Pi 4 or CM4 with a DPI overlay under [pi4]: Controls page greys the right pins.

## HW-23. Sensor list of the Boot Config card lacks IMX283

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| bug | minor | S | no | fix-now | Boot-config-F11 |

**Where.** `src/hardware/BootConfigText.hpp:151-171@cinemate-port`

**Problem.** The sensor table and its comment ('the sensors Core has handling for ... imx577, imx477, imx294, imx585') have no imx283 entry (grep confirms), though the port's detectSensorFamily returns Imx283 (CC:2569-2570) and the imx283 driver ships an overlay. With dtoverlay=imx283,cam0 the card shows an unlisted sensor and cannot switch to IMX585 and back.

**Apertar way.** R5 (add a sensor): every hand-copied sensor list follows the sensor support.

**Rework.**

1. Add {"imx283", "imx283", "IMX283", false, 0, 0, {}} to the table and fix the comment.
2. Add a fixture line to tools/boot_config_test.cpp.

**Owner decision.** None.

**Check here.** g++ tools/boot_config_test.cpp passes with an imx283 fixture.

**Needs the Pi.** Nothing.

## HW-24. Boot Config board model: unknown read as Pi 5, Zero 2 W as pi3, link cap only for pi4

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| board | minor | S | unknown | fix-later | Boot-config-F9, X-board-support-4, X-board-support-6 |

**Where.** `src/hardware/BootConfigText.hpp:76-122,147,182-205@cinemate-port`; `src/ApertarCoreApp.cpp:3653-3657@cinemate-port`

**Problem.** A third board detector matches by substring (bcm2712/bcm2711/bcm2837/bcm2710) and sets family pi5 when nothing matched (BCT:96, confirmed). [pi3] lines count on a Zero 2 W (firmware behaviour unconfirmed). linkOptionsFor caps the link list only for pi4, so a Pi 3 gets the Pi 5 list with 'fps at 4K' and 'over RP1 spec' labels; a rate the driver refuses means no camera after reboot (probable).

**Apertar way.** Conventions section 6: board by exact SoC compatible (RecordingCapabilities.hpp:18-35, DefaultTuningSelection.hpp:18-31@upstream-1.6.0); unknown is Unknown, no guess (DefaultTuningSelection.hpp:67).

**Rework.**

1. Derive family from upstream's exact SoC strings with one inline helper beside recordingCapabilitiesFromCompatible; the card uses it.
2. Unknown board: editable=false with a sentence; the Pi 5 reading only for a host without a device tree (the APERTAR_BOOT_CONFIG test path).
3. linkOptionsFor: the list is offered only for pi5; other families get the driver's default rate only; drop fps/RP1 text there.
4. Zero 2 W filters: decide after a board test.

**Depends on.** HW-11

**Owner decision.** None.

**Check here.** tools/boot_config_test.cpp with fake compatible strings for each family.

**Needs the Pi.** Zero 2 W: put a test line under [pi3] and check vcgencmd get_config <key> after reboot. Pi 4: cat /proc/device-tree/compatible.

## HW-25. Core's free-pin list and output line limit stay fixed to the 40-pin header

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| board | minor | S | yes | fix-later | HW-controls-model-F1 |

**Where.** `src/hardware/ControlsModel.hpp:273,386@04fe197`

**Problem.** Done on the improvement branch (04fe197, worktree /home/user/wt/core-work): the chip and poll_ms rows are back, claims are per chip, the DPI and I2C bus 1 checks apply to the header only, pin dropdowns list the chosen chip's lines. Open: Core's model still lists free pins 4..27 and caps output line at 27 ('the page lifts it for another chip'), so a non-page client sees header limits.

**Apertar way.** HW-17: chip auto or explicit path; GPIO readers accept lines 0..63 (GpioInput.cpp:233@upstream-1.6.0).

**Rework.**

1. ControlsModel: take the chosen chip's line count from readGpioChipInfo (GpioChipInfo.cpp) and use it for the free list and the line max; drop the JS lift.

**Owner decision.** None.

**Check here.** --simulate with two faked chips in get_controls (as 04fe197 tested): free list follows the chip.

**Needs the Pi.** A second gpiochip (MCP2221 or I2C expander): gpiodetect; buttons on that chip work.

## HW-26. Any DPI line greys GPIO 0-27, in the page and in Core's validator

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| board | minor | S | yes | fix-later | WCP-09-F13 |

**Where.** `src/web/WebControlPage.cpp:17198-17200,17260-17264,18209@cinemate-port`; `src/hardware/HardwareConfigText.hpp:844-845,869-871@cinemate-port`

**Problem.** With any DPI overlay in config.txt, pins 0..27 of the header are taken in the page and refused by the validator. 16/18-bit DPI modes leave upper GPIO free (probable), so those pins cannot be used for buttons.

**Apertar way.** No precedent.

**Rework.**

1. Core computes the pins each detected overlay holds (from the overlay name/params read in HW-22) and sends them as dpi_pins (one string, CMD-8).
2. Validator and page use that set; delete the page's own 0..27 loops.

**Depends on.** HW-22

**Owner decision.** None.

**Check here.** Scratch host check of the overlay-to-pins table.

**Needs the Pi.** Read the pin maps of the DPI overlays in use: dtoverlay -h vc4-kms-dpi-generic on the Pi.

## HW-27. Saving one Controls card silently drops the other card's unsaved edits

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| bug | minor | S | no | fix-now | WCP-09-F5 |

**Where.** `src/web/WebControlPage.cpp:18240,18256-18297,18667@cinemate-port`

**Problem.** saveHardware and saveControls call loadControls(true), which resets settingEdits, edits, added, removed, buttons without a confirm; each save sends only its own card. Change GPIO 6 Press on Controls, change a NeoRotary setting on Config, Save Hardware: the GPIO 6 change is gone.

**Apertar way.** WEB-21: window.confirm before discarding edits ('Reload Apertar config and discard unsaved edits?', WCP:10307@upstream-1.6.0).

**Rework.**

1. After a save, reload the model only when the other card is clean; otherwise update state.controlsRevision and keep the other card's key-level edits, or ask with window.confirm.

**Depends on.** HW-13

**Owner decision.** None.

**Check here.** --simulate; headless Chromium reproduces the sequence above; the GPIO 6 edit survives or a confirm appears.

**Needs the Pi.** Nothing.

## HW-28. Tally card: switching off erases the pin

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| bug | minor | S | yes | fix-now | WCP-09-F11 |

**Where.** `src/web/WebControlPage.cpp:17617-17646,17704-17705,17900-17913@cinemate-port`

**Problem.** The enabled field is hidden; syncTallyEnabled writes enabled from 'pin set'; None and Remove write line=-1, pcf_pin=-1. A file with enabled=false shows its pin as None. Turning the tally on again needs the pin re-entered: wiring is lost.

**Apertar way.** RecordingIndicatorOutput reads enabled (:339) and line (:349@upstream-1.6.0) independently. WEB-15: On/Off is a two-pill grid over toggleOptions.

**Rework.**

1. Show enabled as On/Off over toggleOptions; leave line/pcf_pin untouched by it.
2. Delete tallyFileEnabled, syncTallyEnabled and the special cases in tallyShown and Remove.

**Owner decision.** None.

**Check here.** --simulate; switch the tally off and on: line= stays in the file.

**Needs the Pi.** Nothing.

## HW-29. Pins recovered by regex from Core's display text

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| bug | minor | S | no | fix-now | WCP-09-F6 |

**Where.** `src/web/WebControlPage.cpp:17163-17189,17598@cinemate-port`; `src/hardware/ControlsModel.hpp:163,193-194,353@cinemate-port`

**Problem.** controlsRowPinInfo parses row.title /^GPIO (\d+)(?: \+ (\d+))?$/ and row.detail /^A (\d+), B (\d+), push (\d+|none)$/. With encoder0_b missing the detail is 'A 5, B ?, push none', the regex fails, the encoder gets no pin dropdowns and GPIO 5 is offered unmarked to another control.

**Apertar way.** WEB-13: render reads data fields from the snapshot; no label parsing.

**Rework.**

1. ControlsModel row JSON: add "pins":"5,6,13" (one string, CMD-8) next to "pin".
2. controlsRowPinInfo splits it; delete the regexes.

**Owner decision.** None.

**Check here.** --simulate with an encoder missing _b: dropdowns shown, GPIO 5 marked used.

**Needs the Pi.** Nothing.

## HW-30. JSON built in hardware headers with string + and its own escaper; defaults repeated

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| mismatch | minor | S | no | fix-now | HW-controls-model-F9, HW-controls-model-F10 |

**Where.** `src/hardware/ControlsModel.hpp:50-71,255-388@cinemate-port`; `src/hardware/ActionCatalog.hpp:336-358@cinemate-port`

**Problem.** hwconf::jsonEscape; modelJson and peripheralSettingsJson build JSON with std::string +, relying on transitive includes. SettingSpec repeats every reader's defaults (debounce 60, poll 30/40/80, addresses 0x49/0x20/0x04, deadband 32, trigger line 17).

**Apertar way.** CMD-9: JSON with std::ostringstream and escapeJson in App (App:167-215@upstream-1.6.0; the port's own gpioPeripheralJson does this). HW-12: defaults are in-class initialisers of each reader's Config (GpioInput.hpp:45-57, Pcf8574Input.hpp:28-38, TriggerOutput.hpp:46-51@upstream-1.6.0). HW-6.

**Rework.**

1. ControlsModel.hpp keeps data only (controlRows, gpioPinsInUse, peripheralSettings).
2. Move modelJson, peripheralSettingsJson, catalogJson into App's anonymous namespace beside gpioPeripheralJson, with ostringstream and escapeJson; delete hwconf::jsonEscape.
3. Make each reader's Config struct public (one access change per header) and build the fallbacks from GpioInput::Config{}, Pcf8574Input::Config{}, ... during serialisation.

**Depends on.** HW-12

**Owner decision.** None.

**Check here.** Build; get_controls JSON byte-identical before and after on --simulate (diff the two replies).

**Needs the Pi.** Nothing.

## HW-31. GPIO edge-event loop: keep, but stop by eventfd, drain fully, and use member functions

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| new-ground | minor | S | yes | keep-and-document | HW-controls-model-F13, HW-input-classes-F3, HW-input-classes-F4, HW-input-classes-F5 |

**Where.** `src/hardware/GpioInput.cpp:612-856@cinemate-port`; `src/hardware/ButtonGesture.hpp:55-65@cinemate-port`

**Problem.** GpioInput now waits on kernel edge events (both edges, poll() until an edge or the next gesture deadline), falling back to poll_ms on chips without events. The loop wakes every 250 ms so stop() is seen, reads at most 16 events per wake then always does a full readLineValues (events 17..N are applied on top of the newer level: probable spurious encoder steps), and is built around a 95-line capturing lambda.

**Apertar way.** HW-14 (usually): sleep_for(pollMs) loop (GpioInput.cpp:740@upstream-1.6.0). Precedent for poll() on a device fd with an eventfd stop: StandbyPowerButtonInput.cpp:16-31,50-56@upstream-1.6.0. Helpers are private members (readLineValues, emitAction, setLastError).

**Rework.**

1. Keep edge events and the poll_ms fallback; say so in the handoff (tested on GPIO 6 and 10).
2. Add stopFd_ (eventfd) as in StandbyPowerButtonInput; stop() writes it; run() polls both fds with timeout = next debounce/gesture deadline or -1.
3. Drain the line fd until read returns fewer than 16 events; do the catch-up readLineValues only on a wake with no events.
4. Turn the lambdas into private members: void processLevels(uint64_t levels, steady_clock::time_point now), int wakeTimeoutMs(int64_t nowMs) const, with runtime vectors in a run-state struct.
5. Optionally use gpio_v2_line_event::timestamp_ns as the event time.

**Depends on.** HW-7, HW-8

**Owner decision.** None.

**Check here.** Build both configurations.

**Needs the Pi.** Spin a GPIO encoder fast: counts match detents; sudo systemctl restart apertar-core returns within 1 s; strace -p <GpioInput tid> shows no 250 ms wakes when idle.

## HW-32. Switch positions apply toggle actions at start and on every Controls save

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| new-ground | minor | S | yes | fix-later | HW-input-classes-F6, HW-input-classes-F2 |

**Where.** `src/hardware/GpioInput.cpp:656-686@cinemate-port`; `src/ApertarCoreApp.cpp:12302-12319@cinemate-port`

**Problem.** [gpio_switches] applies the position action at each GpioInput start and on each change. GpioInput restarts on every save touching the GPIO/PCF group and at each reopen after a read failure. The monitoring vocabulary is toggles: switch0_on=zebra with zebra already on flips it off at start and again at each save.

**Apertar way.** No precedent; upstream inputs fire on press edges only (GpioInput.cpp:691-710@upstream-1.6.0); absolute settings exist only as parametric tokens (iso800, fps24, wb5600).

**Rework.**

1. Keep the switches as documented new ground.
2. Validator and Controls page: switch positions take absolute actions only (parametric tokens, or *_on/*_off handlers added in App that end in dispatchHardwareInputCommand, HW-3).
3. Apply the start position only once per Core start: keep an 'applied' flag outside the reopen and controls-worker restart path.

**Depends on.** HW-31

**Owner decision.** None.

**Check here.** Scratch host check of the validator rule.

**Needs the Pi.** A two-position switch on GPIO: save Controls twice; journalctl shows one position action at start only.

## HW-33. Remote-only buttons stored as remote<N> in [gpio_buttons]

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| new-ground | minor | M | yes | fix-later | HW-controls-model-F11 |

**Where.** `src/hardware/ControlsModel.hpp:141-149,203-207@cinemate-port`; `src/hardware/HardwareConfigText.hpp:459@cinemate-port`

**Problem.** remote0..15 keys live in [gpio_buttons], which GpioInput owns and must skip; App runs them through test_input without the section-on check.

**Apertar way.** CMD-12: one section = the class that parses it. An App-parsed section is precedented ([ina219], App:4450@upstream-1.6.0).

**Rework.**

1. Give remote buttons their own section read by App, e.g. [remote_buttons] b0=, b0_single=; register it in kSections; drop remote from knownKey(gpio_buttons).
2. Move existing remote<N> keys once (the store's applyEdits can do it on first load), or ask the owner to move his by hand.

**Depends on.** HW-3, HW-14

**Owner decision.** None.

**Risk.** Existing remote<N> keys need a one-time move.

**Check here.** --simulate; Remote controls card fires b0.

**Needs the Pi.** Nothing.

## HW-34. Status probes and scan_i2c read chips the UI process polls

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| bug | minor | S | no | fix-later | HW-controls-model-F15 |

**Where.** `src/hardware/I2cProbe.hpp:2-3@cinemate-port`; `src/ApertarCoreApp.cpp:12097,12495-12521@cinemate-port`

**Problem.** cfeHatPeripheralJson probes bus 10 0x34 on every get_controls; scan_i2c holds only neorotary4/pcf8574/grove and reads every other address, INA219 on bus 4 included. A one-byte read between the UI's register-pointer write and its read can return the wrong register (probable).

**Apertar way.** HW-21: Core and UI touch the same chips with no IPC lock; upstream Core never probes the UI's chips.

**Rework.**

1. scan_i2c: add the [ina219] and [cfexpress_hat] addresses to the held set as 'ui'.
2. Report the hat from the automounter's state instead of probing it. No lock (HW-21).

**Owner decision.** None.

**Check here.** Build.

**Needs the Pi.** Run scan_i2c bus 4 while the UI shows battery: no glitch in the battery value.

## HW-35. Listen is a second 300 ms network poll loop

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| mismatch | minor | S | yes | fix-later | WCP-09-F8 |

**Where.** `src/web/WebControlPage.cpp:18600-18649@cinemate-port`

**Problem.** setInterval 300 ms on controls_last_input, auto-off after 120 s or when the panel hides; timer and seq in module-level let.

**Apertar way.** WEB-7/WEB-13: one network poll, fetchState every 1 s (WCP:11609@upstream-1.6.0); timers on state.

**Rework.**

1. Recommended: add controls_last_input_seq/section/key to /api/state and highlight from renderSnapshot (1 s latency, no new loop).
2. Or keep the user-started poll with timer, seq and in-flight flag on state, as a plain fetch in try/catch.

**Depends on.** HW-13

**Owner decision.** None.

**Check here.** --simulate; press a fake input via test_input; the row lights within 1 s.

**Needs the Pi.** Nothing.

## HW-36. Storage keys: three copies of the store.edit block and two refresh policies

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| duplication | minor | S | no | fix-later | HW-config-text-store-F14 |

**Where.** `src/ApertarCoreApp.cpp:8655-8660,12808-12813,12828-12925@cinemate-port`

**Problem.** set_buffer_mode, set_frames_per_folder/set_clip_merge and set_storage_preroll each build StoreFlags, call store.edit, map the refusal, update counters, wake the worker and always refreshBufferRequest; set_controls and POST /api/config repeat the post-write block but refresh only when written.

**Apertar way.** CMD-25: a shape repeated inside one function becomes a local lambda (App:9478@upstream-1.6.0).

**Rework.**

1. If the storage keys stay in the hardware file (Media-buffer-split-F1 may move them out; decide there first): one local lambda writeStorageKey(section, key, value) in handleCommand and one App helper afterHardwareWrite(const StoreResult &) shared with the route; one refresh policy (refresh when written).

**Owner decision.** None.

**Check here.** Build; the three commands behave as before on --simulate.

**Needs the Pi.** Nothing.

## HW-37. Touch-UI fan mode now needs Core

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| removed | minor | S | yes | keep-and-document | Boot-config-F7 |

**Where.** `Apertar-UI src/SystemActionBridge.cpp:66-97,406-412@cinemate-port`

**Problem.** UI 41ff827 deletes the UI's own fan writer and sends set_fan_mode over a QLocalSocket (8 s timeout); with Core down: 'Connect to Apertar Core before changing the fan mode.' The reason is real: a UI write outside Core's lock could overwrite a Boot Config save.

**Apertar way.** Each process carries its own fan writer (App:3042-3165 vs UI SystemActionBridge.cpp:64-100@upstream-1.6.0). The client follows the synchronous QLocalSocket bridge shape (MediaStatusBridge.cpp:20-42@upstream-1.6.0).

**Rework.**

1. Keep; one paragraph in the handoff: config.txt has one writer (Core) since Boot Config edits it.

**Depends on.** HW-5

**Owner decision.** Keep the single writer in Core (recommended while Boot Config exists; cost: no fan change with Core stopped), or restore the UI's writer (cost: a fan change can overwrite a Boot Config save)?

**Check here.** Build UI.

**Needs the Pi.** Commit says 'build only': change fan mode from the touch UI, then sudo grep -n 'APERTAR FAN' /boot/firmware/config.txt.

## HW-38. Comments and README carry Cinemate references, ticket numbers, names and history

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| slop | minor | S | no | fix-later | HW-config-text-store-F13, HW-controls-model-F14, HW-input-classes-F10, Boot-config-F13, Boot-config-F15, WCP-09-F15 |

**Where.** `src/hardware/HardwareConfigText.hpp:116,317,1006,1082@cinemate-port`; `src/hardware/HardwareConfigStore.hpp:3,20@cinemate-port`; `src/hardware/ButtonGesture.hpp:2-3,20@cinemate-port`; `src/hardware/GpioInput.cpp:623,662,667,735@cinemate-port`; `src/hardware/Pcf8574Input.cpp:425@cinemate-port`; `src/hardware/ActionCatalog.hpp:25,151,315@cinemate-port`; `src/hardware/BootConfigText.hpp:2-28,42,151-153,197-205@cinemate-port`; `src/ApertarCoreApp.cpp:3651,8658,12459,12477,12487,12811@cinemate-port`; `src/web/WebControlPage.cpp:16622-18740 (127 comment lines)@cinemate-port`; `README.md:211@cinemate-port`

**Problem.** 'Like Cinemate', 'cinemate src/module/gpio_input.py', 'Ported from Cinemate's settings-editor config.txt tab', T39-T44 ticket ids, 'for Patrik to run', core.py (in neither tree), 'the text the touch UI used to write', "the WebUI's Listen" inside src/hardware, stale comments ('Call on every poll', 'The Outputs card reads this list'), '(unconfirmed on hardware)' in an operator string, 9 section banners, non-ASCII label glyphs, a README list of socket commands; 127 JS comment lines in the Controls code.

**Apertar way.** STY / conventions section 5: no ticket numbers, no history; rare one-line hazard comments (PowerButtonGesture.hpp:4,26@upstream-1.6.0). WEB-18: no comments in the page (2 lines in 7573). HW-6: no UI feature names in src/hardware.

**Rework.**

1. Delete Cinemate references, ticket ids, person names, history narration and banners; rewrite the timing comment in Apertar terms ('Press fires at once; releases within 500 ms count as clicks; held 3 s is Hold').
2. Say 'socket clients' instead of core.py; 'the template the touch UI writes' (Store.cpp:62).
3. Remove '(unconfirmed on hardware)' from the operator string; ASCII labels.
4. BootConfigText header to two lines; keep the hazard comment at BCT:950.
5. WCP Controls code: keep at most a one-line reason where a rule is not obvious.
6. README: drop the socket-command paragraph.

**Owner decision.** None.

**Check here.** grep -rnE 'Cinemate|cinemate|T[0-9]{2}\b|Patrik|core\.py' src/hardware src/ApertarCoreApp.cpp src/web/WebControlPage.cpp returns nothing in this domain.

**Needs the Pi.** Nothing.

## HW-39. Host tests for the Boot Config engine and helper

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| new-ground | minor | S | yes | keep-and-document | Boot-config-F14 |

**Where.** `tools/boot_config_test.cpp:1-427@cinemate-port`; `tools/boot_config_helper_test.sh:1-33@cinemate-port`

**Problem.** A plain g++ test with the dev Pi's config.txt as fixture, and an sh test of the helper. Neither is in CMake.

**Apertar way.** Conventions section 5 and R14 step 7: no tests, no test target upstream.

**Rework.**

1. The helper test goes with HW-5.
2. Keep tools/boot_config_test.cpp outside the build only if the owner keeps tools/*_test.cpp for the port as a whole (decided in the build domain).

**Depends on.** HW-5

**Owner decision.** None.

**Check here.** g++ -std=c++20 -I src tools/boot_config_test.cpp && ./a.out

**Needs the Pi.** Nothing.

## HW-40. Controls page idioms: two feedback channels, duplicated helpers, inline style, loader naming

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| mismatch | minor | S | no | fix-later | WCP-09-F10, WCP-09-F14, WCP-09-F16 |

**Where.** `src/web/WebControlPage.cpp:16718,17232,17388,17445,17687-17690,17895-17898,17936-17940,18065,18129,18243-18245,18256,18671-18673,18686@cinemate-port`

**Problem.** A save writes 'Saved. Core applies it now.' inline and also toasts. showControlsMessage/showHardwareMessage/showConfigIssues share one body; the test_output handler exists twice; kind names in three maps; controlsPinsTaken and controlsPinOwners compute nearly the same set. Grid columns set inline; the GPIO card called 'GPIO in' on Controls only; loadControls instead of fetchControls.

**Apertar way.** WEB-22: one toast (showToast WCP:7804-7813@upstream-1.6.0); WEB-17: fetch<X> loaders, request<Action>; column classes such as three-col (WCP:9150, CSS :755).

**Rework.**

1. Success and 'applies after the take' go into the toast; keep the issue list and pending note as status lines.
2. One showIssueBox(id, title, issues, isInfo); one requestTestOutput(peripheral); controlsKindNames everywhere; controlsPinsTaken = keys of controlsPinOwners.
3. Column classes instead of inline style; one name for the GPIO card; rename loadControls to fetchControls.

**Depends on.** HW-13

**Owner decision.** None.

**Check here.** --simulate; save shows one toast.

**Needs the Pi.** Nothing.

## HW-41. gpioChipScore half-shared

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| duplication | nit | S | yes | fix-later | HW-controls-model-F12, HW-input-classes-F8 |

**Where.** `src/hardware/GpioChipInfo.cpp:30-54@cinemate-port`; `src/hardware/GpioInput.cpp:475@cinemate-port`; `src/hardware/TriggerOutput.cpp:195@cinemate-port`; `src/hardware/RecordingIndicatorOutput.cpp:191@cinemate-port`

**Problem.** GpioInput calls hardware::gpioChipScore in GpioChipInfo.cpp; TriggerOutput and RecordingIndicatorOutput keep their own copies. The two reports proposed opposite fixes; resolved here toward the upstream rule. GpioChipInfo stays for the page's chip list (04fe197).

**Apertar way.** HW-17: each GPIO user has its own gpioChipScore (GpioInput.cpp:238, TriggerOutput.cpp:201, RecordingIndicatorOutput.cpp:198@upstream-1.6.0).

**Rework.**

1. Restore GpioInput's private gpioChipScore verbatim from upstream.
2. GpioChipInfo.cpp keeps its copy with one line: 'Same scoring as the GPIO readers, so the page shows the chip they pick.'

**Owner decision.** None.

**Check here.** git diff core-upstream -- src/hardware/GpioInput.cpp shrinks by the scoring block.

**Needs the Pi.** Nothing.

## HW-42. Listen wiring: seen callback by setter, gesture suffix arrays in three copies

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| mismatch | nit | S | no | fix-later | HW-input-classes-F7, HW-input-classes-F11 |

**Where.** `src/hardware/GpioInput.hpp:21-22@cinemate-port`; `src/hardware/Pcf8574Input.hpp:21-22@cinemate-port`; `src/hardware/NeoRotary4Input.hpp:23-24@cinemate-port`; `src/hardware/GpioInput.cpp:643-645@cinemate-port`; `src/ApertarCoreApp.cpp:8118-8120@cinemate-port`

**Problem.** setSeenCallback on three classes, called in App::start() ('// T42 Listen'). Seen-key suffixes chosen by static_cast of the gesture enum into parallel arrays, three copies (NeoRotary's differs).

**Apertar way.** CMD-18/HW-1: inputs take callbacks in the constructor (GpioInput.hpp:17; App:6785-6792@upstream-1.6.0 member-init list).

**Rework.**

1. Add a constructor parameter ActionCallback seenCallback = {} to the three classes; pass [this](const std::string &k){ noteInputSeen(k); } in App's member-init list; delete the setters.
2. One inline const char *gestureSuffix(ButtonGesture::Event) switch in ButtonGesture.hpp ('' for Press); callers add their own press suffix.

**Depends on.** HW-7

**Owner decision.** None.

**Check here.** Build; Listen highlights the right row on --simulate via test_input.

**Needs the Pi.** Nothing.

## HW-43. Store: `by` written raw into hardware-state.conf; 100 ms sleep under the store mutex

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| bug | nit | S | no | fix-later | HW-config-text-store-F15 |

**Where.** `src/hardware/HardwareConfigStore.cpp:101-114,198-209,406-414@cinemate-port`

**Problem.** writeStateLocked writes the client's by unfiltered, so by="x\nwritten_revision=h0" injects a revision line. settledLocked sleeps 100 ms under mutex_ once per outside edit, on whichever writer comes first, the IMU included.

**Apertar way.** No precedent. History names already go through safeName (Store.cpp:54-60).

**Rework.**

1. writeStateLocked: write safeName(by).
2. settledLocked: drop the sleep and the second stat; the age check (under 1 s refuses) already covers an editor mid-save.

**Owner decision.** None.

**Check here.** Scratch host check: by with a newline is stored as one line.

**Needs the Pi.** Nothing.

## Conforms to original Apertar (for the handoff)

- HardwareConfigStore writes only the editable path ($APERTAR_HARDWARE_CONFIG or /home/pi), never /boot (HW-9; upstream App:4271-4276).
- Hardware inputs still end in handleHardwareInputAction -> dispatchHardwareInputCommand -> handleCommand; test_input reuses that path instead of a new one (HW-3).
- GPIO is still raw GPIO char-dev v2 ioctls and I2C raw /dev/i2c-N ioctls; no libgpiod or wiringPi (HW-16).
- The edge-event wait has an upstream precedent (poll() on a device fd in StandbyPowerButtonInput.cpp:51-56) and keeps the poll_ms fallback.
- NeoRotary heldAtStartMask only ignores a push held at open until release, matching upstream's release guard.
- The GPIO chip setting is back on the Controls page with per-chip checks (Apertar-Core 04fe197, worktree /home/user/wt/core-work).
- The [display] defaults are the 720x720 square screen again in Core's template (Core 7dc6f7a) and the UI fallback (UI 6a59d83).
- Fan mode still uses fanModeBlock/stripManagedFanBlock unchanged and the upstream sentence 'Changing the fan mode needs sudo permission.' (App:3614-3649@cinemate-port).
- bootConfigMutex() is a function-local static mutex, the same pattern as cacheMutex (App:2269@upstream-1.6.0).
- The Boot Config engine edits config.txt in place and keeps every other byte, as upstream's fan block does, and reads the result back before writing.
- The UI fan client uses the synchronous QLocalSocket bridge shape of MediaStatusBridge (UI MediaStatusBridge.cpp:20-42@upstream-1.6.0).
- ControlsWarning.qml has the same shape as DroppedFrameWarning.qml (missing from qml.qrc is owned by the UI domain).
- Programmatic hardware-file writes keep comments and order and edit one key in place (HW-8), apart from the duplicate-section case HW-17.

## Dropped or left to another domain

- X-board-support-1: fixed by 04fe197 (chip and poll_ms rows, per-chip claims, header-only DPI/I2C checks); the remainder is HW-25.
- X-stock-behaviour-1, X-board-support-2, X-knobs-2 (display fallback): fixed by Core 7dc6f7a and UI 6a59d83 on the improvement branches; the first-run writer stays open as HW-9.
- X-protocol-security-2 part 'a LAN client saves [run_script] path1=<file>': not real at cinemate-port, the script_paths check in saveLocked (HardwareConfigStore.cpp:330-335) refuses it; becomes real if that check goes alone (merged into HW-3).
- X-protocol-security-1 fix 'refuse boot-chain keys': superseded by Boot-config-F3's drop of the text field; offered as the alternative in HW-1's owner question.
- X-knobs-13 ([camera] Clear HDR ISO caps in the hardware file): camera domain (same as CC-2-F1).
- X-knobs-12 conform_fps and directIo parts, X-knobs-16 media-trim part, X-protocol-security-9 media sudoers: media and camera domains; only the hold_ms/double_ms and boot-config parts are taken.
- HW-controls-model-F12 and HW-input-classes-F8 proposed opposite fixes; resolved in HW-41 toward HW-17 (each GPIO user keeps its own score).

## Same problem in another domain (fix once)

| Here | There |
| --- | --- |
| HW-1 | App-1-F7, WCP-10-F3 |
| HW-4 | App-1-F4, App-3-F1, WCP-10-F1 |
| HW-5 | App-1-F8, App-1-F12, Build-scripts-docs-F4 |
| HW-9 | UI-bridges-F2, App-2-F2 |
| HW-11 | App-1-F9 |
| HW-19 | Build-scripts-docs-F10 (socket line cap) |
| HW-21 | App-4-F1, App-4-F13 |
| HW-22 | App-2-F12 |
| HW-36 | Media-buffer-split-F1, CC-3-F2 (storage keys in the hardware file) |
