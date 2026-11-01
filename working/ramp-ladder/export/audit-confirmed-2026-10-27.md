### 1. [T32] blocker - kb/tutorials/inbox/20261027213000 CINEMATE APERTAR T32 speed-ramp-every-control.md @ 4.4 Check (line 224), 4.8 Check (line 406), tutor block 'check 4.8' (line 596)
PROBLEM: The settingsSpeedRamp count after 4.8 is 18, not 17. On a correctly patched tree, tutorial.py's check 4.8 reports FAIL.
VERIFIER: Confirmed. Running grep -c settingsSpeedRamp gives 18 on verify2/home/ApertarCore/src/web/WebControlPage.cpp and 18 on tip-core. It gives 0 on the T31-only tree and 0 on base b606c4f. The web patch 0001-web-speed-ramp-block-in-the-Recording-format-card.patch adds exactly 18 lines that contain settingsSpeedRamp. On the patched tree those lines break down as follows: 8 in the 4.4 HTML (2922, 2924, 2926, 2929, 2935, 2939, 2949, 2950), 9 in the 4.5 JS (5071, 5092, 5093, 5098, 5101, 5112, 5125, 5126, 5140), and 1 in the 4.8 listener (11579: document.getElementById("settingsSpeedRampTargetSelect").addEventListener...). The tutorial's own code blocks give the same split, 8 + 9 + 1 = 18, at tutorial lines 183-211, 246-330 and 401. 17 is the count after 4.5 and does not include the 4.8 listener. Wrong '17' found here: T32 tutorial line 224 ('→ 8 after this step (17 after 4.8)'), line 406 ('→ 17.') and the tutor block at line 596 ('^17$'). On a correctly patched Pi, tutorial.py check 4.8 would report FAIL. The same wrong value is also in kb/working/handoff-speed-ramp.md:52 ('# T32 WebUI block: 17'), which the original finding missed. The export's copy and verify3's copy of the tutorial are byte-identical.
FIX (verified): In kb/tutorials/inbox/20261027213000 CINEMATE APERTAR T32 speed-ramp-every-control.md (both the export and verify3 copies): line 224, change '→ 8 after this step (17 after 4.8).' to '→ 8 after this step (18 after 4.8).'. Line 406, change '→ 17.' to '→ 18.'. Line 596, change 'check 4.8 | grep -c 'settingsSpeedRamp' /home/pi/ApertarCore/src/web/WebControlPage.cpp | ^17$' to '... | ^18$'. Also, in kb/working/handoff-speed-ramp.md line 52, change '# T32 WebUI block: 17' to '# T32 WebUI block: 18'.

### 2. [T32] wrong - kb/tutorials/inbox/20261027213000 CINEMATE APERTAR T32 speed-ramp-every-control.md @ tutor block, 'check 5.1' (line 598)
PROBLEM: tutorial.py never loads this check. tutor_block() splits on ' | ' and keeps only lines with exactly 3 fields. The command's own pipe makes 4 fields, so the line is silently dropped.
VERIFIER: I confirmed the finding myself. In the T32 note (verify3/tutorials/inbox/20261027213000 CINEMATE APERTAR T32 speed-ramp-every-control.md), line 598 reads `check 5.1 | curl -s -m 3 http://127.0.0.1:8000/api/state | grep -o '"fps":[0-9.]*' | "fps":`. The tutor_block() function in verify3/tutorials/tutorial.py:121-123 splits a check line on " | " and keeps it only when `len(fields) == 3`. This line has 4 fields, so the parser drops it without any warning. I loaded tutorial.py and ran tutor_block() on the note. It returns 9 checks: ['3.1','4.1','4.2','4.3','4.5','4.6','4.7','4.8','4.9']. There is no 5.1, so `tutorial.py check T32 5.1` would stop with "No check for step 5.1". The second point also holds. The expected regex `"fps":` matches any value, so the check would pass at 30 and could not catch a missing cap.

The proposed replacement works. /api/state comes from ApertarCoreApp::buildWebStateJson() (verify2/home/ApertarCore/src/ApertarCoreApp.cpp:7805). Inside that function there is only one `"fps":` key, at line 7966: `<< ",\"fps\":" << jsonNumber(settings.fps, 3)`. jsonNumber (line 299) uses std::fixed with setprecision(3), so the output is `"fps":25.000`. The other fps keys are fps_ramp, fps_take_base and similar, and they cannot match `"fps":`. The new line has 3 fields. unsafe_reason() lets it through: curl is in SAFE_FIRST, it sends no Core command, and it does not touch /api/config. cmd_check (tutorial.py:289-292) takes the key `fps` from the expect regex and prints `a
FIX (verified): In kb/tutorials/inbox/20261027213000 CINEMATE APERTAR T32 speed-ramp-every-control.md, line 598 (tutor block), replace
`check 5.1 | curl -s -m 3 http://127.0.0.1:8000/api/state | grep -o '"fps":[0-9.]*' | "fps":`
with
`check 5.1 | curl -s -m 3 http://127.0.0.1:8000/api/state | "fps":25\.000`
After that, tutor_block() returns 10 checks, including 5.1. The check passes only when Core keeps 25 after `set_fps value=30`, and tutorial.py prints the actual `"fps":` value.
Optional matching prose fix at line 477: change "What you see: `\"fps\":25`." to "What you see: `\"fps\":25.000`." (get_state's settingsBody prints fps with 3 decimals).

### 3. [T32] wrong - kb/tutorials/inbox/20261027213000 CINEMATE APERTAR T32 speed-ramp-every-control.md @ §6 Commit, lines 521-524
PROBLEM: `git add <file>` stages the whole WebControlPage.cpp, so the first commit takes in all of 4.4-4.8. The comment says to use `git add -p`, but the command does not. Pasted as written, the second `git add` + `git commit` has nothing to commit and fails, and the two Core commits do not match the two patches.
VERIFIER: I confirmed this myself. In kb/tutorials/inbox/20261027213000 CINEMATE APERTAR T32 speed-ramp-every-control.md, §6 has the first Core add at line 521 and the second at line 523. Line 521 is `git -C ~/ApertarCore add src/camera/CameraController.cpp src/web/WebControlPage.cpp   # only the 4.1 and 4.2 hunks: git add -p`. Line 523 is `git -C ~/ApertarCore add src/web/WebControlPage.cpp`. A plain `git add <path>` stages every change in the file. Both T32 Core patches change WebControlPage.cpp. The cap patch (0001-camera-cap-4K-Clear-HDR-16-bit-at-25-fps.patch) has one hunk at `@@ -4974,8 +4974,9 @@`, which is 4.2. The web patch (0001-web-speed-ramp-block-in-the-Recording-format-card.patch) has seven hunks, at 2916, 4203, 5021, 8706, 8740, 9998 and 11426. If you paste the block as written, the first commit takes 4.1, 4.2 and all of 4.4-4.8. The second `add` then has nothing to stage, so the second `git commit` stops with "nothing to commit, working tree clean" (exit 1). The two Core commits then do not match the two patches. I also checked that the proposed `add -p` fix works. diff -u between verify2/t31home/ApertarCore/src/web/WebControlPage.cpp and verify2/home/ApertarCore/src/web/WebControlPage.cpp gives 8 separate hunks: -2916, -4203, -4974, -5020, -8705, -8739, -9997 and -11425. The 4.2 hunk (-4974,8 +5008,9) is not merged with the 4.5 hunk at -5020, so `git add -p` offers it on its own as the 3rd of 8 and no split is needed. In verify2/home, the reference commits 8cbb718 (cap
FIX (verified): In §6, replace line 521 with these two lines:
`git -C ~/ApertarCore add src/camera/CameraController.cpp                          # the 4.1 cap`
`git -C ~/ApertarCore add -p src/web/WebControlPage.cpp                            # y only on the maximumSupportedFpsForSnapshot hunk (4.2, the 3rd of 8), n on the other seven`
Keep lines 522-524 as they are. After that, line 523 (`add src/web/WebControlPage.cpp`) stages the rest of the WebControlPage changes (4.4-4.8) for the second commit.

### 4. [T32] wrong - kb/tutorials/inbox/20261027213000 CINEMATE APERTAR T32 speed-ramp-every-control.md @ 3.2, the WebUI and touch UI greps (lines 116-117)
PROBLEM: Both greps hit an IMX477 line first. `| head -4` then cuts off the IMX585 line that the answer talks about. The reader sees 16.39 and never sees 30.0.
VERIFIER: The finding is real: I ran both greps myself and could not refute it. In "20261027213000 CINEMATE APERTAR T32 speed-ramp-every-control.md", section 3.2, line 116 is the WebUI grep and line 117 is the touch UI grep. Both hit an IMX477 line first, so `| head -N` cuts off the IMX585 `30.0` line that the Answer quotes.
- WebUI, on the T31 tree (verify2/t31home/ApertarCore/src/web/WebControlPage.cpp): `grep -n -A2 ... | head -4` prints only 4942 `|| (width === 3856 && height === 2180) || (width === 3840 && height === 2160))`, 4943 `return 16.39;`, 4944 `if (width === 4056 && height === 3040)` and `--`. The IMX585 match at 4977 `if ((width === 3856 && height === 2180) || (width === 3840 && height === 2160))` / 4978 `return 30.0;` is cut off.
- Touch UI, on dc471c1:qml/CameraPage.qml (T31 changes no .qml file, so dc471c1 is what the Pi has): `grep -n -A1 ... | head -4` prints 746 `if (resolutionValue === "4056x2160" || resolutionValue === "3856x2180" || ...`, 747 `return 16.39`, `--`, 780 `if (resolutionValue === "3856x2180" || resolutionValue === "3840x2160")`. Line 781 `imx585Max = 30.0` is cut off.
- Result: the reader sees 16.39 and never sees the 30.0 the Answer talks about.
- The proposed fix works. I ran it:
  - The new WebUI pattern matches only 4977/4978 `return 30.0;`, both on T31 and on b606c4f.
  - The new touch UI pattern matches 780, 1294, 1306 and 1349 but not 746, because 746 has `"4056x2160"` right after `if (`. With `| head -2` it prints only 780 and 781 `imx585Max
FIX (verified): In kb/tutorials/inbox/"20261027213000 CINEMATE APERTAR T32 speed-ramp-every-control.md", section 3.2 code block:

1. Replace line 116 with:
grep -n -A1 'if ((width === 3856 && height === 2180) || (width === 3840 && height === 2160))' ~/ApertarCore/src/web/WebControlPage.cpp   # WebUI
It prints only 4977 `if ((width === 3856 ...` and 4978 `return 30.0;` on T31.

2. Replace line 117 with:
grep -n -A1 'if (resolutionValue === "3856x2180" || resolutionValue === "3840x2160")' ~/ApertarUI/qml/CameraPage.qml | head -2   # touch UI
It prints 780 `if (resolutionValue === "3856x2180" || resolutionValue === "3840x2160")` and 781 `imx585Max = 30.0` on dc471c1.

The Answer text ("WebUI and touch UI: `30.0`, with no Clear HDR or bit-depth test at all") can stay as written. Optionally, give the locations in the Answer: WebControlPage.cpp `:4977-4978@T31` and CameraPage.qml `:780-781@dc471c1`.

### 5. [T32] wrong - kb/tutorials/inbox/20261027213000 CINEMATE APERTAR T32 speed-ramp-every-control.md @ §1, second bullet (line 39): `ApertarCoreApp.cpp:8623-8630@T31`, `:8812-8816@T31`
PROBLEM: These are b606c4f (base) line numbers, not T31 ones. At @T31, 8623-8630 is the ISO pot handler and 8812-8816 is the EV handler. fps_up is not in either range.
VERIFIER: Confirmed. Line 39 of "kb/tutorials/inbox/20261027213000 CINEMATE APERTAR T32 speed-ramp-every-control.md" (identical in the export and in verify3) cites `ApertarCoreApp.cpp:8623-8630@T31` and `:8812-8816@T31`. These are b606c4f numbers with the wrong tag. The T31 tutorial cites the same ranges, correctly tagged `@b606c4f`, at line 80 (`App:8623-8630@b606c4f`, `:8812-8816@b606c4f`). The T32 text appears to have copied them and relabelled them @T31. On verify2/t31home/ApertarCore/src/ApertarCoreApp.cpp:
- 8623-8630 is the tail of the ISO pot branch (8623 `const uint32_t iso = ...`, 8626 `dispatch("set_iso", ...)`, 8628 `}`), plus a blank line and only the opening line 8630 `if (target == "fps") {`.
- 8812-8816 is the EV handler (8814 `parseHardwareActionNumber(action, {"evm", "ev"})`, 8815 `dispatch("set_exposure_compensation", ...)`). No fps code is in it.
The real T31 locations:
- PCF pot: 8630 `if (target == "fps") {` through 8638 `}`.
- `fps:<n>`: 8819 `if (const auto fps = parseHardwareActionNumber(action, { "fps" })) {` through 8824 `}`.
- `fps_up` / `fps_down` / `fps`: 8891 `if (const auto mode = pcfSettingStepMode(action, "fps")) {` through 8897 `}`. pcfSettingStepMode at 1054 maps `fps_up` to Up and `fps_down` to Down.
The sentence names `fps_up` buttons, but neither old range covers 8891-8897, even on base, so a third reference is needed. The reviewer's proposed fix is correct as given.
FIX (verified): In "kb/tutorials/inbox/20261027213000 CINEMATE APERTAR T32 speed-ramp-every-control.md" line 39, replace
`(`ApertarCoreApp.cpp:8623-8630@T31`, `:8812-8816@T31`)`
with
`(`ApertarCoreApp.cpp:8630-8638@T31` PCF pot, `:8819-8824@T31` `fps:<n>`, `:8891-8897@T31` `fps` / `fps_up` / `fps_down`)`.
Apply the same edit to the export copy in apertar-kb-speed-ramp-2026-10-27/kb/tutorials/inbox/ and to the verify3 copy.

### 6. [T32] wrong - kb/tutorials/inbox/20261027213000 CINEMATE APERTAR T32 speed-ramp-every-control.md @ 4.7 (lines 363 and 373)
PROBLEM: Two wrong sub-ranges. The recording_elapsed_seconds lines are not at 8843-8846, and `case "set_fps":` is not at 8880-8892.
VERIFIER: Confirmed, and the reviewer's numbers are right. The tutorial says its line numbers refer to the patched trees unless a reference is marked @T31 (header, lines 15-16). Section 4.7 follows that rule for its other anchors: `mergeCameraStateFields` is at :8761 and `applyCommandSnapshotPatch` is at :8848, and both match /tmp/claude-0/-home-user-apertar-kb/17fc979d-f346-53ac-97ad-c8caa225a57d/scratchpad/verify2/home/ApertarCore/src/web/WebControlPage.cpp. The two sub-ranges in 4.7 are wrong on that tree. In the patched file, 8840 is `if (isFiniteNumber(source.recording_elapsed_seconds))` and 8841 is `snapshot.recording_elapsed_seconds = Number(source.recording_elapsed_seconds);`. Lines 8842-8845 are the new fps_ramp/fps_ramp_keep_exposure lines and 8846 is the closing `}`, so `:8843-8846` covers none of the recording_elapsed_seconds lines. `case "set_fps":` runs from 8876 to 8879 (case, if, assign, break). 8880 is `case "set_fps_ramp":`, the new cases end at 8890 with `break;`, and 8891-8892 are `case "set_shutter_us":`. So `:8880-8892` is neither the set_fps case nor exactly the new cases. The tip tree gives the same anchors: tip-core has the recording_elapsed_seconds `if` at 8840 and `case "set_fps":` at 8876. On the T31-only tree the old lines are at 8706-8707@T31 and 8738-8741@T31. They are not needed, because the tutorial's rule is the patched tree.
FIX (verified): In kb/tutorials/inbox/20261027213000 CINEMATE APERTAR T32 speed-ramp-every-control.md:
Line 363: replace "after the `recording_elapsed_seconds` lines (`:8843-8846`)" with "after the `recording_elapsed_seconds` lines (`:8840-8841`; the new lines land at `:8842-8845`)".
Line 373: replace "after `case \"set_fps\":` (`:8880-8892`)" with "after `case \"set_fps\":` (`:8876-8879`; the new cases land at `:8880-8890`)".

### 7. [T32] wrong - kb/tutorials/inbox/20261027213000 CINEMATE APERTAR T32 speed-ramp-every-control.md @ 5.4 (lines 507-510)
PROBLEM: Grepping the journal for `set_shutter_us` cannot work, because neither Core nor the UI logs received commands. 'No set_shutter_us from the UI' therefore shows up with or without 4.9, and the step proves nothing.
VERIFIER: The finding is real. The tutorial's check in 5.4 looks for a log line that Core never writes, so it passes whether or not the 4.9 fix is in place.

Where: kb/tutorials/inbox/20261027213000 CINEMATE APERTAR T32 speed-ramp-every-control.md, line 507 (the grep) and line 510 ("no `set_shutter_us` from the UI during the take").

Evidence, checked on verify2/home/ApertarCore (T31 + T32) and on tip-core:
- No command is logged on the Core side. handleRequest (ApertarCoreApp.cpp:7148) and handleCommand (:9475) print nothing for a command they receive.
- The set_shutter_us handler (:9701-9707) only returns okReply or errorReply. CameraController::setShutterUs (CameraController.cpp:9203-9233) prints nothing.
- In src/ipc/ControlServer.cpp, std::cerr is used only for socket, bind, listen, accept and client-handler errors (:107-221).
- A grep for any cerr or cout line that names a command finds only "media: tuning helper failed" (:9469).
- The only ramp lines in the journal are CameraController.cpp:8399, 8426, 8436, 9149, 9175 and 9178. None contain "set_shutter_us".
- The UI does not log commands either. ApertarControlBridge::sendCoreCommand (Apertar-UI src/ApertarControlBridge.cpp:1033) writes nothing to the log, and the UI runs under its own unit, not `-u apertar-core`.
- So "no set_shutter_us" is true with or without 4.9.

What the step should check instead is the shutter value Core holds:
- With 4.9, applyFps returns after set_fps when m_recording && m_fpsRamp (UI :269-282). Core's 
FIX (verified): In kb/tutorials/inbox/20261027213000 CINEMATE APERTAR T32 speed-ramp-every-control.md, §5.4:

1) Lines 503-504: replace "Record, pick 50 on the touch UI\nFPS picker, then 25, then stop." with
"Record and pick 50 on the touch UI FPS picker. While the take is at 50:

```bash
python3 -I ~/apertar-kb/working/tools/core.py get_state | grep -o '"shutter_us":[0-9]*'   # 20000 with 4.9; 10000 if the UI still sends its own set_shutter_us
```

Then pick 25 and stop."

2) Line 507: replace
`journalctl -u apertar-core -b --no-pager | grep -E 'fps ramp: 25 -> 50|fps ramp: 50 -> 25|set_shutter_us' | tail -4`
with
`journalctl -u apertar-core -b --no-pager | grep -E 'fps ramp: (25 -> 50|50 -> 25) ' | tail -2   # two request lines, policy=exposure`

3) Line 510: replace "What you see: two `fps ramp:` request lines and no `set_shutter_us` from the UI during the take. The shutter readout stays at" with "What you see: two `fps ramp:` request lines with `shutter_us=20000 policy=exposure`, and `get_state` at 50 gives `\"shutter_us\":20000`. Neither Core nor the UI logs the commands it receives, so the journal cannot show a missing `set_shutter_us`; the shutter value can. The shutter readout stays at" (the rest of the paragraph stays as it is).

### 8. [T32] wrong - kb/tutorials/inbox/20261027213000 CINEMATE APERTAR T32 speed-ramp-every-control.md @ §7, first row (line 537)
PROBLEM: The row points to the wrong step. `node --check` is in 4.10, not 4.9 (4.9 is the touch UI bridge change).
VERIFIER: I tried to refute this and could not. The finding is correct. In kb/tutorials/inbox/20261027213000 CINEMATE APERTAR T32 speed-ramp-every-control.md, line 537 (in §7) reads: '| WebUI blank, console says `Unexpected token` | a JS typo in 4.5-4.8 | run the 4.9 `node --check`; it names the line in `/tmp/page.js` |'. But step 4.9 is a different step. Line 408 starts it with '**4.9 Touch UI: the picker leaves the shutter to Core in a ramp take** (Apertar-UI)', and it has no node --check. The node --check is in step 4.10. Line 442 starts it with '**4.10 Host checks before the Pi build**', and line 449 holds 'node --check /tmp/page.js && echo js ok'. The export copy and the verify3 copy are the same at line 537 (verify3/tutorials/inbox/...:537). So a reader who follows the §7 row goes to the wrong step.
FIX (verified): In kb/tutorials/inbox/20261027213000 CINEMATE APERTAR T32 speed-ramp-every-control.md line 537, replace 'run the 4.9 `node --check`; it names the line in `/tmp/page.js`' with 'run the 4.10 `node --check`; it names the line in `/tmp/page.js`'. Make the same change in the export (apertar-kb-speed-ramp-2026-10-27/kb/tutorials/inbox/) and in the verify3 copy.

### 9. [T32] wrong - kb/tutorials/inbox/20261027213000 CINEMATE APERTAR T32 speed-ramp-every-control.md @ 'You will learn' (line 25) and §8 (line 555): 'three places' / 'One ceiling, three copies'
PROBLEM: Core has a fourth copy of the 4K ceiling, used by the PCF pot and the fps/fps_up/fps_down buttons. T32 does not change it, so in Clear HDR 16-bit these controls still offer 30, and Core clamps it to 25.
VERIFIER: Confirmed in the code. Core has a fourth copy of the IMX585 4K ceiling, and it has no Clear HDR or bit-depth test. In /tmp/claude-0/-home-user-apertar-kb/17fc979d-f346-53ac-97ad-c8caa225a57d/scratchpad/verify2/home/ApertarCore/src/ApertarCoreApp.cpp:1162-1165, `maximumPcfFpsForSettings` reads `if (sensor.find("imx585") != std::string::npos) { if ((width == 3856 && height == 2180) || (width == 3840 && height == 2160)) return 30.0;`. The function (:1100) looks only at the sensor and the resolution. `availablePcfFpsOptions` (:1174-1192) drops presets from {24, 25, 30, 50, 60} that are above that value, so in 4K it gives {24, 25, 30}. Two places use that list: the PCF pot (:8631, `if (target == "fps")`) and fps_up/fps_down (:8892-8895, `pcfSettingStepMode(action, "fps")`). The `fps:<n>` button (:8811-8816) does not use the list. It sends whatever value it is given, so the evidence's 'fps/fps_up/fps_down' is slightly off. These lines are identical on the T31-only tree (diff of lines 1100-1192 shows no change), and none of the patches touch `maximumPcfFpsForSettings`. T32 leaves this copy at 30. What happens in Clear HDR 16-bit at 25: fps_up picks nearest index 1, then index 2, and sends `set_fps 30`. The sanitiser clamps that to 25, so fps_up does nothing. The pot's top third also asks for 30 and gets 25. Nothing breaks, but four tutorial passages contradict the code: line 25 says 'three places: Core, WebUI, touch UI'; line 45 says 'All three layers still offer 30' and its table (
FIX (verified): Edit kb/tutorials/inbox/20261027213000 CINEMATE APERTAR T32 speed-ramp-every-control.md:
(1) Line 25: change it to 'Where the FPS ceiling of a mode lives (four places: Core's sanitiser, Core's PCF list, WebUI, touch UI) and why they must agree.'
(2) Line 45: change 'All three layers still offer 30:' to 'All four still offer 30. T32 changes three of them:'. After line 51, add this table row: '| PCF pot, fps_up/fps_down | `ApertarCoreApp.cpp:1162-1165@T31`, `maximumPcfFpsForSettings` (cuts `availablePcfFpsOptions`, `:1174-1192`) | 30, left as is: Core clamps it to 25 |'. Under the table, add one sentence: 'T32 leaves the PCF list alone. In Clear HDR 16-bit at 25, fps_up asks for 30 and Core keeps 25, and the pot's top third gives 25.'
(3) §5.1, lines 477-478: change 'The WebUI FPS pills end at 25, and so does the touch UI picker. ... 30 comes back in all three.' so it names the WebUI pills and the touch UI picker, then says 'comes back in both; the PCF list offers 30 in every case and Core clamps it.'
(4) Line 555: change it to 'One ceiling, four copies. Core is the authority, because its sanitiser clamps whatever arrives. The two UIs and Core's PCF list (`maximumPcfFpsForSettings`) only decide what they offer.'
Instead of (2)-(4), the patch could get a 16-bit test in `maximumPcfFpsForSettings`. That needs `settings.clearHdr` and the raw bit depth from `CaptureSettings`, and it changes the patch and the check counts. The text-only fix is the smaller change.

### 10. [T32] minor - kb/tutorials/inbox/20261027213000 CINEMATE APERTAR T32 speed-ramp-every-control.md @ 5.1, 'What you see' (line 477)
PROBLEM: The grep output is `"fps":25.000`, not `"fps":25`, because Core prints fps with 3 decimals.
VERIFIER: The finding is correct; I could not refute it. On the T32 tree (verify2/home/ApertarCore) the get_state handler (src/ApertarCoreApp.cpp:9628-9656) appends settingsBody(camera_.settings()) at :9655. settingsBody writes fps at :185 as `<< ",\"fps\":" << std::fixed << std::setprecision(3) << settings.fps`, so a value of 25 comes out as 25.000. It is the only `"fps":` key in the get_state reply; fps_phase_lock, fps_ramp and similar keys do not match the grep pattern `"fps":[0-9.]*`. working/tools/core.py prints the raw reply line with `print(buf.split(b'\n')[0].decode())`, and `grep -o '"fps":[0-9.]*'` keeps the whole number. The command at tutorial line 474 therefore prints `"fps":25.000`, not the `"fps":25` that line 477 says. The /api/state path (:7966, jsonNumber(settings.fps, 3)) also gives 25.000. The tip tree is the same (tip-core :185 and :8018). The check at line 598 (expected `"fps":`) still passes, so only the 'What you see' text is wrong.
FIX (verified): In kb/tutorials/inbox/20261027213000 CINEMATE APERTAR T32 speed-ramp-every-control.md, line 477: change 'What you see: `"fps":25`.' to 'What you see: `"fps":25.000`.' Optionally also change the comment on line 474 from '# Core keeps 25' to '# Core keeps 25.000'.

### 11. [T32] minor - kb/tutorials/inbox/20261027213000 CINEMATE APERTAR T32 speed-ramp-every-control.md @ §8, 'Next:' bullet (line 560)
PROBLEM: The tutorial numbering does not match the export. The KB makes T33 the value lists and build max_fps, and T34 the mode ladder.
VERIFIER: The finding is real. The T32 tutorial, at kb/tutorials/inbox/20261027213000 CINEMATE APERTAR T32 speed-ramp-every-control.md:560 (the same line in verify3/tutorials/inbox/...:560), says "- Next: the mode ladder (T33). Clear HDR 16-bit up to 25, then 4K SDR 12-bit up to a maximum of 50 set in the settings." Every other file in the export numbers these the other way round:
- INSTALL.md:27-28 has "T33, the editable value lists (ISO, shutter angle, FPS, WB) and the build's `max_fps=50`" and "T34, the mode ladder with drag and drop...".
- HANDOFF-PROMPT.md:11-12 has "2: T33, the value lists and `max_fps=50`" and "3: T34, the mode ladder".
- kb/working/handoff-speed-ramp.md:1, :15-16, :68 and :79 call T33 the value lists plus build `max_fps` and T34 the mode ladder.
- kb/working/ramp-ladder/README.md has "### 3.1 T33: value lists" at :42 and "### 3.2 T34: the mode ladder" at :89. Its rung table says the 50 ceiling comes from "`max_fps=50` (§3.1)", which is T33. It is a build setting (`[camera] max_fps=50` in apertar-hardware.conf, handoff :73), not "the settings".

T32 is the only file that calls the ladder T33. No other tutorial line mentions T33 or T34. The reviewer's proposed fix gets the numbering right, but its second sentence ends in "set in the settings (T33)", which reads as if the ladder were part of T33 again and keeps the vague word "settings". The fix below is cleaner.
FIX (verified): In kb/tutorials/inbox/20261027213000 CINEMATE APERTAR T32 speed-ramp-every-control.md, lines 560-562, replace

- Next: the mode ladder (T33). Clear HDR 16-bit up to 25, then 4K SDR 12-bit up to a maximum of 50 set in the settings. Its
  rows go into this same block. Cinemate's equivalents are the Dynamic Resolution card and the per-mode FPS ceiling overrides
  (`settings_editor.html:2038-2045`, `:3835-3850`).

with

- Next: the editable value lists and the build's maximum, `max_fps=50` (T33), then the mode ladder (T34): 4K Clear HDR 16-bit
  up to 25, then 4K SDR 12-bit up to that maximum of 50. The ladder's rows go into this same block. Cinemate's equivalents are
  the Dynamic Resolution card and the per-mode FPS ceiling overrides (`settings_editor.html:2038-2045`, `:3835-3850`).

Make the same change in verify3/tutorials/inbox/ (same file name, same line 560) so the overlay matches the export.

### 12. [T32] minor - kb/tutorials/inbox/20261027213000 CINEMATE APERTAR T32 speed-ramp-every-control.md @ §7, row 'Build error `unterminated raw string`' (line 538)
PROBLEM: The symptom and the cause do not match. Typing `)APERTAR"` into the page closes the string early, and g++ then reports `missing terminating " character` at the real closer. 'unterminated raw string' is what you get when the closing `)APERTAR"` is missing or broken.
VERIFIER: I tried to refute the finding and could not; I reproduced it on the real file. The row is at kb/tutorials/inbox/"20261027213000 CINEMATE APERTAR T32 speed-ramp-every-control.md":538, and the same file in verify3 also has it at line 538. It reads: "| Build error `unterminated raw string` | `)APERTAR"` was typed into the page | the page must not contain that sequence; remove it |".

The page starts at WebControlPage.cpp:7 (`R"APERTAR(<!DOCTYPE html>`) and ends at 11805 (`)APERTAR";`), in verify2/home/ApertarCore/src/web/. The unmodified file passes `g++ -std=c++20 -fsyntax-only`. All test copies are in scratchpad/audit-notes/rawstr/.

(A) I typed `// )APERTAR" oops` inside the JS at renderSpeedRamp (line 5080). Result: 340 errors, first `5658:57: stray '\' in program`, mostly `'function' does not name a type` (208). It also gave `11806:9: error: missing terminating " character` at the real closer.
(B) I typed `<p>x )APERTAR" y</p>` into the HTML at line 300. Result: 997 errors, first `316:19: stray '#' in program`. It also gave `11806:9: missing terminating " character`.
Neither case reports `unterminated raw string`.
(C) I changed the closer to `)APERTA";` and (D) I deleted the closer line. Both give `7:32: error: unterminated raw string` plus 3 follow-on errors.

So `unterminated raw string` means the closing `)APERTAR";` is missing or damaged, not that `)APERTAR"` was typed into the page. The proposed fix is basically right. The one correction: in the typed-in case, `missing
FIX (verified): At kb/tutorials/inbox/"20261027213000 CINEMATE APERTAR T32 speed-ramp-every-control.md":538, replace the one row with two rows:
| Build fails with hundreds of errors (`stray '#' in program`, `stray '\' in program`, `'function' does not name a type`) and `missing terminating " character` on the `)APERTAR";` line | `)APERTAR"` was typed into the page, so the raw string closes early | the page must not contain that sequence; remove it |
| Build error `unterminated raw string` at `R"APERTAR(` (line 7) | the closing `)APERTAR";` at the end of the page was deleted or changed | put `)APERTAR";` back as the page's last line |

### 13. [T32] minor - kb/tutorials/inbox/20261027213000 CINEMATE APERTAR T32 speed-ramp-every-control.md @ §7, row '`FPS ramping works in cDNG and MLV takes only.` toast' (line 542)
PROBLEM: The row names the wrong source. In an H.264/ProRes take the block's Ramp, ×2 and Back are already greyed out (canRamp is false). With Over > 0, a ramp_fps refusal goes to the journal, not to a toast. The toast comes from the main FPS pills, which are never greyed out and send set_fps.
VERIFIER: I confirmed the finding against the T32 Core tree at /tmp/claude-0/-home-user-apertar-kb/17fc979d-f346-53ac-97ad-c8caa225a57d/scratchpad/verify2/home/ApertarCore. Tutorial line 542 reads: "| `FPS ramping works in cDNG and MLV takes only.` toast | ramp pressed during an H.264/ProRes take | expected; the buttons should be grey, so check `speedRampFormatSupported` |". The code does not support that row.

(1) The block cannot be pressed in an H.264/ProRes take. In src/web/WebControlPage.cpp:5084 `formatSupported = speedRampFormatSupported(snapshot)` (lines 5061-5063) is true only for cdng, lossydng and mlv. Line 5089 has `canRamp = !stepping && (!recording || (enabled && formatSupported))`, so it is false in a processed-format take. Lines 5141-5143 set Ramp, ×2 and Back to `enabled: canRamp && ...`. Line 5132 sets `targetSelect.disabled = !canRamp`. In buildOptionButtons (9328-9343) a disabled button does nothing when clicked.

(2) Even if the block were enabled, Over > 0 gives no toast. ramp_fps (src/ApertarCoreApp.cpp:9894-9902) calls startFpsRamp. With seconds > 0 that function starts the stepper thread and returns true. A refused step only goes to stderr: src/ApertarCoreApp.cpp:9270 `std::cerr << "ApertarCore fps ramp stopped: " << camera_.lastError()`. Only Over = Cut (seconds 0) calls camera_.setFps directly and sends the error back as a toast.

(3) The real source of the toast is the main FPS pills. WebControlPage.cpp:10059-10063 `buildOptionButtons("fpsOptions", fpsOption
FIX (verified): In kb/tutorials/inbox/20261027213000 CINEMATE APERTAR T32 speed-ramp-every-control.md line 542 (§7), replace the row
| `FPS ramping works in cDNG and MLV takes only.` toast | ramp pressed during an H.264/ProRes take | expected; the buttons should be grey, so check `speedRampFormatSupported` |
with
| `FPS ramping works in cDNG and MLV takes only.` toast | an FPS pill pressed during an H.264/ProRes take with ramping on (the pills send `set_fps` and are never grey) | expected: ramping works only in cDNG/MLV; stop the take to change FPS. The block's Ramp, ×2 and Back are grey in such a take; if one was not, check `speedRampFormatSupported` |
Make the same change in the copy at /tmp/claude-0/-home-user-apertar-kb/17fc979d-f346-53ac-97ad-c8caa225a57d/scratchpad/verify3/tutorials/inbox/ so both stay identical.

### 14. [T32] minor - kb/tutorials/inbox/20261027213000 CINEMATE APERTAR T32 speed-ramp-every-control.md @ 3.1 Answer (line 107): '`:2918` (the picker)'
PROBLEM: The marker is wrong. Per the header, an unmarked UI line means the patched tree, and there the picker is at 2919 (§9 also cites :2919). 2918 is the dc471c1 line, which is what the 3.1 grep shows before the change.
VERIFIER: Confirmed. The T32 header (line 16-17) says line numbers are on the patched trees unless marked `@T31` or `@dc471c1`. In 3.1 Answer (kb/tutorials/inbox/20261027213000 CINEMATE APERTAR T32 speed-ramp-every-control.md:107), `:2918` (the picker) has no marker. On the patched UI tree, `grep -n fpsOptions` gives verify2/home/ApertarUI/qml/CameraPage.qml:2919 `options: root.fpsOptions`. On dc471c1, `git show dc471c1:qml/CameraPage.qml | grep -n fpsOptions` gives 2918 with the same text. So unmarked 2918 is wrong under the header rule. §9 Sources (line 571) also cites `:2919` for the patched tree. The other refs in the same sentence are fine: `:503` and `:663-665` are the same lines in both trees, and `:808-812@dc471c1` is already marked correctly (on the patched tree they are 809-813). Section 3 says "Run these before the change", so the reader's grep prints 2918. The right fix is the marked base line, not 2919.
FIX (verified): In kb/tutorials/inbox/20261027213000 CINEMATE APERTAR T32 speed-ramp-every-control.md line 107, change "and `:2918` (the" to "and `:2918@dc471c1` (the". Leave `:503`, `:663-665` and `:808-812@dc471c1` as they are.

### 15. [T32] minor - kb/tutorials/inbox/20261027213000 CINEMATE APERTAR T32 speed-ramp-every-control.md @ tutor block (lines 577-599)
PROBLEM: Two KB-rule gaps (tutorials/README.md: one `ref` per path:line the note asks him to edit, and each step's **Check:** as a `check`). There are no refs for the edit locations in 4.7 (mergeCameraStateFields), 4.8 and 4.9 (hpp:318, applyCoreState :1368). Step 4.4 has a **Check:** but no `check 4.4`.
VERIFIER: Confirmed on the files. The rules: tutorials/README.md:82 says `ref` is "One per `path:line` the note asks him to read or edit", and :83 says `check` is "The step's **Check:**". llm/tutoring.md step 9 also says "a `ref` per code location, a `check` per **Check:**". The T32 tutor block (note lines 577-599) has 11 refs. None of them covers these edit locations that the steps name:
- 4.7: mergeCameraStateFields insert. On the final tree verify2/home/ApertarCore/src/web/WebControlPage.cpp:8842 is `if (typeof source.fps_ramp === "boolean")`.
- 4.8: state fields at :4238 `speedRampTarget: "",` and the listener at :11579 `document.getElementById("settingsSpeedRampTargetSelect").addEventListener(...)`.
- 4.9: verify2/home/ApertarUI/src/ApertarControlBridge.hpp:318 is `bool m_fpsRamp = false; // Core's fps_ramp ...`, and ApertarControlBridge.cpp:1368 is `if (state.contains(QStringLiteral("fps_ramp")))`.

Step 4.4 has a **Check:** (note line 224), but the block has no `check 4.4` (the checks are 3.1, 4.1-4.3, 4.5-4.9 and 5.1).

All five proposed anchors pass `grep -nF` exactly once, at the stated lines, on the T32 tree. `grep -c 'id="settingsSpeedRamp'` gives 0 on the T31 tree (so the check fails before the change, as tutoring.md step 10 wants) and 8 on the final tree. It stays 8 because only the HTML has `id="settingsSpeedRamp`.

The reviewer's fix is correct but leaves one problem next to it. The count it builds on is wrong. `grep -c 'settingsSpeedRamp'` gives 18 on the final tree, n
FIX (verified): In the tutor block of kb/tutorials/inbox/20261027213000 CINEMATE APERTAR T32 speed-ramp-every-control.md, add these ref lines:
ref core src/web/WebControlPage.cpp 8842 if (typeof source.fps_ramp === "boolean")
ref core src/web/WebControlPage.cpp 4238 speedRampTarget: "",
ref core src/web/WebControlPage.cpp 11579 document.getElementById("settingsSpeedRampTargetSelect").addEventListener
ref ui src/ApertarControlBridge.hpp 318 bool m_fpsRamp = false;
ref ui src/ApertarControlBridge.cpp 1368 if (state.contains(QStringLiteral("fps_ramp")))

Add this check line:
check 4.4 | grep -c 'id="settingsSpeedRamp' /home/pi/ApertarCore/src/web/WebControlPage.cpp | ^8$

Change the step 4.4 **Check:** text (line 224) to the same grep so the note and the block agree: **Check:** `grep -c 'id="settingsSpeedRamp' src/web/WebControlPage.cpp` → 8 (only the HTML has ids; it stays 8 after 4.5-4.8).

Also fix the wrong count. Line 596: `check 4.8 | grep -c 'settingsSpeedRamp' /home/pi/ApertarCore/src/web/WebControlPage.cpp | ^18$` (not ^17$). Line 406: "→ 18." (not 17). If line 224 keeps its old grep, it must say "(18 after 4.8)".

### 16. [T32] minor - kb/tutorials/inbox/20261027213000 CINEMATE APERTAR T32 speed-ramp-every-control.md @ §6, 'messages as in the two patches' (line 518)
PROBLEM: README §6 asks for the full commit message in house format; T31 gives it inline, T32 does not. The message it points to for the 4.3 UI commit also carries a stale Tested line, while the tutorial header says the whole UI was built with Qt 6.4.2.
VERIFIER: I tried to refute this and could not. Both halves hold.

(1) Missing commit messages. The KB README (verify3/tutorials/README.md:49) says row 6 must give "the full commit message in house format". T32 §6 (lines 516-529 of the export's "20261027213000 CINEMATE APERTAR T32 speed-ramp-every-control.md") does not. Line 518 says "messages as in the two patches", and each `git commit` line only has the subject in a comment, e.g. `# "camera: cap 4K Clear HDR 16-bit at 25 fps"`. T31 §6 does it right: it writes the full message inline with `git commit -m "camera: speed ramping, ...\n\n...\nTested: <counts from 5, ...>."`. Pointing to the patches is also unsafe, because every patch message ends with `Co-Authored-By: Claude Opus 5.5` and `Claude-Session:` trailers. verify3/llm/tutoring.md:41 forbids those on Patrik's own commits: "House format (skill: area, imperative, Why, Tested). No Co-Authored-By on his commits".

(2) Stale Tested line. kb/working/patches/0001-ui-4K-Clear-HDR-16-bit-offers-FPS-up-to-25.patch says "Tested: not built here (Qt is not on the host); one expression changed." Commit 266cb19 in verify2/home/ApertarUI has the same line. This contradicts three things:
- the T32 header at lines 18-19: "the whole touch UI built with Qt 6.4.2 on the host, QML compiled ahead of time";
- the sibling patch 0001-ui-FPS-picker-sends-only-set_fps-during-a-speed-ramp.patch: "Tested: host build of the whole UI with Qt 6.4.2 (QML compiled ahead of time). Not run on the Pi.";
- the host i
FIX (verified): A) T32 §6, line 518. Change "Core, two commits on `cinemate-port` (messages as in the two patches):" to "Core and touch UI, two commits each on `cinemate-port`:". Keep the four `git add` lines. Change each bare `git commit` + subject comment into an inline house-format message: subject, blank line, Why/What, Tested placeholder, no Co-Authored-By/Claude-Session trailers (llm/tutoring.md:41). Example in the T31 §6 style:

git -C ~/ApertarCore commit -m "camera: cap 4K Clear HDR 16-bit at 25 fps

Why: at 30 fps the 16-bit Clear HDR stream delivers about 28 fps and drops
frames; the back end is the limit (KB working/research-30fps-answer.md).
What: tableMaximumFpsForResolution() returns 25 for 3840x2160 Clear HDR at
16 bit, so the sanitiser, set_fps and ramp_fps stop there; the WebUI's
maximumSupportedFpsForSnapshot() follows. Clear HDR 12-bit and SDR 4K keep 30.
Tested: <5.1 result>."

git -C ~/ApertarCore commit -m "web: speed-ramp block in the Recording format card

Why: speed ramping (T31) had only socket commands; Cinemate has the same
controls on its web UI.
What: under Bit Depth: Speed Ramp On/Off, Shutter Sync Angle/Exposure, Ramp to
<fps> over Cut..20 s, x2 and Back, a note on format and take rate. Command
replies and the optimistic patch carry fps_ramp and fps_ramp_keep_exposure.
Tested: <5.2, 5.3, 5.5 results>."

git -C ~/ApertarUI commit -m "ui: 4K Clear HDR 16-bit offers FPS up to 25

Why: Core caps 4K Clear HDR 16-bit at 25 fps; the touch UI still offered 30.
What: maximumSupportedFpsForResolution() returns 25 for 3840x2160 Clear HDR at
16 bit. 12-bit Clear HDR and SDR 4K keep 30.
Tested: <5.1 touch UI picker ends at 25>."

git -C ~/ApertarUI commit -m "ui: FPS picker sends only set_fps during a speed-ramp take

Why: applyFps() followed set_fps with its own set_shutter_us and saved the
rate, which undoes Core's Exposure policy and persists a take-scoped rate.
What: the bridge reads fps_ramp; in a take with it on, applyFps() sends set_fps
only. Outside ramp takes nothing changes.
Tested: <5.4 result>."

B) In kb/working/patches/0001-ui-4K-Clear-HDR-16-bit-offers-FPS-up-to-25.patch (and the matching commit, if it is regenerated), change "Tested: not built here (Qt is not on the host); one expression changed." to "Tested: host build of the whole UI with Qt 6.4.2 (QML compiled ahead of time), with the FPS-picker patch on top. Not run on the Pi."

### 17. [T31] wrong - kb/tutorials/inbox/20261026210000 CINEMATE APERTAR T31 speed-ramping.md @ §4.2 (line 99), eleven CC line numbers
PROBLEM: Eleven numbers in 4.2 are 270 lines too low. They point at the wrong code on the T31 tree (the line numbers the status line says it uses). The setFps, setFpsRamp, recordingBaseFps, stop(), startRecording and header numbers in the same paragraph are correct.
VERIFIER: I checked this and the finding holds. The status line says the line numbers are on cinemate-port with the T31 patch applied. That tree is verify2/t31home/ApertarCore/src/camera/CameraController.cpp, which has 10460 lines. On that tree the eleven numbers in §4.2, line 99 of the T31 tutorial, point at the wrong code:

- 8846 is the `};` that closes `struct FpsRampEvent`, which starts at 8836.
- 8871-8877 is `emitMediaWriteState()`.
- 8879-8882 is the `exposureEvent_` media-write emit.
- 8887 is `if (!exposureEvent_) return;`.
- 8894-8904 is the constructor's init list (`previewCallback_`).
- 8953 is `return false;` and 8963 is `activeTuningExposureMeteringModes()`.
- 9466-9467 is `validateTuningFilePath` / `setErrorLocked`.
- 9960 is `return true;`.
- 9815 is `session_->startRecording(...)` inside `startRecording`, and 9840 is a lone `{`.

The real locations on that tree:

- `applyFpsStepLocked` runs from 9116 to 9153.
- In it, `if (rampingTake) { rampTakeChanged_ = true; std::cerr ... }` is 9142-9148, and `applySettingsLocked(next, false, commit)` plus `emitSettingsEventLocked()` plus `return applied;` is 9149-9152.
- `restoreFpsAfterRampLocked` runs from 9157 to 9174. Its re-persist branch (`if (std::abs(settings_.fps - rampTakeBaseFps_) < 0.0001) { ... persistSettingsLocked(); return; }`) is 9164-9169.
- `rampNominalShutterUs_ = 0; // an explicit shutter is the new nominal` is at 9223, and the reset in `setShutterAuto` is at 9233.
- The reset in `setFpsRamp` (`if (enabled !=
FIX (verified): In "kb/tutorials/inbox/20261026210000 CINEMATE APERTAR T31 speed-ramping.md" line 99, in both the export and verify3/tutorials/inbox, replace:
- `:8846-8883` with `:9116-9153` (or `CC:9116-9153`)
- `:8953` with `:9223`
- `:8963` with `:9233`
- `:9466-9467` with `:9736-9737`
- `:9960` with `:10238`
- `:8871-8877` with `:9142-9148`
- `:8879-8882` with `:9149-9152`
- `:8887-8904` with `:9157-9174`
- `:8894-8899` with `:9164-9169`
- `:9815` with `:10085`
- `:9840` with `:10110`

Leave the other numbers in the paragraph as they are: 9069-9114, 9072-9077, 8980-8986, 9826, 9728-9742, 9744-9750, 6877 and the header numbers.

### 18. [T31] wrong - kb/tutorials/inbox/20261026210000 CINEMATE APERTAR T31 speed-ramping.md @ §3.3 Answer (line 91) and §5 expectation (5) (line 142)
PROBLEM: The tutorial predicts a `phase-lock: released` line when the fps changes. Core never prints one for an fps change, before or after the patch. applyControls calls phaseLock_.release() directly, which sets active=false with no log line. The next stepFramePhaseLock then sees wasActive=false, and the 'released' line prints only when wasActive is true.
VERIFIER: Confirmed on both trees. Base b606c4f src/camera/CameraController.cpp: setFps (:8805-8836) goes through applySettingsLocked. The applyControls block at :6376-6380 calls `phaseLock_.release();` under controlsMutex_, and FramePhaseLock.hpp:67-71 `release() { active = false; previousNs = 0; }` logs nothing. The session-stop path at :6293 is just as silent. On the next frame, stepFramePhaseLock reads `const bool wasActive = phaseLock_.active;` (:7455), which is now false. step() then re-arms, which prints `armed` (:7493). The `released` line at :7479-7480 needs `if (wasActive)`, so it does not print. T31 tree: applyControls still releases silently (:6388-6392) and calls noteFpsChange at :6394. That is the only place the grace gets set (:8325). During the grace, `enabled` is false (:7494-7495). step(false) calls release(), but wasActive is already false (:7496), so :7520-7521 prints nothing. When the grace ends, the lock re-arms with `armed fps=` (:7534). Both run under controlsMutex_, so no frame can see the lock active between the release and the settings update. So §3.3 line 91 and §5 (5) line 142 are wrong both before and after the patch. A second problem sits in the same §5 check: the grep at line 139, `phase-lock (stats|armed|released)`, has a space after "phase-lock". The real lines read `ApertarCore phase-lock: armed fps=` (T31 CC:7534) and `phase-lock: released`, with a colon. That grep matches only `phase-lock stats:` (T31 CC:6570), so expectation (5) could not be seen a
FIX (verified): File: kb/tutorials/inbox/20261026210000 CINEMATE APERTAR T31 speed-ramping.md
1) Line 91 (§3.3 Answer). Replace "> `released` then `armed fps=50 ...` within a frame or two of each command: `applyControls` releases on any fps change (`CC:6376-6380@b606c4f`) and `FramePhaseLock` re-arms on the next frame. After the patch the `armed` line comes N+6 frames later, after the grace." with "> No `released` line: only `armed fps=50 ...` and then `armed fps=25 ...`, each within a frame or two of its command. `applyControls` releases the lock silently on any fps change (`CC:6376-6380@b606c4f`; the `released` line prints only when the lock was still active at the next frame), and `FramePhaseLock` re-arms on the next frame. After the patch each `armed` line comes N+6 frames later, after the grace." (Line 87's grep can stay as it is, or narrow to 'phase-lock: armed'.)
2) Line 139 (§5 grep). Replace `phase-lock (stats|armed|released)` with `phase-lock( stats|: armed)`. The current pattern never matches `ApertarCore phase-lock: armed fps=` (T31 CC:7534) because of the colon.
3) Line 142 (§5 expectation 5). Replace "(5) `phase-lock: released` at the first step up and `armed fps=50` N+6 frames after the last step;" with "(5) no `released` line (each step's release in `applyControls` is silent); `armed fps=50` N+6 frames after the last step up and `armed fps=25` N+6 frames after the last step down;".

### 19. [T31] wrong - kb/tutorials/inbox/20261026210000 CINEMATE APERTAR T31 speed-ramping.md @ §5 journal command (line 139)
PROBLEM: The grep pattern `phase-lock (stats|armed|released)` needs a space right after 'phase-lock', but Core prints 'phase-lock: armed'. So the armed and released lines that expectation (5) asks for never show. Separately, `tail -60` is too short: 50 request lines plus up to 50 frame= lines plus the stats lines come to more than 100, so expectation (1) cannot be counted from the output.
VERIFIER: Both parts of the finding are real. The T31 tutorial's §5 command is at line 139 of the export, and the copy in verify3 has the same line. It reads: journalctl -u apertar-core -b --no-pager | grep -E 'fps ramp|capture stats|phase-lock (stats|armed|released)|audio sync' | tail -60.

(a) Wrong regex. Core logs these lines with a colon after 'phase-lock'. On the T31-only tree (verify2/t31home/ApertarCore), src/camera/CameraController.cpp:7521 has `std::cerr << "ApertarCore phase-lock: released\n";` and :7534 has `std::cerr << "ApertarCore phase-lock: armed fps=" << settings_.fps`. Only :6570 `"ApertarCore phase-lock stats: ..."` has a space right after 'phase-lock'. The T32 tree and tip-core have the same two strings at :7526 and :7539. I ran the original pattern over sample lines in /tmp/claude-0/-home-user-apertar-kb/17fc979d-f346-53ac-97ad-c8caa225a57d/scratchpad/audit-notes/t31-3-sample.txt. It printed only the 'phase-lock stats:' and 'fps ramp' lines and dropped 'phase-lock: armed' and 'phase-lock: released'. So expectation (5) at line 142 can never be seen. With 'phase-lock:? (stats|armed|released)' all of them print.

(b) tail -60 is too short. Expectation (1) asks for 50 request lines. These come from CameraController.cpp:9144 'fps ramp: <from> -> <to> fps shutter_us=...', one per step: 25 up plus 25 down. There are also up to 50 'fps ramp: frame=' lines (:8394), the 'fps ramp stats:' line (:8421), the phase-lock stats line, the audio sync line, and the released/armed li
FIX (verified): In kb/tutorials/inbox/20261026210000 CINEMATE APERTAR T31 speed-ramping.md §5 code block (lines 134-140):
1. Add this as the first line of the block, before the set_fps_ramp line: T0=$(date '+%F %T')
2. Replace line 139 with these lines:
journalctl -u apertar-core --since "$T0" --no-pager | grep -E 'fps ramp|capture stats|phase-lock:? (stats|armed|released)|audio sync' | tail -150
journalctl -u apertar-core --since "$T0" --no-pager | grep -c 'fps ramp: [0-9.]* -> '    # 50 requests
journalctl -u apertar-core --since "$T0" --no-pager | grep -c 'fps ramp: frame='         # up to 50, fewer when superseded
If the KB keeps -b, at least change the regex to 'phase-lock:? (stats|armed|released)' and the tail to -150. Then say that the counts assume the first ramp take since boot.

### 20. [T31] wrong - kb/tutorials/inbox/20261026210000 CINEMATE APERTAR T31 speed-ramping.md @ §4.4 (line 115) / §4.5 (line 117)
PROBLEM: No step tells the reader to add the noteFpsChange call in applyControls. 4.4 mentions it only as a locking note. Typed as written, the steps give a grace window that never opens and ramp events that are never queued, so there is no fps-ramp.txt, no frame= lines and drops at each step. The call must also come before `settings_ = sanitized`, because it reads the old rate from settings_.fps.
VERIFIER: I confirmed the finding. The T31 patch adds a hunk in applyControls (patch lines 401-402), and on the T31 tree it sits at /tmp/claude-0/-home-user-apertar-kb/17fc979d-f346-53ac-97ad-c8caa225a57d/scratchpad/verify2/t31home/ApertarCore/src/camera/CameraController.cpp:6393-6395:
`if (std::fabs(settings_.fps - sanitized.fps) > 1e-9)` / `noteFpsChange(settings_.fps, sanitized.fps, sanitized.shutterUs);` / `settings_ = sanitized;`
The hunk is inside the block that holds sessionSettingsMutex_ and controlsMutex_, after the phase-lock release.

No numbered step in section 4 of the tutorial (kb/tutorials/inbox/20261026210000 CINEMATE APERTAR T31 speed-ramping.md) tells the reader to add this call:
- 4.4 lists noteFpsChange only as a method to define (line 107).
- The only place the call site appears is the locking note at line 115: "`noteFpsChange` is called from `applyControls` under the settings and controls mutexes (`:6393-6394`)". It describes the code. It does not tell the reader to add anything, and it gives neither the condition nor the order.
- 4.5, "Wire the frame path", lists recordRawFrame, trackRecordingCadence, stepFramePhaseLock, startRecording and stopRecording. It does not list applyControls.
- The diagram in section 2 (line 45) and the tutor ref at line 209 (`ref core src/camera/CameraController.cpp 6394 noteFpsChange(...)`) both expect the call to be there.

This breaks the KB rule in tutorials/README.md:47 for section 4 ("Numbered steps. File, location ..., the chang
FIX (verified): In kb/tutorials/inbox/20261026210000 CINEMATE APERTAR T31 speed-ramping.md, §4.5, insert this as the first item, before "`recordRawFrame` after `metadataFromRequest`":

"`applyControls`, inside the block that holds `sessionSettingsMutex_` and `controlsMutex_`, after the phase-lock release and before `settings_ = sanitized;` (`CC:6393-6394`): `if (std::fabs(settings_.fps - sanitized.fps) > 1e-9) noteFpsChange(settings_.fps, sanitized.fps, sanitized.shutterUs);` — it must come before the assignment, because `settings_.fps` is still the old rate there; after the assignment the test is never true and no grace or event is ever recorded."

Keep the locking note at line 115 as it is. Its `:6393-6394` is correct on the T31 tree.

### 21. [T31] wrong - kb/tutorials/inbox/20261026210000 CINEMATE APERTAR T31 speed-ramping.md @ §7 Undo (line 187) and status line 'Risk' (line 19)
PROBLEM: §6 commits the change. After that, `git checkout -- <files>` does nothing, because the working tree already matches HEAD, so the 'Full undo' does not undo the patch. T32 uses `git revert` for the same situation.
VERIFIER: Confirmed in /tmp/claude-0/-home-user-apertar-kb/17fc979d-f346-53ac-97ad-c8caa225a57d/scratchpad/apertar-kb-speed-ramp-2026-10-27/kb/tutorials/inbox/20261026210000 CINEMATE APERTAR T31 speed-ramping.md.

- §6 (lines 157-158) runs `git -C ~/ApertarCore add include/apertar/core/Types.hpp src/camera src/audio src/cdng src/ApertarCoreApp.cpp src/ApertarCoreApp.hpp` and then `git -C ~/ApertarCore commit -m "camera: speed ramping ..."`.
- §7 line 187 says: "Full undo: `git checkout -- include/apertar/core/Types.hpp src/camera src/audio src/cdng src/ApertarCoreApp.cpp src/ApertarCoreApp.hpp`, rebuild."
- Line 19 (Risk) says: "Undo: `set_fps_ramp enabled=false`, or `git checkout` the eight files."

After the §6 commit the working tree matches HEAD, so `git checkout -- <paths>` changes nothing and the patch stays in. The same is true for anyone who applied the patch with `git am`, which the status line (line 11) and INSTALL.md:14 both point to, because `git am` commits as well. That checkout line also leaves out `-C ~/ApertarCore`, unlike every other git line in the tutorial.

The "eight files" count is correct: the patch has eight `diff --git` entries (Types.hpp, ApertarCoreApp.cpp/.hpp, AudioRecordingSession.cpp, CameraController.cpp/.hpp, CdngEncoder.cpp/.hpp).

T32 handles the same situation with `git revert`, at T32 line 31 ("Undo: `git revert` the commits, rebuild") and line 549 ("Undo: `git revert` the two Core commits and the two UI commits, rebuild both").

The KB rule at ver
FIX (verified): In kb/tutorials/inbox/20261026210000 CINEMATE APERTAR T31 speed-ramping.md:

Line 187, replace with:
"Undo: `set_fps_ramp enabled=false` (persisted). Full undo before §6: `git -C ~/ApertarCore checkout -- include/apertar/core/Types.hpp src/camera src/audio src/cdng src/ApertarCoreApp.cpp src/ApertarCoreApp.hpp`. After the §6 commit (or after `git am` of the patch): `git -C ~/ApertarCore revert <sha of the T31 commit>`, reverting T32's two Core commits first if T32 is applied. Rebuild."

Line 19, replace "Undo: `set_fps_ramp enabled=false`, or `git checkout` the eight files." with:
"Undo: `set_fps_ramp enabled=false`, or `git revert` the T31 commit (`git checkout` the eight files only before §6 commits them)."

### 22. [T31] wrong - kb/tutorials/inbox/20261026210000 CINEMATE APERTAR T31 speed-ramping.md @ §7 row 'file numbers with holes' (line 176); §5.1 'file numbers contiguous' (line 144)
PROBLEM: Count-based numbering does not stop holes caused by drops in the recorder. nextFrameIndex uses up the index before the queue-capacity and enqueue checks, so a drop[queue-full] still leaves a missing file number. On cinemate-port the copy runs on the recorder worker (T25), so this is a real cause in a ramp take. The table names only countOnly or a mid-take toggle.
VERIFIER: I confirmed this in the T31 tree (/tmp/claude-0/-home-user-apertar-kb/17fc979d-f346-53ac-97ad-c8caa225a57d/scratchpad/verify2/t31home/ApertarCore/src/camera/CameraController.cpp).

How the index is used up:
- CC:8013 runs `const uint64_t frameIndex = recorder_.nextFrameIndex(timestampUs, /*countOnly=*/settings_.fpsRampEnabled);` before any drop check.
- nextFrameIndex at CC:3790-3791 has already stored `frameIndex_.store(index + 1, ...)`.

Recorder-side paths that drop the frame after that:
1. CC:8041-8042 `if (!recorder_.hasCapacityForFrame(frameIndex)) return false;`, which logs `ApertarCore drop[queue-full]: frame=` (CC:3909).
2. CC:8063-8064 `if (!recorder_.enqueueCopy(std::move(copy))) return false;`. enqueueCopy (CC:4056-4069) drops when `heldRequests_ >= maxHeldRequests_` and logs `ApertarCore drop[copy-slot]: frame=` (CC:4064).
3. The copy worker's `enqueue` (CC:3987-3997) drops when `queue_.size() >= maxQueuedFrames_` and logs `drop[queue-full]: frame=` with `metadata.frameIndex`.

In each case the number is already used, so a ramp take has a missing file number. Count-based numbering only hides sensor-side gaps (`drop[capture-gap]`).

The per-frame lines print only on the 1st and every 30th drop (CC:3908, 3990, 4063). The reliable totals are the stop-line counters `dropped_queue_full=` (CC:3673) and `dropped_copy_slot=` (CC:3658).

The tutorial has three wrong spots:
- §5.1 (line 144) says file numbers are contiguous, with no exception.
- §7 (line 176) blames holes 
FIX (verified): File: kb/tutorials/inbox/20261026210000 CINEMATE APERTAR T31 speed-ramping.md

1. §5.1, line 144. Replace
"file numbers contiguous (`ls | wc -l` equals the last number + 1);"
with
"file numbers contiguous unless the recorder dropped frames (`ls | wc -l` plus the stop line's `dropped_queue_full=` and `dropped_copy_slot=` equals the last number + 1; a recorder drop has already used up its index at `:8013`);"

2. §7, line 176, row 'file numbers with holes in a ramp take'. Replace the 'It means' cell with
"`countOnly` not passed at `:8013`, the setting toggled mid-take (refused, check the reply), or a real recorder drop (`drop[queue-full]` / `drop[copy-slot]` in the journal, `dropped_queue_full=` / `dropped_copy_slot=` > 0 on the stop line). The index is used up before the capacity and enqueue checks; count-based numbering hides only sensor-side gaps."
Replace the 'Do' cell with
"no drop counters: fix the call, count-based is the whole point. Drop counters > 0: a recorder/medium throughput problem (T25), not a ramp bug."

3. §8, line 195. Replace
"so real drops leave holes again in a ramp take"
with
"so sensor-side gaps (`drop[capture-gap]`) leave holes again in a ramp take (recorder drops already do)".

### 23. [T31] wrong - kb/tutorials/inbox/20261026210000 CINEMATE APERTAR T31 speed-ramping.md @ §5.3 Shutter policy (line 148)
PROBLEM: The exposure arithmetic is wrong. 40 ms to 20 ms is a full stop darker, not half a stop, and so is 20 ms to 10 ms in angle mode at 50 fps. With the exposure kept at 20 ms, the blur per frame stays the same length, because the angle doubles to 360°; it does not halve.
VERIFIER: The finding is correct. The code is in /tmp/claude-0/-home-user-apertar-kb/17fc979d-f346-53ac-97ad-c8caa225a57d/scratchpad/verify2/t31home/ApertarCore/src/camera/CameraController.cpp. Lines 9136-9137 read `frameUs = floor(1000000.0 / effectiveFps)` and `next.shutterUs = std::min(rampNominalShutterUs_, frameUs)`. So with `shutter=exposure` at 360°, the 40000 us exposure (25 fps) is clamped to 20000 us at 50 fps. Half the exposure time is one full stop, not half a stop. For the `angle` policy, line 9126 calls `shutterUsForPreservedAngle` (lines 202-210), which works out `shutter * currentFps / nextFps`: 20000 * 25/50 = 10000 us. That is also one full stop darker at 50, not half a stop. In the 180° case (20 ms) under the exposure policy, `min(20000, 20000)` keeps the exposure at 20 ms. Each frame's blur therefore stays the same absolute length, and relative to the frame it doubles, because the angle goes from 180° to 360°. The tutorial says the blur halves, which is wrong either way. Cinemate's docs/speed-ramping.md:31 only says "darker", so nothing upstream backs "half a stop". The same two errors are also in kb/working/ramp-answer.md:94 ("motion blur halves at 50") and :95 ("half a stop darker at 50"). The reviewer did not mention that file.
FIX (verified): Make three changes in kb/tutorials/inbox/20261026210000 CINEMATE APERTAR T31 speed-ramping.md, line 148 (§5.3):
1. Change "(`(shutter clamped to the frame)` on the line, half a stop darker, as on Cinemate)" to "(`(shutter clamped to the frame)` on the line, one stop darker, as on Cinemate)".
2. Change "At 180° (20 ms): brightness constant through the ramp, blur halves at 50." to "At 180° (20 ms): brightness constant through the ramp, the same 20 ms blur per frame (360° at 50)."
3. Change "With `angle`: blur constant, half a stop darker at 50." to "With `angle`: blur constant, one stop darker at 50."

Fix the same errors in kb/working/ramp-answer.md:
- Line 94: change "brightness constant through the ramp, motion blur halves at 50," to "brightness constant through the ramp, the same blur per frame (the angle doubles at 50),".
- Line 95: change "`policy=angle`: blur constant, half a stop darker at 50" to "`policy=angle`: blur constant, one stop darker at 50".

Make each change in both the export (apertar-kb-speed-ramp-2026-10-27/kb/...) and verify3.

### 24. [T31] minor - kb/tutorials/inbox/20261026210000 CINEMATE APERTAR T31 speed-ramping.md @ §1 line 23 `:7533-7539`
PROBLEM: This number has no @b606c4f mark, so by the status-line rule it is read on the T31 tree. There, lines 7533-7539 are the phase-lock 'armed' log, not the merge of pendingControls_ in requeueRequest.
VERIFIER: Confirmed. The T31 status line (T31.md:11) says: "Line numbers below are on `cinemate-port` with this patch applied, unless marked `@b606c4f` (before the patch)." In §1, line 23, the bare `(:7533-7539)` comes right after `CC:6355-6388@b606c4f`, but it has no mark of its own, so by that rule it is read on the T31 tree. On the T31 tree, verify2/t31home/ApertarCore/src/camera/CameraController.cpp:7528-7539 is the phase-lock arm block. Line 7534 there is `std::cerr << "ApertarCore phase-lock: armed fps=" << settings_.fps`, and the range ends at 7539 `}`. On base b606c4f, CC:7533-7539 is exactly the pendingControls_ merge block in requeueRequest: 7533 `{`, 7534 `std::lock_guard<std::mutex> lock(controlsMutex_);`, 7535 `if (!pendingControls_.empty()) {`, 7536 `request->controls().merge(pendingControls_);`, 7537 `pendingControls_.clear();`, 7538-7539 `}`. On the T31 tree the same block is at CC:7574-7580, with the merge at 7577. Sources (T31.md:203) already lists `:7533-7539` under "Apertar-Core `b606c4f` (before the patch)", which confirms the base commit was meant. The sentence is §1 prose, outside any tutor block, so tutorial.py does not check it. The proposed fix is right.
FIX (verified): In kb/tutorials/inbox/20261026210000 CINEMATE APERTAR T31 speed-ramping.md, line 23, change "carries the new `FrameDurationLimits` (`:7533-7539`);" to "carries the new `FrameDurationLimits` (`:7533-7539@b606c4f`);". This matches Sources at line 203. The other option is to cite the T31 tree as `CC:7574-7580`, but the @b606c4f form keeps §1 consistent with its neighbouring refs (`CC:8808-8811@b606c4f`, `CC:6355-6388@b606c4f`).

### 25. [T31] minor - kb/tutorials/inbox/20261026210000 CINEMATE APERTAR T31 speed-ramping.md @ §4.1 line 97, §7 line 185, §2 line 63, §4.4 line 103
PROBLEM: Smaller line-number errors on the T31 tree: two refs are off by one and four ranges have the wrong start or end.
VERIFIER: I checked every ref on the T31 tree (/tmp/claude-0/-home-user-apertar-kb/17fc979d-f346-53ac-97ad-c8caa225a57d/scratchpad/verify2/t31home/ApertarCore) with exact line numbering (awk NR / grep -n). All six errors are real.
(1) Line 97 (§4.1) cites App `:214-215`, but src/ApertarCoreApp.cpp:214 is `fps_phase_lock`. `fps_ramp` is at :215 and `fps_ramp_keep_exposure` at :216. The second copy is at :7993-7994, so "near :7994" is fine as written.
(2) Line 185 (§7) cites `:9112`, but src/camera/CameraController.cpp:9112 is the comment "(Cinemate ff59dd8: ...)". `return applyFpsStepLocked(effectiveFps, rampingTake, /*commit=*/!rampingTake);` is at :9113.
(3) Line 63 (§2) cites `:3785-3791` for nextFrameIndex. The function starts at CC:3785, but :3791 is `frameIndex_.store(...)`. `return index;` is at :3792 and the closing `}` at :3793.
(4) Lines 63 (§2) and 103 (§4.4) cite `:8302-8459`. CC:8302 is mid-comment ("is programmed on frame ~N+2 after the request..."). The block banner `// ---- Speed ramping (T31) ----` is at :8293, the first helper `fpsRampGraceFrames()` at :8308, and :8459 is the last helper's closing brace (trackRecordingCadence is at :8461). kb/llm/tutoring.md:107 (the T31 row, added in the verify3 diff) has the same `:8302-8459`.
(5) Line 63 cites `AudioRecordingSession.cpp:382-388`. Lines 382-386 are the patch's added lines; the statement they start ends at :389 (`: videoLastBootUs_ + uint64_t(videoLastDurationUs_);`). :388 is the middle of the ternary.
(6) Line 63 cit
FIX (verified): In kb/tutorials/inbox/"20261026210000 CINEMATE APERTAR T31 speed-ramping.md":
- line 97 (§4.1): `:214-215` -> `:215-216`
- line 185 (§7): `(`:9112`)` -> `(`:9113`)`
- line 63 (§2): `:3785-3791` -> `:3785-3793`
- line 63 (§2) and line 103 (§4.4): `:8302-8459` -> `:8293-8459`
- line 63 (§2): `AudioRecordingSession.cpp:382-388` -> `AudioRecordingSession.cpp:382-389`
- line 63 (§2): `App:9238-9280` -> `App:9238-9285` (or `App:9238-9297`, which also covers stopFpsRamp and matches kb/llm/tutoring.md:107)
Also in kb/llm/tutoring.md line 107 (T31 row): `:8302-8459` -> `:8293-8459`.

### 26. [T31] minor - kb/tutorials/inbox/20261026210000 CINEMATE APERTAR T31 speed-ramping.md @ Status line (line 11); bare refs in §4.2-§4.6 and §7
PROBLEM: The tutorial never defines `CC` or `App`. Many bare `:NNNN` refs come after a different file has been named, so by the rule that a bare ref belongs to the last file named, they point into the wrong file.
VERIFIER: Mostly refuted, but there is a real problem at the same location. Some of the finding's line numbers are wrong for a reason the reviewer did not name.

What is refuted:
(1) `CC` and `App` are abbreviations used across the whole KB. They are defined in llm/README.md §3 ("| `App` | Apertar-Core/src/ApertarCoreApp.cpp |", "| `CC` | Apertar-Core/src/camera/CameraController.cpp |"), and the earlier tutorials T23, T25, T27, T28 and T29 use `CC:`/`App:` without defining them (git show 7886e5b^:tutorials/inbox/...).
(2) Neither tutorials/README.md nor handoff-T26-T30.md §2 has a rule that a bare ref belongs to the last file named. Grepping the KB finds no such rule.
(3) None of the cited bare refs can point into the "foreign" file, because those files are too short: CameraController.hpp has 181 lines, cinemate cinepi_controller.py 4340, and libcamera-qbc agc_channel.cpp 1003. So `:9072`, `:8846`, `:8953` and `:3785` cannot be in them. In 4.6 the text says `AudioRecordingSession::observeVideoFrame (:385-389)`, which names the file. AudioRecordingSession.cpp:385 is the `byDuration` line, and the tutor block has `ref core src/audio/AudioRecordingSession.cpp 385`. Adding definitions is a style change.

What is real: §4.2 (and one §7 ref) gives CameraController.cpp line numbers from the old cloud branch d4ad539, not from cinemate-port with the T31 patch. The status line says the numbers are on that tree. Evidence (t31home tree vs /home/user/tiramisioux/apertar-core d4ad539):
- applyFpsSte
FIX (verified): Do NOT add the CC/App definition to the status line or change refs to `CC:` (not needed, since CC/App are KB-wide per llm/README.md §3). Instead, fix the stale line numbers in "20261026210000 CINEMATE APERTAR T31 speed-ramping.md":

§4.2:
- `(`:8846-8883`)` -> `(`CC:9116-9153`)`
- "after its checks, `:8953`" -> "`:9223`"
- "(`:8963`)" -> "(`:9233`)"
- "(`:9466-9467`)" -> "(`:9736-9737`)"
- "`applyCapturePreset`, `:9960`" -> "`:10238`"
- "(`:8871-8877`)" -> "(`:9141-9147`)"
- "(`:8879-8882`)" -> "(`:9149-9152`)"
- "`restoreFpsAfterRampLocked()` (`:8887-8904`)" -> "(`:9157-9174`)"
- "(`:8894-8899`)" -> "(`:9164-9169`)"
- "(`:9815`, `:9840`)" -> "(`:10085`, `:10110`)"

§7: "`commit` not passed as `!rampingTake` (`:9112`)" -> "(`:9113`)".

Optional, for consistency with the README's version rule: "`agc_channel.cpp:398`, `:983@7e9fef0`" -> "`agc_channel.cpp:398@7e9fef0`, `:983@7e9fef0`". Leave all other refs as they are.

### 27. [T31] minor - kb/tutorials/inbox/20261026210000 CINEMATE APERTAR T31 speed-ramping.md @ §4.2 (line 99)
PROBLEM: 4.2 does not give the new refusal text for the case where ramping is off. A reader who keeps the old message will not match the §7 row 'Stop recording before changing FPS, or enable FPS ramping'.
VERIFIER: The finding is real; I couldn't refute it. In kb/tutorials/inbox/"20261026210000 CINEMATE APERTAR T31 speed-ramping.md", line 99 (§4.2) says "if so, refuse unless `settings_.fpsRampEnabled`" but gives no message for that refusal. The other two refusals in the same paragraph do quote their messages: "The take ended; FPS ramp stopped." and "FPS ramping works in cDNG and MLV takes only.". The tutorial says "Port the logic; type it in, do not paste Cinemate". A reader who leaves the old refusal text in place, or writes their own, will not match the §7 row at line 175, "`Stop recording before changing FPS, or enable FPS ramping` | the setting is off". Evidence: the T31 tree, verify2/t31home/ApertarCore/src/camera/CameraController.cpp:9084, reads `setErrorLocked("Stop recording before changing FPS, or enable FPS ramping (set_fps_ramp) for cDNG/MLV takes.");` inside `if (!settings_.fpsRampEnabled)` (lines 9083-9086). The patch has the same text at line 757 (+), and its line 744 (-) removes the old text. The base, b606c4f CC:8809, reads "Stop recording before changing FPS so video and audio keep the same timeline.". The tutorial quotes only that old text, at line 23. No check catches the gap: check 3.1 greps 'Stop recording before changing FPS', which counts 1 with either message, and §5.5 lists no ramping-off refusal. The finding's location (line 99, §4.2) and its proposed fix are correct. The one addition is the `:9084` line reference.
FIX (verified): In the T31 tutorial, line 99 (§4.2), replace "if so, refuse unless `settings_.fpsRampEnabled`, and refuse when" with "if so, refuse unless `settings_.fpsRampEnabled` (\"Stop recording before changing FPS, or enable FPS ramping (set_fps_ramp) for cDNG/MLV takes.\", `:9084`), and refuse when".

### 28. [T31] minor - kb/tutorials/inbox/20261026210000 CINEMATE APERTAR T31 speed-ramping.md @ §7 rows 1, 4 and 9 (lines 175, 178, 183)
PROBLEM: Three rows contradict the code. Row 1: its 'Do' (`set_fps_ramp enabled=true`) is refused while a take runs, which is when this message appears. Row 4: the dashes in fps-ramp.txt are in columns 2-5, not at the end of the row. Row 9: the folder path is set for MLV too, so 'MLV path?' is not a cause.
VERIFIER: All three parts of the finding check out on the T31 tree (verify2/t31home/ApertarCore/src/camera/CameraController.cpp). The rows are at T31 md lines 175, 178 and 183. The proposed fix for row 9 is partly wrong.

Row 1 (md:175): the message `Stop recording before changing FPS, or enable FPS ramping (set_fps_ramp) for cDNG/MLV takes.` comes from CC:9084. It sits inside `if (rampingTake)`, and CC:9078 sets `rampingTake = recording_ && std::abs(fps - settings_.fps) > 0.0001`, so the message only appears while a take is running. At that moment `setFpsRamp` refuses the change at CC:9731-9735: `if (recording_ && enabled != settings_.fpsRampEnabled) { setErrorLocked("Stop recording before turning FPS ramping on or off."); return false; }`. So the row's 'Do' (`set_fps_ramp enabled=true`) fails as written.

Row 4 (md:178): the writer at CC:8449-8457 writes `event.frameIndex << ' '` first, then either the applied fields or `"- - - -"`, then always `' ' << bootUs << ' ' << fromFps << ' ' << toFps << ' ' << shutterUs`. The header at CC:8448 is `# requested_frame applied_frame frame_us seen tc_at_base boot_us from_fps to_fps shutter_us`. So the dashes fill columns 2-5 (applied_frame through tc_at_base), and the row ends with boot_us, from_fps, to_fps and shutter_us. It never ends with dashes.

Row 9 (md:183): CC:3483 `folderPathString_ = folderPath_.string();` runs for every raw take, before `mlvPathString_` at CC:3484, inside DngRecordingQueue (class at CC:3402; `recorder_` is declared at
FIX (verified): In kb/tutorials/inbox/20261026210000 CINEMATE APERTAR T31 speed-ramping.md, §7:

Line 175, 'Do' cell: replace
`set_fps_ramp enabled=true`; it persists
with
stop the take, `set_fps_ramp enabled=true` (refused while recording; it persists), start a new take

Line 178, 'You see' cell: replace
`fps-ramp.txt` rows ending `- - - -`
with
`fps-ramp.txt` rows with `- - - -` in columns 2-5 (applied_frame..tc_at_base)

Line 183, 'It means' cell: replace
`folderPathString()` empty (MLV path?) or the medium was gone (T28, by design)
with
the medium was gone (T28, by design), or the file could not be opened (`fps ramp: could not write <path>` in the log)

Leave the 'Do' cell on line 183 as it is.

### 29. [T31] minor - kb/tutorials/inbox/20261026210000 CINEMATE APERTAR T31 speed-ramping.md @ §4.5 (line 117), claim about `:8376`
PROBLEM: The tutorial says the two-frame guard stops a frame that is still at an older period from closing a newer request. It only covers two frames. The old period lasts about N+2 frames, so a quick A→B→A reversal (for example the pot flickering at a preset boundary, §8) still pairs B→A on an old-period frame and marks A→B as superseded with seen=0.
VERIFIER: I checked this on the T31 tree (verify2/t31home/ApertarCore/src/camera/CameraController.cpp) and the finding holds. The guard at CC:8376 is `if (event.applied || frameIndex < event.frameIndex + 2) continue;`. The code's own comment at CC:8300-8304 says the new period is programmed about N+2 frames after the request, where N is requests_.size(), 4 to 10. CC:7576-7578 merges pendingControls_ into the next requeued request and then clears it. So for a request A->B (event 0, stamped at frame k0) followed d frames later by B->A (event 1, stamped at k1 = k0+d, with 1 <= d < N), B goes out on its own request and the sensor runs B for about d frames starting near k0+N+2. On frame k1+2 the frame's own FrameDuration (CC:8004) is still A. In pairFpsRampEvents, event 0 (target B) misses, because |A-B| is larger than the tolerance of 0.5|B-A|. Event 1 (target A) is past its two-frame guard and matches. Its inner loop (j <= i) then sets event 0 to applied with seen=0 and logs `lag_frames=2 superseded=1`. When the B frames arrive later, nothing pairs them. As a result, fps-ramp.txt says B was skipped although the sensor ran it, and lag_frames, the number the grace window is sized from, reads 2 instead of about N+2. A monotonic stepper ramp is not affected, because an old period A is two steps from target C and outside the half-step tolerance. The quick reversal the tutorial itself names in §8 (a pot flickering at a preset boundary, line 193) is affected. Only the log is wrong: grace is time
FIX (verified): Required tutorial-only fix: in kb/tutorials/inbox/20261026210000 CINEMATE APERTAR T31 speed-ramping.md line 117, replace "and never earlier than two frames after the change was stamped (`:8376`): `DelayedControls` cannot apply it sooner, and a frame still at an older period that happens to match a newer request would otherwise close the older request as superseded." with "and never earlier than two frames after the change was stamped (`:8376`): `DelayedControls` cannot apply it sooner. The guard is two frames, not the ~N+2 the sensor needs, so a quick reversal (A->B->A within about N frames, e.g. a pot flickering at a preset boundary, §8) still lets a frame at the old period A close the B->A request with `lag_frames=2` and mark A->B `seen=0`, although the sensor runs B for a few frames; only the log is affected, not frame numbering or timecode." Optional code fix, which needs the T31 patch and the tutorial updated together: at CC:8376, change the guard to `if (event.applied || frameIndex < event.frameIndex + requests_.size())` (requests_ is a CameraSession member, already used in fpsRampGraceFrames at CC:8316). Update the comment at CC:8374-8375 to "the sensor takes ~N+2 frames (CC:8303), so a frame closer to the stamp than N still runs an older period". If you make that code change, the tutorial wording becomes "never earlier than N frames after the change was stamped (`:8376`)". A reversal within 1-2 frames can still mis-pair inside the ±1 slack.

### 30. [T31] minor - kb/tutorials/inbox/20261026210000 CINEMATE APERTAR T31 speed-ramping.md @ §4 steps and tutor block (lines 97-121, 225-231); §6 (line 169)
PROBLEM: This breaks two KB rules. tutorials/README.md asks for 'One **Check:** per step' in §4, but T31 has no Check lines and the tutor block covers only 4.2, 4.4 and 4.7. handoff §2 asks for 'a fork-log row for every Core/driver/libcamera commit', and T32 §6 does it, but T31 §6 does not.
VERIFIER: The missing Check lines are a real problem; the fork-log half is not.

1. Check lines: real. tutorials/README.md:47 says "Numbered steps. ... One **Check:** per step". llm/tutoring.md:127 and :130 say the same ("One **Check:** per step" and "a `check` per **Check:**"). T31 §4 (lines 97-121) has no "**Check:**" line: grep -c gives 0 for T31 and 9 for T32. The T31 tutor block (lines 225-231) has checks only for 3.1, 4.2 (twice), 4.4, 4.7, 5 and 5.1, so 4.1, 4.3, 4.5 and 4.6 have none. T27-T30 also skip Check lines, but that does not change the written rule, and T32 in the same export follows it.

The four proposed checks hold. On the T31-only tree, the T31+T32 tree and tip-core:
- `grep -c fpsRamp Types.hpp` = 3
- `grep -c countOnly CameraController.cpp` = 4
- `grep -c 'writeFpsRampLog(mediumGone);'` = 1
- `grep -c byDuration AudioRecordingSession.cpp` = 2

All four give 0 on b606c4f, so each fails before the change, as tutoring.md step 10 requires. They pass the read-only filter in tutorial.py:169 (the `;` and `(` are inside single quotes). The existing checks also count correctly on all three trees: fpsRampEnabled=11, inFpsRampGrace=3, restoreFpsAfterRampLocked=4, ramp_fps in ApertarCoreApp.cpp=4.

2. Fork-log row in §6: not a real violation. The tutorial shape in tutorials/README.md:49 (§6 = git add, commit message, push) does not mention fork-log. handoff-T26-T30.md §2 is about commits Claude writes. working/handoff-speed-ramp.md:32 and :59 already tell the tutor to "add fo
FIX (verified): In kb/tutorials/inbox/20261026210000 CINEMATE APERTAR T31 speed-ramping.md, add a blank line and then one **Check:** line after each §4 step paragraph:

- After 4.1 (line 97): **Check:** `grep -c 'fpsRamp' include/apertar/core/Types.hpp` → 3.
- After 4.2 (line 99): **Check:** `grep -c 'restoreFpsAfterRampLocked' src/camera/CameraController.cpp` → 4 (and `grep -c 'fpsRampEnabled' src/camera/CameraController.cpp` → 11 once 4.1-4.5 are in).
- After 4.3 (line 101): **Check:** `grep -c 'countOnly' src/camera/CameraController.cpp` → 4.
- After 4.4 (after the paragraph ending at line 115): **Check:** `grep -c 'inFpsRampGrace' src/camera/CameraController.cpp` → 3.
- After 4.5 (line 117): **Check:** `grep -c 'writeFpsRampLog(mediumGone);' src/camera/CameraController.cpp` → 1.
- After 4.6 (line 119): **Check:** `grep -c 'byDuration' src/audio/AudioRecordingSession.cpp` → 2.
- After 4.7 (line 121): **Check:** `grep -c 'ramp_fps' src/ApertarCoreApp.cpp` → 4.
- 4.8 is already a check step (the g++ -fsyntax-only loop).

In the tutor block, add these four lines next to the existing check lines (between lines 225 and 231), keeping step order:

```
check 4.1 | grep -c 'fpsRamp' /home/pi/ApertarCore/include/apertar/core/Types.hpp | ^3$
check 4.3 | grep -c 'countOnly' /home/pi/ApertarCore/src/camera/CameraController.cpp | ^4$
check 4.5 | grep -c 'writeFpsRampLog(mediumGone);' /home/pi/ApertarCore/src/camera/CameraController.cpp | ^1$
check 4.6 | grep -c 'byDuration' /home/pi/ApertarCore/src/audio/AudioRecordingSession.cpp | ^2$
```

The §6 fork-log line is optional, not required. If you want T31 to match T32 §6:531, change line 169 to: "Commit on `cinemate-port`; add a `fork-log.md` row for the commit. Pushing follows `working/mac-driven-loop.md` and happens only when you decide."

### 31. [T31] minor - kb/tutorials/inbox/20261026210000 CINEMATE APERTAR T31 speed-ramping.md @ §9 Sources, libcamera bfe0b76 (line 202)
PROBLEM: §1 cites `ipa_base.cpp:851` and `:1638-1667@bfe0b76`, but Sources does not list them. Sources lists `cam_helper.cpp:107-108`, `:123-124` instead, and the text cites neither.
VERIFIER: I could not refute it. The finding holds. In kb/tutorials/inbox/"20261026210000 CINEMATE APERTAR T31 speed-ramping.md", line 34 (§1) says the claim is "settled from the IPA source: `ipa_base.cpp:851`, `:1638-1667@bfe0b76`". The libcamera line in §9 Sources (line 202) instead reads "- libcamera `bfe0b76`: `src/ipa/rpi/cam_helper/cam_helper.cpp:107-108`, `:123-124`.", so it leaves out ipa_base.cpp. Searching the file for "cam_helper" finds only line 202, so no other line in the tutorial cites cam_helper.cpp. The rule in tutorials/README.md:52 says "9 | Sources | Files with commit/release", so the Sources list should name the file the text cites at that commit. The verify3 copy is byte-identical to the export, line 202 included.

I checked the code with `git -C /home/user/tiramisioux/libcamera show bfe0b76:src/ipa/rpi/common/ipa_base.cpp`. Line 851 is `agc->setFixedExposureTime(0, ctrl.second.get<int32_t>() * 1.0us);`, line 1638 is `void IpaBase::applyFrameDurations(Duration minFrameDuration, Duration maxFrameDuration)`, and line 1667 is `agc->setMaxExposureTime(maxExposureTime);`. So the citations on line 34 are correct, and only Sources is wrong.

The cam_helper lines came from the reader report (kb/working/port-raw/r1-ramp-cinemate.md:162, row 39) and never made it into the tutorial text. They are also slightly off: in cam_helper.cpp at bfe0b76, lines 123-124 are only the comment "Limit the exposure to the maximum frame duration requested". The actual re-clip is at lines 127-
FIX (verified): Replace line 202 of kb/tutorials/inbox/"20261026210000 CINEMATE APERTAR T31 speed-ramping.md" (and the identical copy in verify3/tutorials/inbox/) with:
- libcamera `bfe0b76`: `src/ipa/rpi/common/ipa_base.cpp:851`, `:1638-1667`.
No line in the tutorial cites cam_helper.cpp, so drop it. If the author wants to keep it as background, use `src/ipa/rpi/cam_helper/cam_helper.cpp:107-108`, `:127-129` (the re-clip), not `:123-124`, which is only the comment.

### 32. [patches] wrong - src/ApertarCoreApp.cpp (Core; the 25 fps cap patch 0001-camera-cap-4K-Clear-HDR-16-bit-at-25-fps.patch leaves it out) @ maximumPcfFpsForSettings(), IMX585 4K branch, lines 1162-1165 (same on the T31 tree, the T32 tree and tip 3c4f07d); used by availablePcfFpsOptions() :1174-1192, the pot :8630-8637 and the fps / fps_up / fps_down step actions :8891-8897
PROBLEM: The hardware FPS list still goes up to 30 at 4K Clear HDR 16-bit, while Core now clamps that mode to 25. For the IMX585 the list is {24,25,30}. The cycle action "fps" works like this: at 25, nearestPcfPresetIndex gives 1, nextPcfPresetIndex(Cycle) gives 2, so the button sends set_fps 30. The sanitiser clamps that to 25, which equals the current rate, so setFps returns true and nothing changes. Every later press repeats the same steps, so the cycle stays on 25 and never wraps back to 24. Before this patch the sensor probe made 30 reachable on the Pi, so this is a regression. The pot also gets worse: in its top third it sends set_fps 30 on every analog event, because cameraSettings.fps (25) never equals 30. In a take with fps_ramp off, each of those sends is refused with "Stop recording before changing FPS ...", because setFps tests rampingTake before it sanitises. T32 §1 says "All three layers still offer 30", but there is a fourth layer that the patches do not cover.
VERIFIER: I checked the code and could not refute the finding. Core has a fourth FPS ceiling, and the cap patch leaves it at 30.

1. The fourth ceiling. In verify2/home/ApertarCore/src/ApertarCoreApp.cpp:1162-1165, maximumPcfFpsForSettings() reads `if (sensor.find("imx585") ...) { if ((width == 3856 && height == 2180) || (width == 3840 && height == 2160)) return 30.0;`. The same lines appear on t31home and tip-core at 1162-1165. availablePcfFpsOptions() at :1174-1192 filters the IMX585 presets {24,25,30,50,60} against that ceiling, so the list is {24,25,30}. The cap patch 0001-camera-cap-4K-Clear-HDR-16-bit-at-25-fps.patch changes only CameraController.cpp and WebControlPage.cpp, and grep finds 0 hits for a Clear HDR test in ApertarCoreApp.cpp.

2. Core now clamps the mode to 25. CameraController.cpp:2781-2782 reads `if (clearHdr && normalizeRawBitDepth(rawBitDepth) == 16) return 25.0;`.

3. Why the "fps" button gets stuck. The cycle action is at :8891-8897. At 25 fps, nearestPcfPresetIndex returns 1 and Cycle (:1091) gives `(1+1)%3 = 2`, so the button sends set_fps 30. CameraController::setFps (:9074ff) sanitises 30 down to 25. Because `std::abs(settings_.fps - effectiveFps) < 0.0001`, it returns true and nothing changes. Every later press does the same, so the cycle never wraps back to 24. Before the patch, the table returned 30 once the sensor probe was known (`clearHdr && !sensorLimitKnown ? 25.0 : 30.0`), so 30 was reachable and the cycle wrapped. That makes this a regression on t
FIX (verified): 1. Core cap patch (kb/working/patches/0001-camera-cap-4K-Clear-HDR-16-bit-at-25-fps.patch). Add a hunk for src/ApertarCoreApp.cpp that changes lines 1163-1165 in maximumPcfFpsForSettings to:
```cpp
        // Clear HDR 16-bit stops at 25, as in Core's tableMaximumFpsForResolution().
        if ((width == 3856 && height == 2180) ||
            (width == 3840 && height == 2160))
            return settings.clearHdr && settings.rawBitDepth == 16 ? 25.0 : 30.0;
```
Then:
- Add src/ApertarCoreApp.cpp to the diffstat.
- In the 'What:' text, add "maximumPcfFpsForSettings() in ApertarCoreApp.cpp, so the PCF pot and the fps/fps_up/fps_down buttons also end at 25".
- Regenerate the patch with git format-patch on b606c4f+T31 and re-check that it applies with git am on 3c4f07d.

2. T32 tutorial (kb/tutorials/inbox/20261027213000 CINEMATE APERTAR T32 speed-ramp-every-control.md):
- Line 25: "three places: Core, WebUI, touch UI" -> "four places: Core's clamp, Core's PCF list, WebUI, touch UI".
- Line 45: "All three layers" -> "All four layers". Add the table row `| PCF pot and fps / fps_up / fps_down buttons | `ApertarCoreApp.cpp:1162-1165@T31`, `maximumPcfFpsForSettings` | 30 |`.
- Line 39: change `:8623-8630@T31` to `:8630-8637@T31`, and change `:8812-8816@T31` to `:8819-8823@T31` (fps:<n>) plus `:8891-8897@T31` (fps / fps_up / fps_down).
- §3.2: add `grep -n -A3 'if (sensor.find("imx585")' ~/ApertarCore/src/ApertarCoreApp.cpp | head -4   # PCF pot and buttons`. Answer: `return 30.0;`, with no Clear HDR test.
- §4: add a step after 4.1, "4.1b Core: the PCF list, same ceiling — `src/ApertarCoreApp.cpp:1162-1165`, in `maximumPcfFpsForSettings`", with the code block above. Its check is `grep -c 'settings.clearHdr && settings.rawBitDepth == 16 ? 25.0' src/ApertarCoreApp.cpp` -> 1 (it is 0 today on the T32 tree and on tip-core).
- §5.1 (line 478): "comes back in all three" -> "comes back in all four (the PCF fps button cycles 24-25-30 again)". Also add a test: at 4K Clear HDR 16-bit, pressing the PCF `fps` button cycles 24 -> 25 -> 24.
- §8 (line 555): "One ceiling, three copies" -> "One ceiling, four copies (three in Core's repo: the clamp, the PCF list, the WebUI)".

### 33. [patches] minor - kb/tutorials/inbox/20261027213000 CINEMATE APERTAR T32 speed-ramp-every-control.md @ §1, line 39
PROBLEM: The refs are marked @T31 but carry b606c4f line numbers: T31 adds 7 lines above them in ApertarCoreApp.cpp. The second range is also only the `fps:<n>` action, not `fps_up`.
VERIFIER: I confirmed this myself. In the T32 tutorial (export and verify3 copies are identical), line 39 tags its refs `ApertarCoreApp.cpp:8623-8630@T31` and `:8812-8816@T31`. Those are the line numbers at b606c4f, not on the T31 tree. T31 adds 7 lines above this code.

- **Base b606c4f:** grep finds `if (target == "fps") {` at 8623, `parseHardwareActionNumber(action, { "fps" })` at 8812 and `pcfSettingStepMode(action, "fps")` at 8884.
- **T31 tree** (verify2/t31home/ApertarCore/src/ApertarCoreApp.cpp): the same three lines are at 8630, 8819 and 8891. The same numbers hold on the T32 tree.
- **What the wrong numbers point at on T31:** 8623-8630 is the end of the ISO pot block (`if (target == "iso")` starts at 8620; 8623 is `const uint32_t iso = ...`). 8812-8816 is the EV actions (8814 `if (const auto ev = parseHardwareActionNumber(action, {"evm", "ev"}))`).
- **Second range misses `fps_up`:** the text says "`fps:<n>` / `fps_up` buttons", but 8812-8816 (8819-8823 on T31) covers only `fps:<n>`. `fps_up` and `fps_down` go through `pcfSettingStepMode(action, "fps")` (defined at T31:1054, which matches `fps`, `fps_up` and `fps_down`). That block is T31:8891-8897 and it also sends only `set_fps`.
- **The proposed ranges have the same extent as the originals:** pot 8630-8637 runs from `if` to `return;`, `fps:<n>` 8819-8823, and the step block 8891-8897 runs through its closing `}`.
- **Where the mistake came from:** the T31 tutorial (line 80) correctly writes these as `App:8623-8630@b606c4f`
FIX (verified): In kb/tutorials/inbox/20261027213000 CINEMATE APERTAR T32 speed-ramp-every-control.md, line 39, replace

(`ApertarCoreApp.cpp:8623-8630@T31`, `:8812-8816@T31`)

with

(`ApertarCoreApp.cpp:8630-8637@T31` pot, `:8819-8823@T31` `fps:<n>`, `:8891-8897@T31` `fps`/`fps_up`/`fps_down`)

Rewrap the paragraph if needed. The same line numbers hold on the T32 tree. Alternative: keep the old numbers and change both tags to `@b606c4f`, as the T31 tutorial does. That still leaves `fps_up` without a ref, so you would also need to add `:8884-8890@b606c4f`.

### 34. [patches] minor - src/ApertarCoreApp.cpp (T31 patch) @ ApertarCoreApp::startFpsRamp(), lines 9238-9262 (T32 tree); ramp_fps handler :9894-9903
PROBLEM: ramp_fps with seconds > 0 answers ok in a take where every step will be refused. That happens when fps_ramp is off, in an H.264 or ProRes take, or in still mode. The refusal only shows up later in the journal, from the helper thread. The same request with seconds = 0 returns setFps's error. Socket clients (core.py, Cinemate-style scripts) therefore see success for a ramp that never happens. The WebUI greys these cases out, so it is not affected.
VERIFIER: I tried to refute the finding and could not. On the T32 tree (/tmp/claude-0/-home-user-apertar-kb/17fc979d-f346-53ac-97ad-c8caa225a57d/scratchpad/verify2/home/ApertarCore), the T31-only tree has the same line numbers.

- src/ApertarCoreApp.cpp:9246-9252: when `seconds <= 0.0`, startFpsRamp calls `camera_.setFps(targetFps)` and returns `camera_.lastError()` if it fails.
- src/ApertarCoreApp.cpp:9253-9284: when seconds > 0, it sets `fpsRampThreadActive_`, starts `fpsRampThread_` and does `return true;` without checking whether a step can succeed. A refused step only prints `std::cerr << "ApertarCore fps ramp stopped: " << camera_.lastError()` (:9269-9271).
- src/ApertarCoreApp.cpp:9894-9903: the `ramp_fps` handler then sends `okReply(command.id, settingsBody(...))`.
- src/camera/CameraController.cpp:9083-9095: in a take, setFps refuses every change when `!settings_.fpsRampEnabled` ("Stop recording before changing FPS, or enable FPS ramping (set_fps_ramp) for cDNG/MLV takes."). It also refuses when `isProcessedVideoFormat(settings_.recordingFormat) || settings_.photoModeEnabled` ("FPS ramping works in cDNG and MLV takes only."). `isProcessedVideoFormat` (:234-237) is H264 or Prores.
- Still mode can hold a take. `startRecording` (:9792-9830) only refuses still mode when it is long-exposure with a shutter longer than one frame, so all three cases the reviewer named can happen.

So `ramp_fps to=50 seconds=5` in an H.264/ProRes take, a still-mode take, or a take with fps_ramp off g
FIX (verified): 1. In kb/working/patches/0001-camera-speed-ramping-FPS-changes-during-cDNG-MLV-tak.patch (startFpsRamp, ApertarCoreApp.cpp), add these lines right after the closing brace of the `if (seconds <= 0.0) { ... return true; }` block and before `fpsRampStop_.store(false);`. That is after line 9252 in the T31 tree and the T32 tree. Add them to the trees too.

    if (camera_.isRecording()) {
        // Answer the refusal now, as seconds == 0 does, instead of only in the journal from the helper thread.
        const CaptureSettings s = camera_.settings();
        if (!s.fpsRampEnabled) {
            if (error) *error = "Stop recording before changing FPS, or enable FPS ramping (set_fps_ramp) for cDNG/MLV takes.";
            return false;
        }
        if (s.photoModeEnabled || s.recordingFormat == RecordingFormat::H264 || s.recordingFormat == RecordingFormat::Prores) {
            if (error) *error = "FPS ramping works in cDNG and MLV takes only.";
            return false;
        }
    }

   Leave the refusal inside the thread as it is. It still handles a take that ends, or a mode limit, during the ramp.

2. Make the same change in the T31 tutorial's 4.7 text (line 121). After "stop at the first refusal", add: "; in a take, refuse up front with setFps's own two messages when fps_ramp is off or the take is H.264/ProRes/still, so ramp_fps with seconds > 0 answers the same error as seconds = 0". In 5.5 (line 152), add: "`ramp_fps to=50 seconds=5` during an H.264 take: the reply is the error 'FPS ramping works in cDNG and MLV takes only.'"

3. The 11 new lines move everything after :9252 in ApertarCoreApp.cpp down by 11. In the T31 tutorial that means :9238-9285 becomes :9238-9296, :9255 becomes :9266, :9269 becomes :9280, :9287-9297 becomes :9298-9308, :9882-9892 becomes :9893-9903, :9894-9903 becomes :9905-9914, :9900 becomes :9911, :9350 becomes :9361, :9478 becomes :9489, :11107 becomes :11118 and :11268 becomes :11279. Do the same for every T32 ref into ApertarCoreApp.cpp after line 9252. Refs at or before 9252 (:7021, :7127, :7947-7948, :9626, :9240) stay the same. Then rerun tutorials/tutorial.py on both trees. Regenerate the patch with git format-patch from the fixed tree, and check that it still applies with git am on b606c4f and on 3c4f07d.

### 35. [patches] minor - src/ApertarControlBridge.cpp (Apertar-UI, patch 0001-ui-FPS-picker-sends-only-set_fps-during-a-speed-ramp.patch) @ applyFps(), the new early return at line 277 `if (m_recording && m_fpsRamp) return true;`
PROBLEM: m_recording is also true during a sound-only recording. Core's get_state sets "recording" to camera_.isRecording() || soundRecording, and toggleRecording sets it for sound_only. So with fps_ramp on, the picker skips its set_shutter_us and saveCurrentCameraSettings even though no camera take is running. Core then commits the change as a normal FPS change. With Shutter Sync = Exposure it keeps the exposure instead of the angle. That breaks the patch's claim "Outside ramp takes nothing changes". What the UI shows is still Core's reply, so the values on screen are not wrong.
VERIFIER: I confirmed this myself. The reviewer's evidence holds, and the result is a minor behavior change that contradicts "Outside ramp takes nothing changes" (patch message line 17; T32 tutorial line 437).

How it happens:
(1) The touch FPS dropdown is not disabled while recording. qml/CameraPage.qml:2926-2929 onOptionSelected calls controlBridge.applyFps(v), and there is no enabled: guard on it.
(2) m_recording is true during a sound-only recording:
- ApertarControlBridge.cpp:833 setRecordingState(recording) after record_start with sound_only (:818).
- The Core event {"event":"recording","active":true,"sound_only":true} (ApertarCoreApp.cpp:8515) reaches setRecordingState at UI :1229.
- get_state does the same (ApertarCoreApp.cpp:9633 `const bool recording = camera_.isRecording() || soundRecording;` and :9637), via UI :1540.
(3) Core does not treat a sound-only recording as a take:
- CameraController.cpp:9083 `const bool rampingTake = recording_ && ...` looks only at the camera.
- :9118 `applyFpsStepLocked(effectiveFps, rampingTake, /*commit=*/!rampingTake)`, so the change is committed and persisted as a normal FPS change.
- :9127 `const bool keepExposure = next.fpsRampEnabled && next.fpsRampKeepExposure;` does not depend on the take, so with fps_ramp on and Shutter Sync = Exposure, Core keeps the exposure.
(4) When idle, applyFps then sends set_shutter_us with the preserved angle (UI :290-293) and saves it. During a sound-only recording the new early return at UI :277 `if (m_recor
FIX (verified): Apertar-UI patch 0001-ui-FPS-picker-sends-only-set_fps-during-a-speed-ramp.patch, and the same changes in T32 tutorial §4.9:

1) src/ApertarControlBridge.hpp, below the m_fpsRamp line:
    bool m_soundRecording = false; // Core's sound_recording: a sound-only take, the camera is not recording

2) src/ApertarControlBridge.cpp applyCoreState, right after the two fps_ramp lines (:1368-1369):
    if (state.contains(QStringLiteral("sound_recording")))
        m_soundRecording = state.value(QStringLiteral("sound_recording")).toBool(m_soundRecording);

3) src/ApertarControlBridge.cpp applyCoreMessage, recording branch (:1227), right after `applyCoreState(message);`. This is needed because Core's sound-only event sends "sound_only", not "sound_recording":
        if (message.contains(QStringLiteral("sound_only")))
            m_soundRecording = message.value(QStringLiteral("active")).toBool(false)
                               && message.value(QStringLiteral("sound_only")).toBool(false);

4) applyFps, line 277:
    if (m_recording && !m_soundRecording && m_fpsRamp)

The comment above it can say "A ramp step in a camera take (T31) ...".

Tutorial T32:
- §4.9: change "two places ... and one member" to "three places ... and two members", and add blocks 1-3.
- Change the 4.9 applyFps block and the tutor ref to `ref ui src/ApertarControlBridge.cpp 277 if (m_recording && !m_soundRecording && m_fpsRamp)`. The line stays 277 because everything else is added below it or in the .hpp.
- Keep `check 4.9 | grep -c 'm_fpsRamp' ... | ^2$`, since it is still 2.
- Add `check 4.9b | grep -c 'm_soundRecording' /home/pi/ApertarUI/src/ApertarControlBridge.cpp | ^3$`. The 3 lines are the applyCoreState assignment, the event-branch assignment and the applyFps test; block 3's assignment is a single statement split over two lines, and only its first line contains m_soundRecording.
- The applyCoreState line reference changes from `:1368-1369` to `:1368-1371`.
- Patch message: change "Outside ramp takes nothing changes." to "Outside camera ramp takes (including a sound-only recording) nothing changes."

### 36. [docs] wrong - kb/working/handoff-speed-ramp.md + kb/tutorials/inbox/20261027213000 CINEMATE APERTAR T32 speed-ramp-every-control.md @ handoff §3 point 1 line 52; T32 line 224 (4.4 Check), line 406 (4.8 Check), tutor block line 596 (check 4.8)
PROBLEM: The settingsSpeedRamp count is wrong. With 4.4-4.8 applied it is 18, not 17: 8 lines from the HTML, 9 from the 4.5 render code and 1 from the 4.8 listener. On a correct tree the handoff's Pi check, step 4.8's Check and `tutorial.py check T32 4.8` all report a failure.
VERIFIER: Confirmed. On the T32 Core tree and on tip-core, `grep -c settingsSpeedRamp src/web/WebControlPage.cpp` returns 18, not 17. The base b606c4f and the T31-only tree both return 0, so all 18 come from the T32 web patch. The patch also has 18 `+` lines that contain the string. The tutorial's own code blocks add up to 18 as well: 8 in step 4.4 (T32 lines 183-211), 9 in step 4.5 (lines 246, 272, 273, 278, 286, 297, 315, 316, 330) and 1 in step 4.8 (line 401, the `settingsSpeedRampTargetSelect` addEventListener). The tree matches this: 2922-2950 (8), 5071-5140 (9) and 11579 (1). So the handoff Pi check, the step 4.8 Check and `tutorial.py check T32 4.8` (^17$) would all fail on a correct tree. The step 4.4 intermediate value of 8 is right. The export files are byte-identical to the verify3 copies, so both places need the fix.
FIX (verified): Apply the fix in both the export (apertar-kb-speed-ramp-2026-10-27/kb/...) and verify3:
1) working/handoff-speed-ramp.md line 52: change `# T32 WebUI block: 17` to `# T32 WebUI block: 18`.
2) tutorials/inbox/20261027213000 CINEMATE APERTAR T32 speed-ramp-every-control.md line 224: change `→ 8 after this step (17 after 4.8).` to `→ 8 after this step (18 after 4.8).`
3) Same file line 406: change `→ 17.` to `→ 18.`
4) Same file line 596 (tutor block): `check 4.8 | grep -c 'settingsSpeedRamp' /home/pi/ApertarCore/src/web/WebControlPage.cpp | ^18$`

### 37. [docs] wrong - apertar-kb-speed-ramp-2026-10-27.zip (scratchpad) @ r1-core.md and r2-cinemate.md inside the zip
PROBLEM: The zip that HANDOFF-PROMPT tells Patrik to attach is older than the export folder. Its r1-core.md and r2-cinemate.md still carry the cloud-host paths that the folder copies had removed.
VERIFIER: Confirmed. /tmp/claude-0/-home-user-apertar-kb/17fc979d-f346-53ac-97ad-c8caa225a57d/scratchpad/apertar-kb-speed-ramp-2026-10-27.zip was written at 21:39:31.17. kb/working/ramp-ladder/r1-core.md and r2-cinemate.md in the export folder were changed afterwards, at 21:39:56.28 and 21:39:56.29. `find <folder> -newer <zip>` lists only those two files. I unzipped the zip to /tmp/claude-0/-home-user-apertar-kb/17fc979d-f346-53ac-97ad-c8caa225a57d/scratchpad/audit-notes/unzip-docs2 and ran `diff -r` against the folder. Only these two files differ.

r1-core.md in the zip:
- line 4: "Tree: `/home/user/tiramisioux/apertar-core` at `d4ad539`" (folder: "Apertar-Core (cloud branch `clearhdr-fixes`)")
- line 12: "`/home/user/apertar-kb/llm/ui-map.md`" (folder: "`llm/ui-map.md`")
- line 76: "`/home/user/apertar-kb/working/sensor-capabilities.md:51`" (folder: "`working/sensor-capabilities.md:51`")

r2-cinemate.md in the zip, lines 7-11, still list the cloud-host paths `/home/user/tiramisioux/cinemate`, `/home/user/tiramisioux/cinepi-raw`, `/home/user/tiramisioux/cinemate-handbook`, `/home/user/tiramisioux/apertar-core` and `/home/user/apertar-kb`. The folder version uses plain names.

This matters because HANDOFF-PROMPT.md:1 and :3 and INSTALL.md:6 tell Patrik to attach this zip and unzip it. He would get the older copies with the cloud paths in them.
FIX (verified): Rebuild the zip from the current export folder, after the last edit to it, with the same single top-level folder as now: `cd /tmp/claude-0/-home-user-apertar-kb/17fc979d-f346-53ac-97ad-c8caa225a57d/scratchpad && rm apertar-kb-speed-ramp-2026-10-27.zip && zip -r -X apertar-kb-speed-ramp-2026-10-27.zip apertar-kb-speed-ramp-2026-10-27`. To check it, unzip into a new empty folder and run `diff -r <new>/apertar-kb-speed-ramp-2026-10-27 apertar-kb-speed-ramp-2026-10-27`. It must print nothing. Also run `grep -rn '/home/user/' <new>` to confirm no cloud-host paths are left in r1-core.md or r2-cinemate.md.

### 38. [docs] wrong - INSTALL.md (+ kb/working/patches/README.md new section, kb/working/handoff-speed-ramp.md point 0) @ INSTALL.md lines 94-102 'On the Pi afterwards'; patches/README.md last code block
PROBLEM: The Pi `git am` lines read `~/apertar-kb/working/patches/0001-camera-speed-ramping-*.patch` etc. on the Pi. Install step 4 only commits on the Mac, and nothing sends the KB to the Pi, so the patches are not there and `git am` fails. The same applies to T31/T32 §5, which use the Pi's `~/apertar-kb/working/tools/` (the takes.sh regex change). Getting the KB to the Pi is a push (`push pi main`), and the handoff rule says nothing is pushed unless Patrik asks, so the missing step has to be named.
VERIFIER: The finding is partly right. The `git am` lines fail as written. The claim about T31/T32 §5 is wrong.

**Real: the Pi `git am` lines.** INSTALL.md:99-102 under "On the Pi afterwards", and the new block in kb/working/patches/README.md:40-43, run `git -C ~/ApertarCore am ~/apertar-kb/working/patches/0001-camera-speed-ramping-*.patch ...`. Those are Pi paths.
- The five patches are NEW files in this export (INSTALL.md:47-51).
- The export is installed only into the Mac KB. INSTALL.md:87-92 ends at `git commit`, and handoff-speed-ramp.md point 0 (line 41-43) also stops at commit plus the Obsidian move.
- The Pi KB has no remote and gets new files only from the Mac. working/sync.md:78-91: Pi `~/apertar-kb` remote "none", "Sync, always from the Mac ... `git -C ~/Documents/Apertar/apertar-kb pull pi main` / `push pi main`".
- handoff-T26-T30.md:80 says `deploy_to_pi.sh` has not been run since the KB moved on and that the Pi's `~/apertar-kb` is behind.
- No file in the export mentions `push pi`, `pull pi`, `deploy_to_pi` or sync.md (grep of the whole export: no hits).

So on the Pi the globs match nothing and `git am` stops at the first argument because the file does not exist. The handoff rule (handoff-speed-ramp.md:31, "Nothing is pushed unless Patrik asks, and then only from the Mac") means the step has to be named as Patrik's call.

**Wrong: "T31/T32 §5 use the Pi's working/tools/ (the takes.sh regex change)".**
- Neither tutorial calls takes.sh (grep: 0 hits).
- Their Pi command
FIX (verified): 1. In INSTALL.md, add after step 4 (after line 92):

**5. Send the KB to the Pi, only when Patrik says so** (working/sync.md; nothing is pushed without him):
```bash
git -C ~/Documents/Apertar/apertar-kb pull pi main
git -C ~/Documents/Apertar/apertar-kb push pi main
```
The Pi's `~/apertar-kb` is behind and does not have the five new patches.

2. In INSTALL.md, change line 96-97 to begin: "After step 5 (the patches must be in the Pi's `~/apertar-kb`): the handoff's point 1 checks ..."

3. In kb/working/patches/README.md, add one sentence before the code block at line 40: "On the Pi, after the KB is synced from the Mac (`working/sync.md`):"

4. In kb/working/handoff-speed-ramp.md point 0 (line 41-43), add after "commit when he is happy": "If he wants the patches on the Pi, sync the KB when he says so (`working/sync.md`: `pull pi main`, `push pi main` from the Mac)."

5. Do not add the "the tutorials' tools need it" wording, and do not mention takes.sh. T31/T32 §5 use only core.py, which is already on the Pi, so they need no sync.

Alternative to steps 1-3 that needs no KB sync: pipe the patches from the Mac (`git am` reads concatenated format-patch files as an mbox):
```bash
cd ~/Documents/Apertar/apertar-kb/working/patches
cat 0001-camera-speed-ramping-*.patch 0001-camera-cap-4K-*.patch 0001-web-speed-ramp-*.patch | ssh apertar 'git -C ~/ApertarCore am'
cat 0001-ui-4K-*.patch 0001-ui-FPS-picker-*.patch | ssh apertar 'git -C ~/ApertarUI am'
```

### 39. [docs] wrong - kb/tutorials/inbox/20261027213000 CINEMATE APERTAR T32 speed-ramp-every-control.md @ §6 Commit, line 521
PROBLEM: The command is not copy-pasteable. `git add src/camera/CameraController.cpp src/web/WebControlPage.cpp` stages the whole WebControlPage.cpp, including every speed-ramp hunk from 4.4-4.8, into the 'cap' commit. The `git add -p` is only in a comment. Pasted as written, line 523-524's `git add src/web/WebControlPage.cpp; git commit` then fails with 'nothing to commit', and the cap commit carries the whole block.
VERIFIER: Confirmed, and reproduced on a scratch clone. T32 line 521 (§6 Commit) reads `git -C ~/ApertarCore add src/camera/CameraController.cpp src/web/WebControlPage.cpp   # only the 4.1 and 4.2 hunks: git add -p`. The only instruction to use `add -p` is inside a comment, so pasting the line stages the whole of WebControlPage.cpp. This breaks the KB rule at tutorials/README.md:56: "Commands are copy-pasteable, one per line, with a comment saying what each proves."

How I reproduced it: I cloned t31home/ApertarCore (HEAD 5276066, T31 committed) into /tmp/claude-0/-home-user-apertar-kb/17fc979d-f346-53ac-97ad-c8caa225a57d/scratchpad/audit-notes/sim-t32-commit-b/as-written and copied in the final CameraController.cpp and WebControlPage.cpp from verify2/home/ApertarCore. I then ran lines 521-524 as written:
- The "cap" commit came out as `CameraController.cpp | 7`, `WebControlPage.cpp | 156`, `161 insertions(+), 2 deletions(-)`. So it holds the whole speed-ramp block.
- Line 523 `add src/web/WebControlPage.cpp` followed by line 524 `commit` printed `nothing to commit, working tree clean` and exited 1.

Patch 9 (0001-camera-cap-4K-Clear-HDR-16-bit-at-25-fps.patch) touches WebControlPage.cpp only with `3 ++-`, in one hunk (`@@ -4974,8 +4974,9`). Patch 10 adds 153 lines.

The proposed fix works. On the same tree, `git diff` of WebControlPage.cpp has 8 hunks: -2916, -4203, -4974 (4.2), -5020, -8705, -8739, -9997, -11425. The 4.2 hunk is the third, and it stands far enough from its neighbours
FIX (verified): In kb/tutorials/inbox/20261027213000 CINEMATE APERTAR T32 speed-ramp-every-control.md §6, replace line 521:
`git -C ~/ApertarCore add src/camera/CameraController.cpp src/web/WebControlPage.cpp   # only the 4.1 and 4.2 hunks: git add -p`
with these three lines:
`git -C ~/ApertarCore add src/camera/CameraController.cpp                          # 4.1 (whole file)`
`git -C ~/ApertarCore add -p src/web/WebControlPage.cpp                            # 4.2 only: y for the maximumSupportedFpsForSnapshot hunk (3rd of 8, 'return snapshot.clear_hdr ... ? 25.0 : 30.0'), n for every other hunk`
`git -C ~/ApertarCore diff --cached --stat                                         # 2 files changed, 8 insertions(+), 2 deletions(-)`
Leave lines 522-524 as they are. After this change, line 523 stages the remaining 153 lines and line 524 commits them as the web commit.

### 40. [docs] wrong - kb/tutorials/inbox/20261027213000 CINEMATE APERTAR T32 speed-ramp-every-control.md @ §5.4, lines 506-510
PROBLEM: The test cannot fail. Neither Core nor the UI writes incoming or outgoing commands to the journal, so `grep ... set_shutter_us` in the apertar-core journal never matches, with or without step 4.9. The text 'no set_shutter_us from the UI during the take' is therefore unobservable this way.
VERIFIER: The finding is real: the §5.4 test can never fail. In the T32 tutorial (kb/tutorials/inbox/20261027213000 CINEMATE APERTAR T32 speed-ramp-every-control.md), the grep is at line 507 and the claim it is meant to prove is at lines 510-512.

1. Core never writes a command name to the journal.
   - The `set_shutter_us` handler (verify2/home/ApertarCore/src/ApertarCoreApp.cpp:9701-9707) only calls `camera_.setShutterUs` and returns `okReply`/`errorReply`.
   - `CameraController::setShutterUs` (src/camera/CameraController.cpp:9203-9234) has no `std::cerr`.
   - ControlServer.cpp writes only socket errors (socket(), bind(), listen(), accept(), client handler failed).
   - Searching src/ for `cerr`/`cout` lines that mention a command or shutter finds only a tuning-helper error (ApertarCoreApp.cpp:9469) and a still-exposure timeout (CameraController.cpp:8118).
2. The UI writes nothing either. src/ApertarControlBridge.cpp has no qDebug, qInfo, qWarning or cerr, and the grep reads the apertar-core journal anyway.
3. The only matching log line is CameraController.cpp:9149 (`fps ramp: <old> -> <new> fps shutter_us=<policy value> policy=...`), and it is written before the UI's follow-up command arrives. So `set_shutter_us` in the grep never matches, with or without step 4.9 (the UI `m_fpsRamp` early return at ApertarControlBridge.cpp:277).

**The proposed fix is right in substance but the expected text is wrong.** core.py prints Core's raw reply (working/tools/core.py:19, `print(buf.split(b
FIX (verified): In kb/tutorials/inbox/20261027213000 CINEMATE APERTAR T32 speed-ramp-every-control.md:

**1. §5.4, lines 506-508.** Replace the bash block with:

```bash
# during the take, after picking 50 and before picking 25:
python3 -I ~/apertar-kb/working/tools/core.py get_state | grep -oE '"(fps|shutter_us)":[0-9.]+'
# after stop:
journalctl -u apertar-core -b --no-pager | grep -E 'fps ramp: (25 -> 50|50 -> 25)' | tail -2
```

**2. §5.4, line 510.** Replace "What you see: two `fps ramp:` request lines and no `set_shutter_us` from the UI during the take. The shutter readout stays at" with:

"What you see: `"fps":50.000` and `"shutter_us":20000` during the take (without 4.9 the UI's own `set_shutter_us` would leave `10000`), then two `fps ramp:` request lines. The shutter readout stays at"

Lines 511-512 stay as they are. The Angle repeat gives `"shutter_us":10000` either way, so only the Exposure run tests 4.9.

**3. §5.1, line 477.** Change ``What you see: `"fps":25`.`` to ``What you see: `"fps":25.000`.``

### 41. [docs] wrong - kb/tutorials/inbox/20261026210000 CINEMATE APERTAR T31 speed-ramping.md @ step 4.2, line 99: 'called from stopRecording and checkRecordingFailure after the session stopped (`:9815`, `:9840`)'
PROBLEM: Wrong line numbers. On the T31 tree the two restoreFpsAfterRampLocked() calls are at 10085 and 10110. 9815 is the session_->startRecording call and 9840 is a '{' line. §7 (line 184) already gives the right numbers, so the tutorial contradicts itself.
VERIFIER: I could not refute the finding; it is real. In the export tutorial, line 99 (step 4.2) says restoreFpsAfterRampLocked "is called from stopRecording and checkRecordingFailure after the session stopped (`:9815`, `:9840`)". On the T31 tree (verify2/t31home/ApertarCore/src/camera/CameraController.cpp) the calls are elsewhere. Line 10085 is `    restoreFpsAfterRampLocked();` inside stopRecording, which starts at 10075. Line 10110 is the same call inside checkRecordingFailure, which starts at 10094. Line 9815 is `if (!simulateCamera_ && session_ && !session_->startRecording(...` and line 9840 is `{`. Line 184 (§7) correctly says `(:10085, :10110)`, so the tutorial contradicts itself. Cause: 9815 and 9840 are the line numbers on the old cloud branch d4ad539 (/home/user/tiramisioux/apertar-core, where `grep restoreFpsAfterRampLocked` gives 9815 and 9840). The same paragraph has more refs copied from d4ad539 that are wrong on T31 (+270 offset). Each was checked in both files: `applyFpsStepLocked (:8846-8883)` is really 9116-9153. `(:8871-8877)` (the rampingTake log and rampTakeChanged_) is really 9141-9147; T31 9141 is `next.fps = effectiveFps;` and 9147 ends the log line. `(:8879-8882)` (applySettingsLocked plus emit) is really 9149-9152. `restoreFpsAfterRampLocked() (:8887-8904)` is really 9157-9174. `(:8894-8899)` (the re-persist branch) is really 9164-9169. setShutterUs reset `:8953` is really 9223. setShutterAuto `:8963` is really 9233. setFpsRamp reset `(:9466-9467)` is really 9
FIX (verified): In "kb/tutorials/inbox/20261026210000 CINEMATE APERTAR T31 speed-ramping.md", step 4.2 (line 99), change "after the session stopped (`:9815`, `:9840`)" to "after the session stopped (`:10085`, `:10110`)". In the same paragraph, also change these stale d4ad539 numbers to their T31 values: `(:8846-8883)` to `(:9116-9153)`; `(:8871-8877)` to `(:9141-9147)`; `(:8879-8882)` to `(:9149-9152)`; `restoreFpsAfterRampLocked()` (`:8887-8904`) to (`:9157-9174`); `(:8894-8899)` to `(:9164-9169)`; `:8953` to `:9223`; `:8963` to `:9233`; `(:9466-9467)` to `(:9736-9737)`; `:9960` to `:10238`. Leave :9069-9114, :9072-9077, :8980-8986, :9826, :9728-9742 and :9744-9750 as they are. Apply the same edits to the copy in verify3/tutorials/inbox/.

### 42. [docs] wrong - kb/tutorials/inbox/20261027213000 CINEMATE APERTAR T32 speed-ramp-every-control.md @ §1, line 39: `ApertarCoreApp.cpp:8623-8630@T31`, `:8812-8816@T31`
PROBLEM: These are b606c4f line numbers labelled @T31. On the T31 tree, 8623-8629 is the ISO pot and 8812-8816 is ev_up/ev_down. The FPS pot, the `fps:<n>` action and fps_up/down are 7 lines lower.
VERIFIER: Confirmed. The T32 tutorial, §1 bullet 2 (file line 39), cites `ApertarCoreApp.cpp:8623-8630@T31` and `:8812-8816@T31`, but these are base b606c4f line numbers. In base b606c4f:src/ApertarCoreApp.cpp, line 8623 is `if (target == "fps") {` and 8630 is its `return;` (the closing brace is at 8631). Line 8812 is `if (const auto fps = parseHardwareActionNumber(action, { "fps" })) {` and 8884 is `if (const auto mode = pcfSettingStepMode(action, "fps")) {`. The T31 tree (verify2/t31home/ApertarCore/src/ApertarCoreApp.cpp) puts the same code 7 lines lower. 8630 is `if (target == "fps") {`, 8636 `dispatch("set_fps", { { "value", compactNumber(fps) } });` and 8638 `}`. 8819 is `if (const auto fps = parseHardwareActionNumber(action, { "fps" })) {` through 8824 `}`, and 8891 is `if (const auto mode = pcfSettingStepMode(action, "fps")) {` through 8897 `}`. On T31, 8623 is `const uint32_t iso = ...` inside the ISO pot. 8808 is `if (action == "ev_up" || action == "ev_down") {` and 8812-8816 is the ev_up/ev_down tail plus the `evm`/`ev` parse, so neither @T31 range points at FPS code. The T32 tree (verify2/home) gives the same 8630/8819/8891, so the T32 Core patches do not move these lines. The sentence also names the `fps_up` buttons but cites no range for them; the step-mode block is at 8891-8897@T31. The reviewer's proposed numbers are correct, except that the `fps:<n>` block ends at 8824 and the pot block ends at 8638, both of which the proposal already has.
FIX (verified): In kb/tutorials/inbox/20261027213000 CINEMATE APERTAR T32 speed-ramp-every-control.md, line 39, replace `(`ApertarCoreApp.cpp:8623-8630@T31`, `:8812-8816@T31`)` with `(`ApertarCoreApp.cpp:8630-8638@T31` pot, `:8819-8824@T31` `fps:<n>`, `:8891-8897@T31` `fps_up`/`fps_down`)`. If base numbers are wanted instead, the right refs are `:8623-8631@b606c4f`, `:8812-8817@b606c4f` and `:8884-8890@b606c4f`, but the table below it uses @T31, so the @T31 form is the consistent choice.

### 43. [docs] wrong - kb/tutorials/inbox/20261027213000 CINEMATE APERTAR T32 speed-ramp-every-control.md @ §8, line 560: 'Next: the mode ladder (T33).'
PROBLEM: The tutorial ID contradicts the handoff, the project status file, INSTALL and HANDOFF-PROMPT. All of them make T33 the value lists and T34 the mode ladder.
VERIFIER: The finding holds. In the T32 tutorial, line 560 (§8) says "- Next: the mode ladder (T33). Clear HDR 16-bit up to 25, then 4K SDR 12-bit up to a maximum of 50 set in the settings." No other T33/T34 mention is in the T31 or T32 tutorial. Every other file in the export gives the numbers the other way round:
- kb/working/handoff-speed-ramp.md:1 says "then value lists (T33) and the mode ladder (T34)". Line 15 has "| T33 value lists + build `max_fps` |" and line 16 has "| T34 mode ladder |". Lines 68 and 79 say "**2. T33: value lists...**" and "**3. T34: the mode ladder.**".
- kb/working/ramp-ladder/README.md:42 is "### 3.1 T33: value lists (ISO, shutter angle, FPS, WB), Cinemate-style" and :89 is "### 3.2 T34: the mode ladder".
- INSTALL.md:27-28 says "T33, the editable value lists ... and the build's `max_fps=50`; T34, the mode ladder ...".
- HANDOFF-PROMPT.md:11-12 says "2: T33, the value lists and `max_fps=50`; 3: T34, the mode ladder".
So the tutorial's "(T33)" is wrong. It also skips the value-list tutorial, which comes next. That tutorial follows on from the §8 exercise just above it (line 559, adding 12/15/18/20 to both FPS lists). It also brings in the `max_fps=50` that line 560 already refers to.
FIX (verified): In kb/tutorials/inbox/20261027213000 CINEMATE APERTAR T32 speed-ramp-every-control.md, line 560 (§8), replace "- Next: the mode ladder (T33). Clear HDR 16-bit up to 25, then 4K SDR 12-bit up to a maximum of 50 set in the settings. Its" with "- Next: the value lists and the build's `max_fps` (T33), then the mode ladder (T34): Clear HDR 16-bit up to 25, then 4K SDR 12-bit up to a maximum of 50 set in the settings. Its". Leave lines 561-562 ("rows go into this same block. Cinemate's equivalents ... `:3835-3850`).") as they are. Apply the same change to the copy in verify3/tutorials/inbox/ if that copy is kept in sync.

### 44. [docs] wrong - kb/tutorials/inbox/20261026210000 CINEMATE APERTAR T31 speed-ramping.md @ §5, line 142: 'Write down before you look: (1) 50 request lines ...'
PROBLEM: This is a prediction prompt. The working rules forbid prediction questions unless Patrik asks (handoff-T26-T30 §2, handoff-speed-ramp §2, HANDOFF-PROMPT). T32 follows the rule.
VERIFIER: The finding holds up. kb/tutorials/inbox/"20261026210000 CINEMATE APERTAR T31 speed-ramping.md":142 (the same line in the export and in verify3) opens with "Write down before you look: (1) 50 request lines ...". That tells Patrik to write down a prediction before looking, which is the predict-first exercise the working rules forbid. Three places state the rule, and all three apply to this export:
- verify3/working/handoff-T26-T30.md:32 says "**No prediction questions unless he asks for them.**"
- working/handoff-speed-ramp.md:29 (new in this export) says "**No prediction questions** unless he asks."
- HANDOFF-PROMPT.md:17, the text Patrik pastes in himself, says "- No prediction questions."

llm/tutoring.md:30 ("Always ask for a prediction before a command runs") and tutorials/README.md:46 are general KB defaults. The session handoffs override them for Patrik, and the export's own prompt repeats the override, so the T31 wording is a violation. T32 shows the right form: a grep of the T32 tutorial finds no "predict", "write down" or "before you look", and it lists outcomes as expected results. A grep of T31 finds this line as the only predict-first phrasing; the §5.4 MLV question is an open hardware question, not a prediction. The proposed fix is correct. The list itself already gives the expected values, so only the lead-in needs to change. One related spot can optionally change too: verify3/working/ramp-answer.md:87 (new in this export) reads "Predictions to write down before
FIX (verified): In kb/tutorials/inbox/20261026210000 CINEMATE APERTAR T31 speed-ramping.md line 142, replace "Write down before you look: (1) 50 request lines" with "What you should see: (1) 50 request lines" and leave the rest of the line as it is. Optional, for consistency: in kb/working/ramp-answer.md line 87, replace "Predictions to write down before the first test (T31 §5):" with "What to expect in the first test (T31 §5):".

### 45. [docs] wrong - kb/working/ramp-ladder/README.md @ §3.1 lines 62, 74, 84; §3.2 line 136; §4 line 143 (ApertarCoreApp.cpp, T31 tree, identical on the T32 tree)
PROBLEM: Several ApertarCoreApp.cpp line numbers are off. `App:1151-1160` is the d4ad539 number (r1-core) and on cinemate-port lands in the imx294 branch.
VERIFIER: I checked this and the finding holds. kb/working/ramp-ladder/README.md is identical in the export and in verify3. Its §3.1 table labels the Core column "ApertarCoreApp.cpp, T31 tree". Its other Core numbers match the T31 tree: 361-368, 1874, 7262-7289, and availablePcfFpsOptions at 1174-1192. Lines 1-9700 of ApertarCoreApp.cpp are identical in t31home and in the T32 tree, so the same numbers apply to both.

What t31home/ApertarCore/src/ApertarCoreApp.cpp actually has at the cited lines:
- Line 62 cites :1664-1835. Line 1664 is blank and 1835 is blank. `SharedUiSettingsSnapshot readSharedUiSettings()` is at 1665 and its closing `}` is at 1837.
- Line 74 cites :4324. Line 4324 is blank. `std::string defaultHardwareConfigTemplate()` is at 4325.
- Line 136 cites :9607, labelled "T31 tree". Line 9607 is `const auto modes = camera_.sensorModes();`, inside the handler. The handler starts at 9604 with `if (command.name == "list_sensor_modes") {`.
- Line 143 cites presets at :1177-1180. Line 1177 is `const std::string sensor = lowerAscii(sensorName);`. The presets run from 1178 `const std::vector<double> presets =` to 1181 `: std::vector<double>{24.0, 25.0, 30.0, 50.0, 60.0};`.
- Line 84 cites `App:1151-1160`. That range is copied from r1-core.md:397 (Risk 9), which is written against d4ad539. On d4ad539 it is correct: 1151 is the imx585 `if`, through `return 60.0;` at 1160. The README does not say the number belongs to d4ad539, though. On the T31 tree, 1151-1160 falls inside the imx2
FIX (verified): In kb/working/ramp-ladder/README.md:
- Line 62: change `(`:1664-1835`)` to `(`:1665-1837`)`.
- Line 74: change `defaultHardwareConfigTemplate()` `:4324` to `defaultHardwareConfigTemplate()` `:4325`.
- Line 84: change `maximumPcfFpsForSettings` `App:1151-1160` to `maximumPcfFpsForSettings` `App:1162-1171`. On the T31 tree that is the imx585 branch plus the `return 60.0` fallback, inside the function at `:1100-1172`. Alternatively, keep the old range and mark it as d4ad539: `App:1151-1160@d4ad539`.
- Line 136: change `ApertarCoreApp.cpp:9607` to `ApertarCoreApp.cpp:9604`.
- Line 143: change `presets at `:1177-1180`` to `presets at `:1178-1181``.

### 46. [docs] minor - kb/working/ramp-ladder/README.md @ §3.1 table line 48, Touch UI column: `presets` in `availableFpsOptions()` `:809-813`
PROBLEM: The table gives no tree for the touch UI column, so it reads as dc471c1, as in §4. At dc471c1 the presets are at 808-812; 809-813 is the patched tree. §4 line 141 says `:808-812` @dc471c1, so the file contradicts itself.
VERIFIER: Confirmed. kb/working/ramp-ladder/README.md:48 (same text in the export and in verify3/working/ramp-ladder/README.md) gives the touch UI presets as `presets` in `availableFpsOptions()` `:809-813`, and the column header `Touch UI (qml/CameraPage.qml)` names no tree. The file's other touch UI references all point at dc471c1: line 3 names `dc471c1` as the UI base, line 141 says `qml/CameraPage.qml:807-832@dc471c1`, presets at `:808-812`, and line 33 gives `:1557-1558`. At dc471c1 that matches `if (root.controlBridge)` / `return` (the patched tree has them at 1558-1559). In `git show dc471c1:qml/CameraPage.qml`, line 807 is `function availableFpsOptions() {`, line 808 is `var presets = root.imx477Detected` and line 812 is `: [24.000, 25.000, 30.000, 50.000, 60.000])`, so the presets are at 808-812. In the patched tree (verify2/home/ApertarUI/qml/CameraPage.qml), the T32 UI patch adds one comment line at 780 (`// Clear HDR 16-bit stops at 25, ...`). That moves the function to 808 and the presets to 809-813. Line 48 therefore uses the patched numbering while the rest of the file uses dc471c1, so the file contradicts itself.
FIX (verified): In kb/working/ramp-ladder/README.md line 48, change `presets` in `availableFpsOptions()` `:809-813` to `presets` in `availableFpsOptions()` `:808-812@dc471c1`. This matches §4 line 141 and line 33, which both use dc471c1. Do not take the other option of labelling the column 'after T32': line 33 and §4 use dc471c1 numbering, so that label would put the file at odds with itself again.

### 47. [docs] minor - kb/tutorials/inbox/20261027213000 CINEMATE APERTAR T32 speed-ramp-every-control.md @ line 537 (§7 first row)
PROBLEM: Wrong step reference. `node --check` is step 4.10; 4.9 is the touch UI picker.
VERIFIER: I could not refute it. The T32 tutorial (export kb/tutorials/inbox/20261027213000 CINEMATE APERTAR T32 speed-ramp-every-control.md, and the identical copy in verify3) has this at line 537, in the first row of §7: "| WebUI blank, console says `Unexpected token` | a JS typo in 4.5-4.8 | run the 4.9 `node --check`; it names the line in `/tmp/page.js` |". Step 4.9 is not that check. It starts at line 408: "**4.9 Touch UI: the picker leaves the shutter to Core in a ramp take** (Apertar-UI) — two places in `src/ApertarControlBridge.cpp`". The `node --check` comes under step 4.10, whose heading is at line 442 ("**4.10 Host checks before the Pi build**"), and the command itself is at line 449: "node --check /tmp/page.js && echo js ok". The reviewer's location and evidence are correct.
FIX (verified): In kb/tutorials/inbox/20261027213000 CINEMATE APERTAR T32 speed-ramp-every-control.md, line 537, change "run the 4.9 `node --check`; it names the line in `/tmp/page.js`" to "run the 4.10 `node --check`; it names the line in `/tmp/page.js`". Nothing else in that row changes.

### 48. [docs] minor - kb/tutorials/inbox/20261027213000 CINEMATE APERTAR T32 speed-ramp-every-control.md @ line 438 `qml/CameraPage.qml:1557-1558`; line 436 `applyCoreMessage (:1095)`; line 107 `:2918 (the picker)`
PROBLEM: The T32 header says unmarked numbers are on the patched trees. These three are not. The 4.3 patch adds a QML line above 1557 and 2918, and the call site is one line earlier.
VERIFIER: Only one of the three parts holds up: line 107. The other two are wrong, because the reviewer's evidence contradicts itself and misreads the file.

- Line 436, `applyCoreMessage (:1095)`, is correct. In the patched tree, verify2/home/ApertarUI/src/ApertarControlBridge.cpp:1095 is `applyCoreMessage(message);` and 1094 is `const QJsonObject message = doc.object();`. grep gives 1095, plus 1631 for the other call. At dc471c1 the call is at 1088. The reviewer's ":1094" is wrong.
- Line 438, `qml/CameraPage.qml:1557-1558`, is correct on the patched tree. In verify2/home/ApertarUI/qml/CameraPage.qml, 1557 is `function ensureValidFpsSelection() {` and 1558 is `if (root.controlBridge)`, which is the reviewer's own evidence. At dc471c1 the function is at 1556 and the guard at 1557, so the cited numbers are already patched-tree numbers. Nothing needs to change. The reviewer's `:1557-1558@dc471c1` would point to different lines.
- Line 107, `:2918 (the picker)`, is real. The header (line 16) says unmarked numbers are on the patched trees. On the patched tree, `grep -n fpsOptions qml/CameraPage.qml` gives 503, 663, 665 and 2919 (`options: root.fpsOptions`); line 2918 there is `isOpen: root.openDropdown === "fps"`. At dc471c1 the same grep gives 503, 663, 665 and 2918. So 2918 is the dc471c1 number, which is what the reader sees in section 3 ("Run these before the change"). But it has no marker, while the same answer marks `:808-812@dc471c1`. The source list at line 571 already uses the pa
FIX (verified): Only line 107 of kb/tutorials/inbox/20261027213000 CINEMATE APERTAR T32 speed-ramp-every-control.md needs a change. Replace "and `:2918` (the" with "and `:2918@dc471c1` (the". This matches the dc471c1 grep output the reader sees in section 3 and the `:808-812@dc471c1` marker in the same answer. Leave line 436 (`:1095`) and line 438 (`:1557-1558`) as they are, because both are correct on the patched trees.

### 49. [docs] minor - kb/tutorials/inbox/20261026210000 CINEMATE APERTAR T31 speed-ramping.md + T32 @ T31 tutor block lines 230-231 (check 5, check 5.1); T32 tutor block line 598 (check 5.1)
PROBLEM: Three tutor-block checks never run, and one would be refused even if it did. tutor_block() splits on ' | ' and keeps only lines with exactly 3 fields, so these piped commands are silently dropped. T31 check 5.1 also uses `find` (not in SAFE_FIRST) and `2>/dev/null` (a `>`, which tutorials/README.md forbids). T32 check 5.1's regex `"fps":` matches at 30 too, so it does not test the 25 ceiling.
VERIFIER: I checked this myself and it is real. The export copies in apertar-kb-speed-ramp-2026-10-27/kb/tutorials/inbox/ are byte-identical to the ones in verify3.

1. The lines are dropped. tutorials/tutorial.py:121-123 splits each check line on " | " and keeps it only when there are exactly 3 fields. These lines have 4 fields:
   - T31:230 `check 5 | journalctl -u apertar-core -b --no-pager | grep -c 'fps ramp stats:' | ^[1-9][0-9]*$`
   - T31:231 `check 5.1 | find /media -name fps-ramp.txt 2>/dev/null | wc -l | ^[1-9][0-9]*$`
   - T32:598 `check 5.1 | curl -s -m 3 http://127.0.0.1:8000/api/state | grep -o '"fps":[0-9.]*' | "fps":`
   Running tutor_block() on the notes gives T31 steps ['3.1','4.2','4.4','4.2','4.7'] and T32 steps ['3.1','4.1','4.2','4.3','4.5','4.6','4.7','4.8','4.9']. So `tutorial.py check T31 5` and `check T31 5.1` die with "No check for step", and so does `check T32 5.1`. No other check line in the KB has a field count other than 3.

2. Even if parsed, unsafe_reason() would refuse both T31 commands:
   - the journalctl one gives "'journalctl' is not on the read-only list" (SAFE_FIRST, tutorial.py:43-45);
   - the find one gives "contains ; & ` $( > ...", because of `2>/dev/null`. tutorials/README.md:83 also forbids `>` in a check.

3. The T32 regex `"fps":` would pass at any fps value. GET /api/state is buildWebStateJson (ApertarCoreApp.cpp:7248-7251). It writes `,"fps":` << jsonNumber(settings.fps, 3) once (:7966), so the output is `"fps":25.000` or `"fps":30.00
FIX (verified): I tested both new lines through tutor_block() and unsafe_reason(): each parses into 3 fields and is not refused.

1. T32 line 598: replace with
   `check 5.1 | curl -s -m 3 http://127.0.0.1:8000/api/state | "fps":25\.000`
   Optionally, change T32 line 476 "What you see: `"fps":25`" to "What you see: `"fps":25.000`".

2. T31 line 231: replace with
   `check 5.1 | ls /media/RAW/*/fps-ramp.txt | (?m)^/media/RAW/\S+/fps-ramp\.txt$`
   The anchored regex matters: pi_run returns stdout and stderr together. With only `fps-ramp\.txt`, the error "ls: cannot access '/media/RAW/*/fps-ramp.txt'" would also pass. With the anchor, the error line does not match and a real path does.

3. T31 line 230: delete it. journalctl is not on SAFE_FIRST, and no allowed command can read the stats line. The step 5 text (line 142) already has the reader check the journal by hand.

### 50. [docs] minor - kb/tutorials/inbox/20261026210000 CINEMATE APERTAR T31 speed-ramping.md @ §4 steps 4.1-4.7
PROBLEM: KB rule 'One **Check:** per step' (tutorials/README.md, section 4 row) is not met: T31 has no **Check:** line. The tutor block holds checks for 4.2, 4.4 and 4.7, but the note never shows them to Patrik. T32 does it right.
VERIFIER: Confirmed, but the proposed fix gets two counts wrong. The KB rule is at verify3/tutorials/README.md:47: "| 4 | Make the change | ... One **Check:** per step |". In the export, `grep -c '\*\*Check:\*\*'` returns 0 for "kb/tutorials/inbox/20261026210000 CINEMATE APERTAR T31 speed-ramping.md" and 9 for the T32 note. T31 steps 4.1-4.7 (lines 97-121) have no Check line. Its tutor block (lines 226-229) holds checks for 4.2, 4.4 and 4.7, and Patrik never sees them. Both notes are new in this export (untracked in verify3), so the problem comes from this change.

Counts measured on verify2/t31home/ApertarCore (T31 only; verify2/home and tip-core give the same):
- fpsRampEnabled in CameraController.cpp: 11 in total. The lines come from 4.1 (189, 736, 809), 4.2 (9083, 9122, 9731, 9736, 9739), 4.3 (8013) and 4.5 (6470, 8023). Right after 4.2 the count is 8, not 11.
- restoreFpsAfterRampLocked in CameraController.cpp: 4 (8985, 9157, 10085, 10110), all from 4.2. Correct.
- inFpsRampGrace in CameraController.cpp: 3, not 4 as proposed. The definition (8339) comes from 4.4 and the two call sites (7495 stepFramePhaseLock, 8466 trackRecordingCadence) come from 4.5. Right after 4.4 the count is 1.
- ramp_fps in ApertarCoreApp.cpp: 4 (9236 is the comment above startFpsRamp, then 9626, 9894, 9897). Correct. It is 3 if Patrik leaves out the comment.

A second problem follows from this: the tutor-block line `check 4.4 | grep -c 'inFpsRampGrace' ... | ^[3-9]$` FAILS when run right after step 4.4, be
FIX (verified): In "kb/tutorials/inbox/20261026210000 CINEMATE APERTAR T31 speed-ramping.md" §4, add one **Check:** line after each step. The counts are cumulative when the steps are done in order, and they use T32's format:
- after 4.1 (line 97): **Check:** `grep -c 'fpsRamp' include/apertar/core/Types.hpp` → 3.
- after 4.2 (line 99): **Check:** `grep -c 'restoreFpsAfterRampLocked' src/camera/CameraController.cpp` → 4; `grep -c 'fpsRampEnabled' src/camera/CameraController.cpp` → 8 (11 once 4.3 and 4.5 are in).
- after 4.3 (line 101): **Check:** `grep -c 'countOnly' src/camera/CameraController.cpp` → 4.
- after 4.4 (after the paragraph at line 115): **Check:** `grep -c 'inFpsRampGrace' src/camera/CameraController.cpp` → 1 (the definition; 4.5 adds the two callers).
- after 4.5 (line 117): **Check:** `grep -c 'inFpsRampGrace' src/camera/CameraController.cpp` → 3.
- after 4.6 (line 119): **Check:** `grep -c 'timecodeWallClockUs' src/cdng/CdngEncoder.cpp` → 2; `grep -c 'byDuration' src/audio/AudioRecordingSession.cpp` → 2.
- after 4.7 (line 121): **Check:** `grep -c 'ramp_fps' src/ApertarCoreApp.cpp` → 4 (3 without the comment above startFpsRamp).

Also fix the tutor block so it agrees with these lines. Replace line 227 `check 4.4 | grep -c 'inFpsRampGrace' /home/pi/ApertarCore/src/camera/CameraController.cpp | ^[3-9]$` with `check 4.4 | grep -c 'inFpsRampGrace' /home/pi/ApertarCore/src/camera/CameraController.cpp | ^[1-9]$` and `check 4.5 | grep -c 'inFpsRampGrace' /home/pi/ApertarCore/src/camera/CameraController.cpp | ^3$`. You can optionally add matching tutor checks for 4.1, 4.3 and 4.6 (for example `check 4.1 | grep -c 'fpsRamp' /home/pi/ApertarCore/include/apertar/core/Types.hpp | ^3$`). Do not use the reviewer's values "fpsRampEnabled → 11 after 4.2" and "inFpsRampGrace → 4": the first is wrong at that step and the second is wrong on every tree.

### 51. [docs] minor - kb/working/patches/README.md @ new section, line 'Written in a cloud session on top of `cinemate-port` as it is on GitHub: Core `b606c4f`'
PROBLEM: This says GitHub cinemate-port is at b606c4f. The handoff and INSTALL put the GitHub tip at 3c4f07d (b606c4f..3c4f07d = ebdcd08, 3c4f07d).
VERIFIER: The finding is real. kb/working/patches/README.md:24 (identical in the export and in verify3) says: "Written in a cloud session on top of `cinemate-port` as it is on GitHub: Core `b606c4f`, Apertar-UI `dc471c1`." But GitHub cinemate-port is at 3c4f07d. In tip-core (origin github.com/Tiramisioux/apertar-core), `git log b606c4f..3c4f07d` shows two commits on top of b606c4f: ebdcd08 "media/audio: media tuning opt-in..." and 3c4f07d "web: storage label says Media Removed...". The rest of the export uses 3c4f07d as the GitHub tip. working/handoff-speed-ramp.md:11 says "`cinemate-port` on GitHub at `3c4f07d`. The three Core patches ... apply with plain `git am` on `b606c4f` and on `3c4f07d`". INSTALL.md:14-15 says "applies with plain `git am` on Core `b606c4f` and on the current tip `3c4f07d`", and INSTALL.md:105 says "every patch applies in that order on `b606c4f` and `3c4f07d` (Core) and `dc471c1` (UI)". So the README is the only file that calls b606c4f the GitHub state of Core. The UI half is correct, since handoff:12 also puts UI cinemate-port on GitHub at dc471c1.
FIX (verified): In kb/working/patches/README.md line 24, change "Written in a cloud session on top of `cinemate-port` as it is on GitHub: Core `b606c4f`, Apertar-UI `dc471c1`. Each patch applies" to "Written in a cloud session on top of `cinemate-port`: Core `b606c4f` (the three Core patches also apply on the GitHub tip `3c4f07d`), Apertar-UI `dc471c1` (the GitHub tip). Each patch applies". Line 25, "with plain `git am` in this order (checked in the cloud). **Not built on a Pi.**", stays as it is. Make the same edit in the export copy at apertar-kb-speed-ramp-2026-10-27/kb/working/patches/README.md.

### 52. [docs] minor - INSTALL.md @ Files table, line 57: '`working/research-30fps/` (10 `.md` + `q1-pisp-be-sim.cpp`)'
PROBLEM: The folder holds 9 .md files. The count is 10 only if research-30fps-answer.md, which sits outside the folder, is included.
VERIFIER: Confirmed. The row is INSTALL.md:57, '| NEW | `working/research-30fps-answer.md`, `working/research-30fps/` (10 `.md` + `q1-pisp-be-sim.cpp`) | 30 fps research |', in /tmp/claude-0/-home-user-apertar-kb/17fc979d-f346-53ac-97ad-c8caa225a57d/scratchpad/apertar-kb-speed-ramp-2026-10-27/INSTALL.md. Listing /tmp/claude-0/-home-user-apertar-kb/17fc979d-f346-53ac-97ad-c8caa225a57d/scratchpad/apertar-kb-speed-ramp-2026-10-27/kb/working/research-30fps/ shows exactly 9 .md files (README.md, critic.md, q1-backend.md, q2-pipelining.md, q3-bandwidth.md, q4-swap.md, q5-copy.md, q6-link.md, q7-cinemate.md) plus q1-pisp-be-sim.cpp. The overlay in verify3 has the same 10 untracked files (9 .md + .cpp) under working/research-30fps/. working/research-30fps-answer.md is a separate file in working/, not in the folder. The parenthetical comes right after the folder name, so a reader takes it as the folder's contents, and it says 10 where the folder holds 9. Ten is only right if the separately named answer file is counted too. Nothing else in INSTALL.md or HANDOFF-PROMPT.md repeats the count (line 83 names the folder without a number), so only this one line needs the fix.
FIX (verified): INSTALL.md line 57: change '`working/research-30fps/` (10 `.md` + `q1-pisp-be-sim.cpp`)' to '`working/research-30fps/` (9 `.md` + `q1-pisp-be-sim.cpp`)'. Leave the rest of the row as it is.
