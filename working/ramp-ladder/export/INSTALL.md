# KB export: speed ramping on cinemate-port, 30 fps research, project status (cloud session, 2026-10-26/27)

Files only: no commits, nothing pushed. `kb/` mirrors the knowledge base, so every file sits at the path it should have in
`apertar-kb`. Base: GitHub `Tiramisioux/apertar-kb` `main` at `7886e5b` (T22-T30 moved to Obsidian).

**For VS Code:** paste `HANDOFF-PROMPT.md` (next to this file) and attach the zip. It points the session at
`kb/working/handoff-speed-ramp.md`.

**This export replaces `apertar-kb-additions-2026-10-27.zip`.** Do not use that one: it was built on `bd334eb`, it would put
T27-T30 back into `tutorials/inbox/`, and its T31 patch targets the cloud branch, not `cinemate-port`.

## What is in it

1. **T31 speed ramping, moved to `cinemate-port`.** The patch applies with plain `git am` on Core `b606c4f` and on the
   current tip `3c4f07d`. Neither T31 nor T32 is on GitHub `cinemate-port` yet. The tutorial's line
   numbers are on that tree with the patch applied. Three steps differ from the cloud version because of the port; the status
   line names them. Step 4.7 is also new: in a take, `ramp_fps` refuses up front with `set_fps`'s own errors (`fps_ramp` off;
   H.264, ProRes or still mode) instead of answering ok.
2. **T32 speed ramping from every control** (new). Four parts:
   - the Cinemate-style Speed Ramp block in the WebUI (Settings → Record → Recording format, under Bit Depth);
   - the touch UI FPS picker, which now leaves the shutter to Core in a camera ramp take (not in a sound-only take);
   - 25 fps as the ceiling for 4K Clear HDR 16-bit in Core (its clamp and its list for the PCF pot and `fps` buttons), the
     WebUI and the touch UI;
   - three Core patches in order (T31, then two for T32) and two UI patches on Apertar-UI `dc471c1`.
3. **30 fps Clear HDR 16-bit research.** The answer with ranked experiments, seven reader reports, the critic, `be_cycle.py` and
   the PiSP back-end simulation.
4. **Handoff** (`working/handoff-speed-ramp.md`): where things stand, the rules, and the points in order for the next session.
5. **Project status** (`working/ramp-ladder/README.md`). Your requirements from 2026-10-27 in order, what is done, and the
   decisions so far for the two parts that are **not built**:
   - T33, the editable value lists (ISO, shutter angle, FPS, WB) and the build's `max_fps=50`;
   - T34, the mode ladder with drag and drop, optional thresholds and a toggle.

   Also in that folder: the two reader reports for the ladder. `working/ramp-mode-ladder.md` is the first assessment.
6. **Mode-ladder design** (`working/ramp-ladder/design/design-T34.md`), planned, critiqued from the code and the operator side,
   and revised. It recommends A + R:
   - rungs change between takes only;
   - an opt-in Ramp-ready switch starts a ramp take in the top rung, so 20 → 50 → 20 stays in one mode;
   - B, switching mid-take with a clip split, is deferred until the Pi has measured it.

   It also has the measurements to make first, the data model and commands, a file-by-file plan, a T34 tutorial outline, and
   open questions Q1-Q12. `sketch/` holds the ladder logic as a header without libcamera, with a host test (28 checks pass).
   Mockup of the editor: https://claude.ai/artifact/YKbhhk8aMUS8sxEWa6UfRL (private).

Left out on purpose: the T27-T30 reference-patch corrections from the earlier export. `cinemate-port` already has T27-T30 with
its own fixes, including `8f7dc39` for the T27 build error.

## Files

NEW = not in the KB yet. REPLACES = the file at `7886e5b` plus the lines listed.

| Status | Path | Change |
| --- | --- | --- |
| REPLACES | `llm/tutoring.md` | +2 rows: T31, T32 |
| REPLACES | `tutorials/README.md` | +2 rows: T31, T32 |
| REPLACES | `working/patches/README.md` | +26 lines: "Speed-ramp series" table (patches 8-12) and the Pi's `git am` lines |
| REPLACES | `working/tools/takes.sh` | stats regex also prints `changes= base_fps= min_fps= max_fps=` |
| NEW | `tutorials/inbox/20261026210000 CINEMATE APERTAR T31 speed-ramping.md` | T31 on `cinemate-port` |
| NEW | `tutorials/inbox/20261027213000 CINEMATE APERTAR T32 speed-ramp-every-control.md` | T32 |
| NEW | `working/patches/0001-camera-speed-ramping-FPS-changes-during-cDNG-MLV-tak.patch` | Core, T31 |
| NEW | `working/patches/0001-camera-cap-4K-Clear-HDR-16-bit-at-25-fps.patch` | Core, T32 |
| NEW | `working/patches/0001-web-speed-ramp-block-in-the-Recording-format-card.patch` | Core, T32 |
| NEW | `working/patches/0001-ui-4K-Clear-HDR-16-bit-offers-FPS-up-to-25.patch` | UI, T32 |
| NEW | `working/patches/0001-ui-FPS-picker-sends-only-set_fps-during-a-speed-ramp.patch` | UI, T32 |
| NEW | `working/ramp-answer.md` | the speed-ramping answer (cites the cloud commit; a note says so) |
| NEW | `working/port-raw/r1-ramp-cinemate.md`, `r2-ramp-core.md`, `critic-ramp.md` | T31 evidence |
| NEW | `working/handoff-speed-ramp.md` | handoff for the next session (VS Code) |
| NEW | `working/ramp-ladder/README.md`, `r1-core.md`, `r2-cinemate.md` | project status and the ladder reader reports |
| NEW | `working/ramp-ladder/design/` (`design-T34.md`, `changes-from-critique.md`, `plan-v1.md`, `critique-code.md`, `critique-operator.md`, `sketch/camera/ModeLadder.hpp`, `sketch/mode_ladder_test.cpp`) | the mode-ladder design (A + R) and its host-tested sketch |
| NEW | `working/ramp-mode-ladder.md` | first mode-ladder assessment |
| NEW | `working/research-30fps-answer.md`, `working/research-30fps/` (9 `.md` + `q1-pisp-be-sim.cpp`) | 30 fps research |
| NEW | `working/tools/be_cycle.py` | back-end cycle split S1-S4 |

## Install on the Mac

**1. Check that the four replaced files have not changed since `7886e5b`.**

```bash
cd ~/Documents/Apertar/apertar-kb
git diff --stat 7886e5b -- llm/tutoring.md tutorials/README.md working/patches/README.md working/tools/takes.sh
```

No output: safe to overwrite. A file is listed: do not overwrite it; add the lines from the table by hand (row text is in the
exported file).

**2. Copy.** The trailing `/.` copies the contents of `kb/`.

```bash
cp -R ~/Downloads/apertar-kb-speed-ramp-2026-10-27/kb/. ~/Documents/Apertar/apertar-kb/
chmod +x ~/Documents/Apertar/apertar-kb/working/tools/be_cycle.py
```

**3. Look.**

```bash
git status --short       # 4 modified; new: 2 tutorials, 5 patches, handoff-speed-ramp.md, ramp-answer.md, ramp-mode-ladder.md,
                         # research-30fps-answer.md, be_cycle.py, 3 port-raw files, and the folders ramp-ladder/ and research-30fps/
git diff --stat          # small additions only (+2, +2, +26, +1/-1)
```

**4. Commit when you are happy**, then move the two inbox notes into Obsidian as usual (copy, then `git rm` the inbox copy):

```bash
git add -A llm tutorials working
git commit -m "kb: T31 on cinemate-port, T32 speed ramping from every control, 30 fps Clear HDR research, speed-ramp status and handoff"
```

**5. Send the KB to the Pi, only when Patrik says so** (`working/sync.md`; nothing is pushed without him):

```bash
git -C ~/Documents/Apertar/apertar-kb pull pi main
git -C ~/Documents/Apertar/apertar-kb push pi main
```

The Pi's `~/apertar-kb` is behind and does not have the five new patches until then.

## On the Pi afterwards

After step 5 (the patches must be in the Pi's `~/apertar-kb`): the handoff's point 1 checks whether T31 and T32 are on the
Pi, then goes through what is missing. The patches are the reference (Core on `b606c4f` or `3c4f07d`, UI on `dc471c1`):

```bash
git -C ~/ApertarCore am ~/apertar-kb/working/patches/0001-camera-speed-ramping-*.patch ~/apertar-kb/working/patches/0001-camera-cap-4K-*.patch ~/apertar-kb/working/patches/0001-web-speed-ramp-*.patch
git -C ~/ApertarUI am ~/apertar-kb/working/patches/0001-ui-4K-*.patch ~/apertar-kb/working/patches/0001-ui-FPS-picker-*.patch
```

Checked in the cloud, not on a Pi:
- every patch applies in that order on `b606c4f` and `3c4f07d` (Core) and `dc471c1` (UI);
- host `g++ -fsyntax-only` passes for the Core files that do not need libcamera;
- `node --check` passes for the WebUI script, and the WebUI block was driven in Chromium against a mocked state;
- the whole touch UI builds with Qt 6.4.2.

`CameraController.cpp` was not compiled (libcamera).
