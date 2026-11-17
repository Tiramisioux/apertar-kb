# V-H4: skeptic pass on "12-bit Clear HDR 1x1 crops return a pedestal or a top OB band Core does not crop"

Refs: driver `cd548ef` (baseline `e5b74d3`), Core `01f170c`. Code read with `git show <ref>:<path>`; nothing edited.

## Verdict

**Survives, but only as a sensor-behaviour question with a low prior. No code defect.** Driver and Core agree
exactly on what a 12-bit Clear HDR crop delivers (active picture, no OB rows). The hypothesis needs the sensor
to emit OB rows or a pedestal in a 12-bit CCMP *windowed 1x1* readout while it does not in the 12-bit CCMP
*full-field* readout. The two readouts are programmed through the same WINMODE crop registers; only the four
window values differ. Nothing in code makes that difference plausible. Nothing on hardware rules it out either:
no 12-bit Clear HDR crop has ever been configured on record.

## Claims

| # | Claim | Label | Evidence |
| --- | --- | --- | --- |
| 1 | Port offers 29 modes in 12-bit Clear HDR: 1080p binned, 4K, and 27 sensor-windowed 1x1 crops (13 aspect, 3 x 1920-wide, 10 x 2048-wide, 1440x1080) | confirmed | `imx585.c:3089-3094@cd548ef` range `[IMX585_MODE_1080P_12BIT, IMX585_MODE_CROP_1440X1080_HDR12]`; enum `imx585.c:858-904@cd548ef` |
| 2 | Baseline offered 4K only in 12-bit Clear HDR, so all 27 crops are new in Clear HDR | confirmed | `git show e5b74d3:imx585.c` get_mode_table: `*mode_list = &supported_modes[10]; /* 4K 12-bit only */`, `*num_modes = 1` |
| 3 | No 12-bit Clear HDR crop was ever configured on the rig | confirmed (KB) | every `camera configured:` line in the KB is 3840x2160/2200 or 1920x1080/1100 (`grep -rIh "camera configured" /home/user/apertar-kb`); journal lines with `1440x1080 clear_hdr` are the probe listing, not a configure |
| 4 | Crop entries are shared by SDR and Clear HDR 12-bit: same `supported_modes[]` rows, same base table `mode_window_12bit_1x1_regs` | confirmed | `imx585.c:660-665`, e.g. 1440x1080 entry `imx585.c:1350-1366@cd548ef` |
| 5 | Windowed 1x1 12-bit programs `PIX_VWIDTH = crop.height`, no OB allowance (only `raw16` adds 20) | confirmed | `imx585.c:2961-2994@cd548ef`: `vst = 12 + mode->crop.top;` ... `if (mode->raw16) sensor_height += IMX585_PIXEL_ARRAY_TOP_4K;` |
| 6 | 4K 12-bit Clear HDR uses the same mechanism: `WINMODE=0x14`, `PIX_VST=12`, `PIX_VWIDTH=2160` | confirmed | `IMX585_WIN_CROP_REGS(12, 2160)` in `mode_4k_regs_12bit`, `imx585.c:610-626@cd548ef` |
| 7 | Core expects no OB rows in H12: transport = active | confirmed | `src/camera/Imx585Modes.hpp:202-208@01f170c` (`if (cls != Class::H16) return { mode.width, mode.height };`); `activeFor` passes non-16 through, `:220-223` |
| 8 | Core's H12 list equals the driver's 12-bit Clear HDR range, size for size (29 rows) | confirmed | `Imx585Modes.hpp:78-87@01f170c` vs claim 1 |
| 9 | Core's OB-row crop is 16-bit only; for a 12-bit crop configured == requested, so no crop is needed | confirmed | `CameraController.cpp:3661` `imx585Clear16 = ... rawBitDepth == 16`, rule `:3659-3676@01f170c` |
| 10 | Sensor in 12-bit CCMP strips OB at the window; HDR-12 4K bench: OB top 0, OB bottom 0 | probable (commit text, bench table, not code) | `git show 728904b` message: `HDR-12 | 3840x2160 | 0 | 0 | scene`; driver comment `imx585.c:582-586@cd548ef` |
| 11 | The "~19 OB rows at the top in ClearHDR" known-issue comment is the 16-bit effect, written before it was explained | probable | `imx585.c:4139-4148@cd548ef`; `git log -S"Known issue: ClearHDR mode leaves"` = `728904b`, the same commit whose bench table shows 0 OB rows for HDR-12 and 20 for HDR-16 |
| 12 | The known pedestal failure (WP-585-8) is windowing *plus 2x2 binning* at RAW16; the 2x2 windowed crops are kept out of 12-bit Clear HDR, the 1x1 ones are not | confirmed | `imx585.c:3065-3086`, `:1016-1017` static_assert, gate README `tools/clearhdr-gate/README.md@cd548ef` |

## Why the hypothesis is weak

- The mechanism it needs (sensor prepends OB because the window does not suppress it) was measured as a
  RAW16 effect: same WINMODE settings give 0 OB rows at HDR-12 and 20 at HDR-16 (claim 10). A 1x1 window
  differs from 4K only in `PIX_HST/PIX_HWIDTH/PIX_VST/PIX_VWIDTH` values (claims 5, 6). If the window
  suppresses OB at `VST=12`, it has no reason to stop at `VST=12+top`.
- The pedestal failure on record needs 2x2 binning; the 27 crops are all 1x1.
- 4K 12-bit Clear HDR was configured 66+ times (`stream=3840x2160 format=RGGB_PISP_COMP1` / `SRGGB16 storage_bits=12`)
  with no top band reported; the KB also records no visual check of 12-bit output after 2026-10-25 (G1),
  so this is absence of a report, not a measurement.

## What is still open (Pi only)

- Whether the owner's "strange output" was in a crop at all. If it was 4K or 1080p, H4 is out.
- Whether the sensor's Clear HDR 1x1 window behaves like the SDR one. No crop of any family has a recorded
  hardware take in the KB (`lessons/hardware-log.md` has no 2880x2160 / 3840x1920 / 2048x1080 hit), and
  `18c1eb2` says G4 (hardware) UNRUN for the 1920/2048 families. So even SDR crops are unproven on record.
- A residual that is not H4 but would give the same "pedestal" look: crops run at `min_vmax = PIX_VWIDTH + 70`
  (`IMX585_CROP_VMAX`, `imx585.c:618`); whether Clear HDR's exposure/SHR limits hold at that short VMAX is
  not checked here.

## Pi test (settles it in one take)

1. `journalctl -u apertar-core | grep 'camera configured'` after selecting the mode the owner used. Crop =
   `raw=` not 3840x2160 / 1920x1080.
2. If a crop: record about 1 s with `set_cdng_compression none` (the script rejects compressed DNGs:
   `pedestal_check.py:81-82@cd548ef`), same scene, plus a 4K 12-bit Clear HDR control take.
3. `python3 tools/clearhdr-gate/pedestal_check.py <crop take> <4K take>` from the driver repo.
   H4 confirmed: verdict `PEDESTAL`, or `top` mean near the black level while `p50` is scene. H4 refuted:
   both `REAL` and `top` close to `p50`.

## Fix sketch

None: no code defect. If the Pi confirms a band, the fix belongs in the driver, the Apertar way, not in Core:
drop the crops from the 12-bit Clear HDR range the same way WP-585-9 did for the 2x2 crops (end the range at
`IMX585_MODE_4K_12BIT`, i.e. `num_modes = IMX585_MODE_4K_12BIT - IMX585_MODE_1080P_12BIT + 1` at
`imx585.c:3091-3094`), and shorten `kH12Modes` (`Imx585Modes.hpp:78-87`) to `{1920,1080,true},{3840,2160,false}`.
Host test: a check in a `tools/imx585_modes_test.cpp` that every `kH12Modes` row satisfies
`transportFor(H12,row) == {row.width,row.height}` and the list matches the driver range size.
