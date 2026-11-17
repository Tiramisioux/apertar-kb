# V-H6: skeptic pass on "the 12-bit HG/LG combination window is not tied to what Core writes"

Refs: Core `01f170c` (fork main `f60e301`), driver `cd548ef`, Cinemate `4990afc`, cinepi-raw `63a08d5`,
Cinemate handbook `c99ff77`. Code read in the checkouts at those refs; nothing in the repos edited.
Host check: `/home/user/build/hdr12-numeric/h6_window.cpp` -> `h6_window.out`.

## Verdict

**Refuted as the cause of a 12-bit-only symptom.** Every part of the mechanism is either the same in 16-bit
or better in 12-bit:

- the window is a property of the sensor's built-in combination, which both depths use with the same EXP_GAIN
  and the same GAIN (driver writes one register table for both, differing only in CCMP_EN and MDBIT);
- at Core's defaults (adder 1, ISO 800 capped to 720) 12-bit sits inside the window with 20 gain codes to spare;
- the fixed-WhiteLevel mechanism (merge clamps below declared white, highlights go magenta) is measured by
  Cinemate at **both** depths, and 16-bit (white 65535) is the worse one; in 12-bit, inside the window, the
  measured peak is code 4095, which Core's table maps to exactly its WhiteLevel 65520.

What survives is a **latent Core defect that does not reach the owner's default setup**: the 12-bit ISO cap is
derived for +12 dB while Core writes +6 dB, and it ignores the adder, so adder 3..5 (socket or preset only, no
UI control) puts ISO 720 outside the window. Not a port regression in the sense H6 claims: the adder default is
on fork main, but the ISO cap is **new in the port** (`8175273`).

## Claims

| # | Claim | Label | Evidence |
| --- | --- | --- | --- |
| 1 | Core's default gain adder is menu index 1 | confirmed | `include/apertar/core/Types.hpp:206@01f170c` `uint32_t hdrGainAdder = 1;`; same `Types.hpp:159@f60e301` |
| 2 | Driver menu index 1 = +6 dB; index 2 (+12 dB) is the driver default; 0..5 = 0/6/12/18/24/29.1 dB | confirmed | `imx585.c:335-337@cd548ef` `"+0dB", "+6dB", "+12dB", "+18dB", "+24dB", "+29.1dB"`; `.def = 2` `:3747` |
| 3 | Core writes the adder at every Clear HDR start and on each knob change | confirmed | `CameraController.cpp:7076-7084` (`applyImx585HdrControls`), callers `:7335`, `:11689`, `:12695@01f170c` |
| 4 | What the sensor gets is the cached adder, not the table's 0x02: the Clear HDR table writes `0x3081 = 0x02`, then `__v4l2_ctrl_handler_setup` rewrites EXP_GAIN from the control | confirmed | `imx585.c:536` (table), `:4131` (table write), `:4186` (handler setup), `:3627-3628` (`V4L2_CID_IMX585_HDR_GAIN` -> `IMX585_REG_EXP_GAIN`) `@cd548ef` |
| 5 | 12-bit and 16-bit Clear HDR share one register path: same `common_clearHDR_mode` (WDMODE 0x10, `COMBI_EN` built-in combination, EXP_GAIN), same handler setup; only `CCMP_EN` and `MDBIT` differ | confirmed | `imx585.c:4130-4163@cd548ef`; `:524-526` `/* COMBI_EN: with built-in combination */` |
| 6 | The window `9.6 dB <= GAIN + EXP_GAIN <= 29.1 dB` is stated for "built-in combination", not for CCMP or 12-bit | confirmed (driver comment; AppNote not in the container) | `imx585.c:171-178@cd548ef` |
| 7 | The 12-bit cap comment assumes "+12 dB EXP_GAIN"; Core writes +6 dB. Stale comment | confirmed | `CameraController.cpp:2934-2936@01f170c` vs claim 1 |
| 8 | The cap depends on depth only, not on the adder | confirmed | `CameraController.cpp:3017-3023@01f170c` `return normalizeRawBitDepth(settings.rawBitDepth) == 16 ? limits.max16 : limits.max12;` |
| 9 | The ISO cap is new in the port; fork main has none | confirmed | `git show f60e301:src/camera/CameraController.cpp \| grep -n clearHdrIsoCap` empty; `git log -S"max12 = 720" origin/main..cinemate-port` -> `8175273` |
| 10 | Window per adder (ISO -> code = floor(20 log10(ISO/100)/0.3), Pi-measured 2026-10-28, KB `lessons/hardware-log.md:505-508`): adder 0 codes 32..80 (ISO 302..1585); **adder 1 codes 12..77 (ISO 151..1429)**; adder 2 0..57 (100..716); adder 3 0..37 (100..359); adder 4 0..17 (100..180); adder 5 0..0 | confirmed (arithmetic) | `/home/user/build/hdr12-numeric/h6_window.out` |
| 11 | Default operating point: ISO default 800 (`Types.hpp:158`), capped to 720 = code 57, + 6 dB = 23.1 dB, inside, 6 dB below the top | confirmed (arithmetic + code) | `CameraController.cpp:3084-3085`, claim 10 |
| 12 | The adder has no WebUI or touch-UI control; it is reachable by socket `set_hdr_gain_adder`, a WebUI preset import, or `camera_settings.conf` | confirmed | `ApertarCoreApp.cpp:13167`; WebUI only lists `cameraHdrGainAdder` as a preset key `WebControlPage.cpp:19110`; `grep -rli "gain.adder" Apertar-UI` empty `@7ea9afc` |
| 13 | So "adder 3+ above ISO ~360" needs a manual socket/preset change the owner gave no sign of | probable | claims 10, 12 |
| 14 | 12-bit WhiteLevel = table top = 65520 = `expansionTable()[4095]`; 16-bit WhiteLevel = 65535 fixed | confirmed | `CdngEncoder.cpp:1490-1491`; `ClearHdrCcmp.hpp` `buildExpansion` (`span = 65520 - base`); `cdng/BlackLevel.hpp:22-26@01f170c` |
| 15 | Inside the window Cinemate measured 12-bit peak raw code **4095** at gain codes 20, 40, 51, 60, collapse only at 71 (3188) and 80 (2408) | confirmed (measurement record) | handbook `lessons/hardware-log.md:2532-2544@c99ff77` |
| 16 | So in-window 12-bit highlights reach exactly WhiteLevel 65520: no grey/magenta from the tag | probable (needs claim 15 to hold at 4K on driver cd548ef) | claims 14, 15 |
| 17 | The sub-white clamp that causes magenta was measured in **16-bit** too, at the same adder 1: 54100 (0.83) at code 71, 48600 (0.74) at code 80, "blown sky pink"; Cinemate's `clip_ceiling.hpp` fixed it at both depths (F06 12-bit, F03 16-bit) | confirmed (measurement record) | handbook `hardware-log.md:1893-1924@c99ff77`; `cinepi-raw cinepi/clip_ceiling.hpp:9-35@63a08d5` |
| 18 | The adder does not move the 12-bit ceiling at code 80: adders 1, 2, 3 all 2412, adder 0 1452 (binned HD) | confirmed (measurement record), weak | handbook `hardware-log.md:2434-2445`; weak because the same log records an adder write that "does not reach the driver" (`:518-520`, value stayed 1) |
| 19 | Cinemate's own default adder is also 1; its "+12 dB" in the sweep entry is the driver default, not proven on the sensor | confirmed / probable | `cinemate src/module/app/main/events.py:76` `hdr_cfg.get('gain_adder', 1)`; claim 18 caveat |
| 20 | Below the window: at adder 1, ISO 50..151 (codes 0..11) gives 6.0..9.3 dB < 9.6 dB. Effect unknown; no record anywhere below code 20 | confirmed (arithmetic) / unconfirmed (effect) | claim 10; Cinemate sweep starts at ISO 200 (`hardware-log.md:2536`) |
| 21 | Any lower-bound effect would hit 16-bit at the same ISO (same GAIN, same EXP_GAIN, claim 5), so it cannot explain "16-bit fine" | probable (assumes the AppNote window is not CCMP-specific, claim 6) | claims 5, 6 |

## Why each part of H6 fails as the 12-bit differentiator

| H6 part | Result |
| --- | --- |
| "Core writes +6 dB, cap assumes +12 dB" | True, but +6 dB makes the cap more conservative (upper bound code 77, cap code 57). Measured 4095 at code 60 even at nominal +12 dB. |
| "cap ignores the user-settable adder" | True (claim 8). Only matters for adder 3..5, which has no UI control (claim 12). |
| "WhiteLevel fixed 65520, no measured clamp" | True, and correct whenever the merge reaches 4095 (in window). The same fixed-white problem is larger in 16-bit (65535, measured clamps 0.74-0.89), which the owner reports fine. |
| "12-bit only" | Not supported: same sensor path both depths (claim 5). 16-bit's cap 1585 = code 80 is 0.9 dB *outside* the window at adder 1 (30.0 dB); 12-bit's cap never is at adder 0..2. |
| "below the window, effect unknown" | Unknown, but symmetric in depth (claim 21). |

## Latent defect (provable from code, not the reported symptom)

`clearHdrIsoCap` returns 720 for 12-bit whatever the adder. With adder 3 / 4 / 5 the window top is ISO 359 / 180
/ 100 (claim 10), so ISO 360..720 is outside the documented window. The cap comment also names the wrong EXP_GAIN.

Fix sketch, in the place the port already keeps IMX585 mode facts (`src/camera/Imx585Modes.hpp`, tested by
`tools/imx585_modes_test.cpp`), no new abstraction:

```cpp
// Imx585Modes.hpp
// Clear HDR 12-bit: the sensor merges HG and LG only while GAIN + EXP_GAIN <= 29.1 dB (imx585.c, AppNote
// section 5). EXP_GAIN is the gain adder (0/6/12/18/24/29.1 dB); GAIN is 0.3 dB per code, ISO 100 = code 0.
// The highest ISO whose gain code stays inside, per adder.
inline uint32_t clearHdr12MaxIso(uint32_t gainAdder)
{
    static constexpr uint32_t kMaxIso[6] = { 1585, 1429, 716, 359, 180, 100 };
    return kMaxIso[gainAdder < 6 ? gainAdder : 5];
}
```

```cpp
// CameraController.cpp clearHdrIsoCap, 12-bit branch
if (normalizeRawBitDepth(settings.rawBitDepth) == 16)
    return limits.max16;
return limits.max12 == 0 ? 0 : std::min(limits.max12, imx585::clearHdr12MaxIso(settings.hdrGainAdder));
```

and the comment at `:2934-2936` corrected to "+6 dB (adder 1, Core's default)". `setHdrGainAdder` already goes
through `applySettingsLocked` (`commitHdrKnobsLocked`, `:11681-11685`), so raising the adder re-caps the ISO.
Note: adder 2's exact top is ISO 716 (code 57 is reached at 720 only through the floor mapping); keep 720 from
`apertar-hardware.conf` as the outer bound and the table as the inner one, or use 720 in the table for adder 2.

Host test (add to `tools/imx585_modes_test.cpp`; build `g++ -std=c++20 -I src tools/imx585_modes_test.cpp`):

```cpp
// Every adder's ceiling lands on a gain code inside 9.6..29.1 dB.
const double adderDb[6] = { 0, 6, 12, 18, 24, 29.1 };
for (uint32_t a = 0; a < 6; ++a) {
    const uint32_t iso = im::clearHdr12MaxIso(a);
    const int code = static_cast<int>(std::floor(20.0 * std::log10(iso / 100.0) / 0.3 + 1e-9));
    CHECK(code * 0.3 + adderDb[a] <= 29.1 + 1e-9);
    CHECK((code + 1) * 0.3 + adderDb[a] > 29.1 || code >= 80);
}
CHECK(im::clearHdr12MaxIso(9) == im::clearHdr12MaxIso(5));
```

Severity: low. It only bites after a socket or preset adder change, and Cinemate's one sweep (claim 18) suggests
the adder may not move the ceiling at all.

## What remains for the Pi (cheap; would turn this into a hard no)

1. `printf '{"cmd":"get_state"}\n' | socat - UNIX-CONNECT:/tmp/apertar-core.sock` -> `hdr_gain_adder` 1 and `iso` <= 720
   rules out the upper bound for the owner's take.
2. `v4l2-ctl -d /dev/v4l-subdevN --get-ctrl analogue_gain,hdr_gain_adder_db` while 12-bit Clear HDR streams:
   expect code <= 57, adder 1.
3. One DNG of a blown lamp at 4K 12-bit, ISO 100 and ISO 640, adder 1: `exiftool -WhiteLevel` = 65520 and the
   decoded max (rawpy, through the LinearizationTable) = 65520 means the tag is right in-window. Repeat ISO 100 in
   16-bit: if both depths show the same at ISO 100, the lower bound is not a 12-bit differentiator.
4. Same scene in 16-bit at ISO 640: decoded max well below 65535 confirms the 16-bit clamp (claim 17) and shows the
   owner's "16-bit fine" was not judged on blown highlights.
