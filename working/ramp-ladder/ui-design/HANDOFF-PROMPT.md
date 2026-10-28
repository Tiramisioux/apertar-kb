# Prompt for Claude in VS Code: the Mode Ladder UI design

Paste the block below into Claude in VS Code.

---

We are building T33 and T34 (the build maximum and the Mode Ladder). I approved the UI design for the Mode Ladder in a
cloud session; it is in the KB on GitHub, branch `cloud/speed-ramp-2026-10-27`, folder `working/ramp-ladder/`. Get it into my
KB clone first (files only, no merge):

```bash
cd ~/Documents/Apertar/apertar-kb
git fetch origin cloud/speed-ramp-2026-10-27
git checkout origin/cloud/speed-ramp-2026-10-27 -- working/ramp-ladder
```

Then read, in this order:
1. `working/ramp-ladder/ui-design/UI-DESIGN.md`: the approved design, my 12 decisions, every text, colour and behaviour.
2. The screenshots in `working/ramp-ladder/ui-design/shots/`. Open them and look:
   - `mockup-00-record-page.png` (the whole Settings > Record page), `mockup-01-mode-ladder.png`, `mockup-02-speed-ramp.png`,
     `mockup-03-activated-sensor-modes.png`, `mockup-03b-sensor-modes-crops-open.png`, `mockup-04-camera-settings.png`:
     the approved mockup. This is the target.
   - `reference-*.png`: a cloud build of the same design, for the states the mockup does not show (recording, locked
     controls, phone width, the FPS switching note, the clamp toast). Its switches are out of date (now Off/On buttons) and so
     is its sensor modes grid (now one column in collapsible groups).
3. The mockup source, `working/ramp-ladder/mockup/Main.dc.html` and `Quick.dc.html`: the `Component` class holds the exact
   rules for legal values (`normalize`, `legal`, `spans`, `setThrAt`), the crop graphic (`cropOf`) and the file sizes
   (`sizeMB`).
4. Only if you need the Core side or a working example: `working/ramp-ladder/build/SPEC.md` (sections 2.5-2.7: commands,
   the `mode_ladder` reply, the state fields) and the reference patches in `working/ramp-ladder/build/patches-on-6ae70b5/`
   (built on Core `6ae70b5` + T31 + T32, not on my current tip, and reviewed: `critique-confirmed.json`, `fix-report.json`).

What I want from you:
- Compare the design with what we have built so far for T33/T34 on my Pi tree and list the differences, screen by screen
  (Settings > Record, Camera settings, Recording format and Favorites locks, touch UI FORMAT row and Settings row).
- Then take me through the changes so the WebUI and the touch UI match the design. Decisions that matter most: Off/On
  buttons instead of toggle switches (Activate ladder, Allow speed ramping, the touch UI's Mode Ladder row); the sensor
  mode tiles in one column, in collapsible groups; "Max (fps)" instead of "Up to"; "Resolution 1, 2, 3"; the running line
  `Resolution 1 · 3840×2160 · ClearHDR16 · ≤25 · Uncompressed`; no illegal values.
- Use the WebUI's own classes and pill buttons, not the mockup's inline styles.
- Ask me before you decide the open point in UI-DESIGN.md (the touch FORMAT row: keep the size or drop it).

Work as my tutor with the apertar-dev rules: I type the changes; no prediction questions; I run sudo, restarts and reboots
(give me the exact commands); builds only on the Pi; nothing is pushed unless I ask.
