# Changes from the two critiques (plan-v1 → design-T34)

2026-10-27, reviser pass. Every critic point below was read against the code where it disagreed with plan v1. Trees: Core
`scratchpad/tip-core` `119d0bb`, Apertar-UI `scratchpad/verify2/home/ApertarUI` `34499f1`, KB `scratchpad/verify3` `8b655da`.
"Checked" = I opened the line or ran the command myself (CONFIRMED). "Where" = the section of `design-T34.md`.

Decision: **accepted** (as proposed), **changed** (the point stands, the fix differs), **rejected**, **deferred** (true, not in T34).

## Code-feasibility critique (`critique-code.md`)

| # | Point | Checked | Decision | Where |
| --- | --- | --- | --- | --- |
| 1 | Size about 1.5x low (900 → 1,250-1,600) | T31 patch: 379 `+` lines in `CC`, 105 in `App` (blank lines included); T32 WebUI 153. The tested header alone is 283 lines | accepted. New estimate ~1,100 for T34, ~1,250 with T33 | §0 item 7, §4 "Size" |
| 1 | Ship as four tutorials | `tutorial.py:98` finds notes by `T\d\d` only, so `T34a` is not found | changed: T33 + one T34 in three parts, each with a build gate; Q12 offers T34/T35/T36 | header table, §5, Q12 |
| 2 | No plan for the compile risk; put logic in a libcamera-free header with a host test | Ran `g++ -fsyntax-only -DAPERTARCORE_HAS_LIBCAMERA=0`: 33 errors, first `CC:6851`. Pattern exists (`FramePhaseLock.hpp` at `CC:1`, `tools/media_profile_test.cpp`) | accepted, and built: `sketch/camera/ModeLadder.hpp` + `sketch/mode_ladder_test.cpp`, 28/28 pass, also compiles with Core's include paths | §3.1, §4 A1-A4 |
| 3 | "Apply, then align" restarts twice and half-fails | `setRecordingFormat` single apply `CC:9379`; `applyCapturePreset` rollbacks `App:10103`, `:10131`, `:10522`, sync `:6991`; `setFpsRamp` controls-only `CC:9746` | accepted: one `ladderRewriteLocked(next)` before each single apply | §1.3 "What never happens", §3.8, §4 A9, A11 |
| 3 | At boot, rewrite before `session_->start` | Sensor family is Unknown before start (`CC:8833`, set at `:6250`); pre-probe a 4K SDR rung reads 30 | rejected; post-start guard kept (rare) | §4 A11, §7.3 |
| 3 | Call the rewrite in the App's `apply_preset` | `apply_preset` fields `App:10871-10898`; presets carry no `clear_hdr` | changed: refuse a Favorite that names another mode (operator 8); rewrite an FPS-only Favorite; never inside `applyCapturePreset` | §3.5, §3.7, §4 A12, A17, Q10 |
| 3 | `setStillExposureMode` missing | `CC:9283`, `:9294` | accepted (also Missing 3) | §4 A11 |
| 4 | PCF pot jumps at record start when `fps_max` shrinks | `App:8607-8613`, `:8682-8690`, `GAI:473` | changed: two fields. `fps_max` (off-take value, stable in takes) for the pot and `fps_up/down`; `fps_take_max` for the pickers in a take. No new settings events | §3.6, §4 0.11, B7, C6 |
| 5 | Touch UI: five mode controls live; the picker freezes; display uses the requested FPS | `QML:1217`, `:1242-1250`, `SP:636`, `SP:3179-3188`, `SP:3264`; `CB:1084`; `QML:2926-2929`; `CB:280`, `:288` | accepted: greyed + caption + warnings, accepted FPS from the reply. Freeze documented, not fixed (same as `set_clear_hdr` today) | §1.1, §4 C3, C7, C9, R9 |
| 6 | Raw-pool risk already fixed; the real risk is the silent cached-heap fallback | `recorder_.clearRawPool()` `CC:7294`; heaps `CC:7392-7414`; "too slow" `CC:7297-7298` | accepted: F13, R5, M8 | §2.1, §6 M8, §7.1 |
| 6 | Optional fallback counter in `get_state` | | deferred until M8 | §2.4, §7.3 |
| 7 | 50 fps may be back-end bound; M3 too short | `Q2P:125-127`; buffers `CC:1063`, `:1181-1188`; `HL:380-386` | accepted: M3 = 180 s, drive fill, PCIe gen, `APERTAR_RAW_CAMERA_BUFFERS=8` retry, prediction "unknown" | §2.1 F10, §6 M0, M3 |
| 8 | `notice` field races with the stepper | stepper calls `setFps` without the command lock (`App:9321` vs `:9532`) | accepted: dropped. The WebUI compares requested and accepted FPS | §3.7, §4 B8 |
| 9 | `# mode=` line only in ramped takes | `if (events.empty()) return;` `CC:8424` | accepted: dropped | §2.3 |
| 10 | Validation rules twice (C++ and JS) | | accepted: Core only, `set_mode_ladder … dry_run=true` | §3.5, §4 B5 |
| 11 | Ramp-ready as an FPS value is too much state | | accepted: a boolean, reach = the ladder top; placed in the Speed Ramp block (operator 6) | §3.2, §3.4 |
| 12 | M1 times the wrong switch and hides the profile cost | log preview builds two CameraManagers `CC:6222-6237` | accepted: three transitions, round trip subtracted, profile printed, run with Standard and the usual profile, lower bound | §6 M1 |
| 13 | `;` in the rung text ends the shell command | `tools/core.py:6-8` JSON-quotes strings; `CP:62-118` reads a quoted string whole | accepted: `,` between rungs | §3.4 |
| M1 | Host test for chooser and parser | | accepted (built) | §3.1 |
| M2 | Soak test M8 | | accepted | §6 M8 |
| M3 | Re-align when leaving photo mode | `CC:9283-9294` | accepted | §4 A11 |
| M4 | Probe off → empty pool; fall back to Core's own list | `CC:10191-10195` | changed: no second list; the editor says "Sensor probe off"; rungs still validate | §3.5, §7.3 |
| M5 | `max_fps=50` also caps HD, crops, H.264 | `CC:2786-2790` | accepted: T33 says it | §4 Part 0 note, R6 |
| M6 | Tutorial numbers clash | T32 line 560; README §3.1 | accepted | header table, Q12 |
| M7 | PCF resolution pot spams "Hardware input action failed" | `App:8631-8639`, `:8692-8700` | accepted: skip when `ladderActive` | §4 A16 |
| M8 | `atomicWrite` fsync under the controller lock | `SF:36-58` | rejected: the same call holds the lock for a reconfigure; Save only | §3.4, §7.3 |
| M9 | No way to turn the ladder off on the camera | | accepted: two touch Settings rows | §1.1, §4 C4, C8 |
| Verdict | Drop B0 | | accepted | §2.3 |

## Operator and post-production critique (`critique-operator.md`)

| # | Point | Checked | Decision | Where |
| --- | --- | --- | --- | --- |
| 1 | Ramp-ready armed by `fps_ramp`, which stays on: every take silently SDR 12-bit | `fps_ramp` persisted per profile `CC:735`, `:809`; T31 line 19 "every fps control ramps" | accepted: own switch, default Off; R needs Ramp-ready **and** Speed Ramp | §0 item 3, §3.2 |
| 1 | Default one-shot | | changed: sticky by default, Q9 asks. One-shot adds a reconfigure (135 MB reallocation) after every ramp take | Q9, §7.3 |
| 2 | Touch screen never shows the class; "R1/2" is a number | `QML:519-526`, `:3606-3610`; class only in the quick menu `QML:3235` | accepted: `HDR16 · ≤25 · Uncompressed`, `SDR12 · ≤50 · RAMP` amber; WebUI line; WebUI pills tinted | §1.1, §4 B8, C5 |
| 2 | Tint the touch picker entries | `QML:2919` options are strings | deferred | §7.3 |
| 3 | "No frames lost" excludes storage drops; ramp numbering hides them | `CC:8018`; `HL:317-321`, `:380-386` | accepted: said in §0/§1.2; M0/M3 at shoot-day fill; `max_fps` = what held | §1.2, §6 |
| 3(c) | Check the dropped flag; add counters to `fps-ramp.txt` | queue-full sets the flag `CC:3911-3912`; touch UI shows it `QML:2593`; counters printed at stop `CC:3678` | flag: confirmed, no code. `fps-ramp.txt` line: rejected (session code, ramped takes only) | §1.2, §7.3 |
| 4 | T31/T32 never ran on the Pi; M0 first | README §2 lines 37-38 | accepted: M0 before any T34 code | §0 item 8, §6 M0, R3 |
| 5 | Pot changes meaning at record start | same as code 4 | accepted (merged) | §3.6 |
| 6 | Two controls hold the ramp's top; the T32 select falls back silently | `Web:4238`, `:5124-5131` | accepted: one Ramp-ready switch in the Speed Ramp block, no reach select; a text line in a take instead of a disabled select entry | §1.1, §4 B2, B10 |
| 7 | "Lossy rung 2: design unchanged" is wrong | `RC:76-78`; `CC:4200-4201` | accepted: corrected | §2.4 |
| 8 | Presets silently overridden | `CC:10231-10257`; fields `App:10871-10898` | accepted: refuse mode-naming Favorites; Q10 | §3.7, §4 A17 |
| 9 | Touch mode controls fail silently | same as code 5 | accepted (merged) | §4 C7 |
| 10 | Redraw rule contradicts itself; focus lost each second | poll `Web:11800` | accepted: rows redraw only on fetch, save, revert, local edits; never on the poll | §4 Part B note |
| 10 | "Changed elsewhere" message | | rejected: the ladder is not in the poll; one operator | §7.3 |
| 11 | In-take cap must be the rung's ceiling | | accepted: one number per rung; Q3 default threshold | §3.2, §4 A9 |
| 12 | Lowest FPS: steps land seconds late | grace `CC:8313-8331`; stepper `App:9290-9334` | accepted: M5 records `lag_frames` at 2, 5, 12; Q6 | §6 M5 |
| 13 | Logic out of `CC`, host test of the `ff59dd8` invariant | | accepted (built; invariant test included) | §3.1 |
| 14 | A alone gives a ramp take the wrong base rate | RA §3 row 5 | accepted: row in the comparison | §2.2 |
| 15 | B ends the shot in the other look | plan §1.5 "never switches back down" | accepted: row in the comparison | §2.2 |
| 16 | Hysteresis at the boundary | `GAI:427`, `:473` | deferred (settle delay only if M1 is long) | §2.4, R11 |
| 17 | M6 compares grade, not exposure | ISO → gain the same in both classes `CC:2141-2143` | accepted: grey-card level and clip point | §6 M6 |
| M1 | M0 | | accepted | §6 |
| M2 | On-set sheet | | accepted | §1.2 |
| M3 | What "ladder off" leaves | | accepted: camera stays in the last rung; both UIs say so | §1.2 C |
| M4 | Arming from the camera body | | changed: touch Settings rows (Ladder, Ramp-ready); PCF action deferred | §4 C8, §7.3 |
| M5 | HDMI monitor shows no class | | deferred | R12 |
| M6 | "Where each setting lives" table | | accepted | §3.3 |
| M7 | Measurement hygiene | | accepted (M1 round trip, M3 drive fill, M5 latency, M7 ISO/WB from DNGs) | §6 |
| M8 | One-shot needs a re-align after the drain | | only if Q9 = one take | Q9 |
| M9 | Name the Cinemate lesson | | accepted | §5 §2 |
| M10 | Optimistic patch shows stale class during a switch | `Web:9302` | accepted: "Switching to 4K SDR 12-bit…" until the reply; optimistic `ladder_*` for `set_mode_ladder` | §4 B8, B10 |
| Dropped | Per-rung "Enabled" box | | accepted: Remove + the pool | §3.1 |
| Dropped | Five of seven `ladder_*` fields | | changed: five fields in all (`fps_max`, `fps_take_max`, `ladder_active`, `ladder_rung`, `ladder_ramp_ready`); no `ladder_class` (the UIs build it from `clear_hdr` + `raw_bit_depth`) | §3.6 |
| Q9-Q11 | New questions | | accepted | §7.2 |

## Where the critics disagreed with each other

| Topic | Code critic | Operator critic | Design |
| --- | --- | --- | --- |
| `fps_max` in a take | keep it the ladder ceiling for everyone | pot list stable, pickers may keep the in-take cut | two fields: `fps_max` stable, `fps_take_max` for pickers in a take |
| Presets | rewrite them before the apply | never rewrite silently | refuse mode-naming Favorites, rewrite FPS-only ones |
| Ramp-ready location | checkbox in the ladder card | switch in the Speed Ramp block | Speed Ramp block |
| Ramp-ready default | (none) | one take only | sticky, Q9 |
| `# mode=` header | drop | (keeps §1.6 as correct) | dropped; the DNG tags carry bit depth and black level |
