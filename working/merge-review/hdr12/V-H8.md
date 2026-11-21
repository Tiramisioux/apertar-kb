# V-H8: skeptic check of H8 (Clear HDR exposure rules differ by depth)

Verdict: **not a cause** of a 12-bit-only "strange output". The rules exist as described (confirmed), but they are
the same at both depths except the cap value, and with Core's defaults the only 12-bit-specific effect is ISO 800 to
720 (0.15 stop). Nothing in them produces a picture that looks strange rather than slightly darker.

## What the code does (all @01f170c unless marked)

| # | Claim | Label | Evidence |
| --- | --- | --- | --- |
| 1 | One rule for both depths: Clear HDR turns auto ISO and auto WB off and sets the `*AfterClearHdr` flags. No bit-depth branch. | confirmed | src/camera/CameraController.cpp:3073-3098 `if (settings.clearHdr) { if (settings.isoAuto) {...} if (settings.whiteBalanceAuto) {...}` |
| 2 | The only depth-dependent part is the cap: `max16 == 1585`, else `max12 = 720`. | confirmed | CameraController.cpp:2936-2939, 3017-3023 `normalizeRawBitDepth(settings.rawBitDepth) == 16 ? limits.max16 : limits.max12` |
| 3 | Values held at the switch are the measured ones (gain to ISO, AWB Kelvin), only when turning Clear HDR on from SDR with auto on. | confirmed | CameraController.cpp:11626-11640 `next.iso = isoForMeasuredGain(gain)` / `next.whiteBalanceKelvin = std::clamp<uint32_t>(wb.kelvin, 1500, 12000)` |
| 4 | Defaults: ISO 800 manual, auto ISO off, shutter auto off, auto WB off. Same on main and upstream. | confirmed | include/apertar/core/Types.hpp:158-173@01f170c; Types.hpp:127-141@main and @upstream-1.6.0 |
| 5 | AE runs only if `isoAuto` or `shutterAuto`. In Clear HDR isoAuto is forced off, so AE runs only with shutter auto on (not default), at both depths. | confirmed | CameraController.cpp:2425 `const bool autoExposure = settings.isoAuto \|\| settings.shutterAuto;`, 2438 `AeEnable` |
| 6 | Turning Clear HDR on keeps the current depth if 16, else 12. From SDR (10 or 12) it lands in 12-bit; the touch UI sends only `set_clear_hdr`. | confirmed | CameraController.cpp:3452-3454 `return bitDepth == 16 ? 16u : 12u;`; Apertar-UI src/ApertarControlBridge.cpp:703-713@7ea9afc |
| 7 | The cap is a `min` and is never undone: going 12 to 16 or back to SDR keeps ISO 720. | confirmed | CameraController.cpp:3084-3085; no restore in 3087-3096 |
| 8 | Fork main had no such rule (no `AfterClearHdr`, no cap); AE/AWB ran in Clear HDR if the user had them on. | confirmed | `grep -n AfterClearHdr\|clearHdrIsoCap src/camera/CameraController.cpp@main` returns nothing |

## Why the symptom does not follow

| Predicted symptom | Check | Result |
| --- | --- | --- |
| "Up to 1.1 stop darker in 12-bit" | log2(1585/720) = 1.14 stop needs ISO above 720 *in Clear HDR 16-bit* and a switch to 12-bit. From SDR at the default ISO 800: log2(800/720) = 0.15 stop. Via the touch UI path (row 6) 12-bit is entered first, so a later 16-bit inherits 720 too (row 7): no depth difference at all. | Darker only, uniform, by a known amount. Visible as the ISO readout (`iso_max` 720 is published, CameraController.cpp:3161-3167). Not "strange". |
| "WB and ISO frozen at last SDR values, cast after a light change" | Row 1: identical at 16-bit. Default WB is manual anyway (row 4). | Cannot explain 12-bit bad / 16-bit fine. |
| "Different shutter than 16-bit for the same scene" | Needs shutter auto on (default off). AeEnable is the same at both depths; only the stats source differs (12-bit software-unwrapped buffer vs 16-bit, which Core's own comment calls invalid, 3069-3070). | If anything 16-bit AE is the less trustworthy one. A shutter difference is an exposure level, not strange output. |

The owner says 16-bit is fine. Every element of H8 except the cap value applies equally to 16-bit, and the cap value
gives at most a uniform darkening that the ISO display shows. H8 cannot carry a 12-bit-only "strange" report.

## Side finding (not H8, belongs with G4-3 / G2-X1)

- confirmed: the cap comment derives 720 from the driver's +12 dB EXP_GAIN (CameraController.cpp:2932-2935;
  imx585.c:174-176@cd548ef, driver default `0x3081 = 0x02` at imx585.c:536), but Core writes `hdrGainAdder = 1`
  (+6 dB) at every Clear HDR start (Types.hpp:206, CameraController.cpp:7076-7084; menu imx585.c:335-336). With
  +6 dB the AppNote window 9.6 <= GAIN+EXP_GAIN <= 29.1 dB gives GAIN 3.6..23.1 dB, i.e. about ISO 150..1430, not
  up to 720. So the 12-bit cap is over-strict, and ISO 100-150 in 12-bit may sit below the merge window. Whether
  that window applies to the CCMP 12-bit mode is unconfirmed. That is a low-ISO merge question for H-G4-3, not H8.
- Fix sketch (style of the surrounding code, optional, only if the owner wants the cap to follow the adder): in
  `clearHdrIsoCap`, for 12-bit return `limits.max12` only when `settings.hdrGainAdder == 2`, else keep the
  configured value but log it; or simply correct the comment to say the cap assumes +12 dB while Core writes +6 dB.
  Host test: none needed for a comment; a cap rule would go in `tools/clear_hdr_iso_cap_test.cpp` with a copy of
  `clearHdrIsoCap` checking (clearHdr, depth, adder) -> cap.

## What remains for the Pi (cheap, rules H8 out completely)

```
# in SDR, note values; then enter 12-bit via the touch UI path and again via set_raw_bit_depth 16
echo '{"command":"get_state"}' | socat - UNIX-CONNECT:/tmp/apertar-core.sock | tr , '\n' \
  | grep -E '"(iso|iso_max|iso_auto|shutter_auto|shutter_us|wb_auto|white_balance_kelvin|raw_bit_depth|iso_auto_after_clear_hdr|wb_auto_after_clear_hdr)"'
```

Expected if H8 is irrelevant to the report: identical iso, shutter_us, kelvin in 12 and 16 (both 720 via the UI
path), shutter_auto false. If the owner's 12-bit still looks strange at the same ISO, shutter and Kelvin as a good
16-bit take, H8 is excluded.
