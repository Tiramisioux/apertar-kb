# Q1: PiSP back-end cost per frame, Clear HDR 16-bit 3840x2200 at 30 fps

Reader: Q1 back end (research subagent, Claude Opus 5.5) · trees: libcamera-apertar `6b0b49f` (base libcamera-qbc `7e9fef0`),
libpisp `v1.3.0` (`9ba67e6`), kernel-rpi `rpi-6.12.y` `5bd564a`, imx585-apertar `98b9862`, apertar-core `f60e301` · date 2026-10-26

Labels: **CONFIRMED** = I opened the line or page, or ran the code. **PROBABLE** = derived, with the reasoning shown.
**UNCONFIRMED** = needs the Pi or a source I could not open. Citations: `repo/path:line@commit`.

Simulation used in this report: libpisp v1.3.0's own `BackEnd::Prepare()` and tiler, built on the cloud host from a scratch copy of
the tree (no Pi, nothing built in the source trees) and driven with the configuration that `configureBe()` and the IPA produce for this
mode. Source: `working/research-30fps/q1-pisp-be-sim.cpp`. Build: copy `libpisp/src` and compile `backend/*.cpp backend/tiling/*.cpp
common/pisp_{utils,logging,pwl}.cpp variants/variant.cpp` with nlohmann/json 3.11.3, `-DPISP_LOGGING_ENABLE=0`, and run it with
`LIBPISP_BE_CONFIG_FILE=<libpisp>/src/libpisp/backend/backend_default_config.json`. Its numbers are **CONFIRMED for libpisp v1.3.0**. They
apply to the Pi only if the Pi's libpisp is the same version (**UNCONFIRMED**, see experiment X0).

## Short answer

1. **What the BE does (CONFIRMED, code and simulation).** For each frame the BE reads the whole 16-bit unpacked raw (3840x2200,
   stride 7680) in **10 vertical tiles of 408-432 px x 2192 rows**. It runs DPC, GEQ, **TDN**, SDN, BLC, WBG, CDN, LSC and demosaic, then
   CCM, YCbCr and inverse, false colour, sharpen, gamma, CSC1, and downscale + resample to **one** output (output 1: 1280x720 YUV420).
   Stitch, CAC, tonemap, debin and output 0 are off. The BE has no statistics output.
2. **TDN is on, and it is the expensive part (CONFIRMED).** Denoise defaults to `ColourHighQuality` and imx585.json has `tdn` blocks.
   libcamera forces the CFE format to unpacked 16-bit for this mode and gives the TDN nodes that same format. So the TDN reference is a
   **16-bit, uncompressed, full-frame Bayer image, read and written every frame**. In 8-bit-compressed modes this traffic is half as
   large.
3. **Bytes per frame (CONFIRMED for v1.3.0 tiling; TDN write width PROBABLE).** Raw read 18.73 MB + TDN read 18.73 + TDN write 18.73 +
   output 1.38 = **57.6 MB/frame = 1.73 GB/s at 30 fps** (lower bound 53.8 MB = 1.61 GB/s). TDN is 65 % of that. The BE is probably the
   largest single pass in the frame budget, larger than the endian swap (33.8 MB) or Core's copy (33.8 MB).
4. **Rate (PROBABLE).** The idle start->done of 13.4 ms is 40 % of 33.3 ms. It implies at least 0.70 Gpix/s and 4.3 GB/s while the BE
   runs. On its own, the BE exceeds the frame period only if recording slows it by about 2.2-2.5x or more. The CPU passes slowed 1.44-1.62x. So the
   BE alone does not explain the loss unless contention hits it much harder than the CPU (its AXI QoS is 0). One ftrace window (X1)
   settles this.
5. **Cheapest lever (PROBABLE).** Turn **TDN off for the preview**. The raw and the DNG are untouched, because the BE only reads the raw
   buffer. Two ways: a tuning-file copy without `tdn` (no rebuild), or `NoiseReductionMode=Off` from Core. Either removes **37.6
   MB/frame (1.13 GB/s)**: BE traffic -65 %, total memory traffic about -23 %. Do not use `disable_tdn` in the pipeline config file: in
   this tree it probably makes `Camera::start()` fail.
6. **Ideas that do not help (CONFIRMED; the FE point PROBABLE).** A smaller preview cuts only 4 % (the Bayer stage dominates). A request without a preview buffer
   still runs the BE, into an internal buffer. The PiSP has no Bayer-domain downscaler. The FE cannot make a downscaled preview Bayer at
   RAW16, because its input is byte-swapped. Running the BE every Nth frame, or feeding it a CPU-made half-size Bayer, would work, but
   both need libcamera patches.

## 1. How pisp.cpp configures the BE for this mode

### 1.1 Streams, formats and nodes

| Item | Value | Label, source |
| --- | --- | --- |
| Core's streams in raw mode | `{VideoRecording, Raw}`. Preview: YUV420 1280x720, Rec709. Raw: sensor format | CONFIRMED, `apertar-core/src/camera/CameraController.cpp:6366-6369,6415-6419,1043-1044,2920-2931@f60e301`. The Pi runs `d9f00d4`; that the same holds there is PROBABLE (brief §1 says 1280x720) |
| One output stream goes to BE **output 1** | `if (i == 1 \|\| outStreams.size() == 1)` -> `Isp::Output1`, `PISP_BE_RGB_ENABLE_OUTPUT1` | CONFIRMED, `libcamera-apertar/src/libcamera/pipeline/rpi/pisp/pisp.cpp:1944-1947@6b0b49f` |
| CFE / BE input format | 16-bit sensor -> `Needs16bitEndianSwap`. `rawStats_` set -> CFE forced to `Packing::None` (unpacked u16), stride from `compute_optimal_stride` (7680 B) | CONFIRMED, `pisp.cpp:1744-1750,1812-1820,1855-1874@6b0b49f`. Simulation: stride 7680 |
| BE input = the CFE buffer itself | `isp_[Isp::Input]` set to `cfeFormat`; `prepareBe` queues the CFE buffer on `pispbe-input` | CONFIRMED, `pisp.cpp:1907,2750-2757@6b0b49f` |
| BE image format word | `PISP_IMAGE_FORMAT_BPS_16 + PISP_IMAGE_FORMAT_UNCOMPRESSED` (= 0x3); no `DECOMPRESS` | CONFIRMED, `pisp.cpp:166-169,2510-2517@6b0b49f` |
| TDN and stitch node formats | **set to `cfeFormat`**, i.e. 16-bit unpacked 3840x2200; TDN/stitch compress only if that format is compressed (it is not) | CONFIRMED, `pisp.cpp:1901-1905,2566-2602@6b0b49f` |
| CFE nodes | `rp1-cfe-fe_image0` (FE output 0) is the raw node. CSI-2 -> `pisp-fe` link on, CSI-2 -> `rp1-cfe-csi2_ch0` off, FE output 1 link off | CONFIRMED, `pisp.cpp:1366,2686-2697@6b0b49f` |
| Output 1 crop | `cfeFormat.size.boundedToAspectRatio(1280x720)` centred: (0,20) 3840x2160 | CONFIRMED, `pisp.cpp:1999-2000@6b0b49f`. Core's ScalerCrop keeps the full active area (`CameraController.cpp:2134-2152@f60e301`, `ScalerCropGeometry.hpp`), so this is PROBABLE at runtime |
| Output 1 scaling | SmartResize 3840x2160 -> 1280x720: downscaler 3840->1920 x 2160->1080, then resampler 1920x1080 -> 1280x720 | CONFIRMED, `libpisp/src/libpisp/backend/backend_prepare.cpp:568-600@v1.3.0`. Simulation: `downscale1 on resample1 on` |

### 1.2 Global enables (steady state)

The IPA sets the Bayer and RGB block enables each frame (`libcamera-apertar/src/ipa/rpi/pisp/pisp.cpp:365-373,426-470@6b0b49f`).
`configureBe()` adds INPUT and CSC1 (`pisp.cpp:2507,2542-2552@6b0b49f`). The simulation reproduces **`bayer_enables 0x47075d`,
`rgb_enables 0x0925ba`**.

| Block | On? | Why (CONFIRMED unless marked) |
| --- | --- | --- |
| INPUT / DECOMPRESS | on / off | `pisp.cpp:2507-2517`; input not compressed |
| DPC | on | tuning `rpi.dpc strength 1` -> `applyDPC` case 1 (`ipa pisp.cpp:776-778`; `imx585.json:23`) |
| GEQ | on | `rpi.geq` (`imx585.json:34`; `ipa pisp.cpp:871-880`) |
| **TDN, TDN_OUTPUT, TDN_INPUT** | **on** (TDN_INPUT off on the first frame, `tdn.reset`) | `rpi.denoise` has `tdn` in normal/hdr/night (`imx585.json:53,70,87`) -> `tdnEnable` (`denoise.cpp:55`); default mode `ColourHighQuality` (`denoise.cpp:76`); `tdn.status` set (`denoise.cpp:161-166`) -> `applyTdn` (`ipa pisp.cpp:846-851`). Core f60e301 never sets `NoiseReductionMode` (grep, no hit) |
| TDN_COMPRESS / DECOMPRESS | off | TDN format uncompressed (`pisp.cpp:2572-2582`) |
| SDN, CDN | on | `denoise.cpp:138-187` |
| BLC | on (per channel, FE BLA/BLC zeroed) | `ipa pisp.cpp:697-735` (RAW14/16 path) |
| WBG | on | AWB (`ipa pisp.cpp:620`) |
| LSC | on | `rpi.alsc` present (`imx585.json:1126`). That ALSC emits a status without calibration tables is PROBABLE |
| STITCH (+ in/out) | **off** | `rpi.hdr` dropped from the imx585 tunings in `16f1e271` (2026-05-17), so there is no `stitch.status` (`ipa pisp.cpp:447-458`). The kernel also clears stitch enables when they are off and ignores the queued stitch buffers (`kernel-rpi/drivers/media/platform/raspberrypi/pisp_be/pisp_be.c:422-428,534-551@5bd564a`) |
| CAC | off | `rpi.cac {}`: `config_.enabled` needs the LUTs (`cac.cpp:56-58,98-99`) |
| TONEMAP | off | no `rpi.tonemap` in imx585.json |
| DEBIN | off | `binX = binY = 1` in the 4K all-pixel mode (`ipa pisp.cpp:1127-1137`). That the mode reports bin 1 is PROBABLE |
| DEMOSAIC, FALSE_COLOUR, YCBCR, YCBCR_INVERSE | on | `setDefaultConfig` (`ipa pisp.cpp:1032-1050`) |
| CCM, GAMMA, SHARPEN | on | `rpi.ccm`, `rpi.contrast`, `rpi.sharpen` present |
| SAT_CONTROL | off | no `rpi.saturation` |
| CSC1, DOWNSCALE1, RESAMPLE1, OUTPUT1 | on | `pisp.cpp:2542-2563`; SmartResize |
| OUTPUT0, CSC0, DOWNSCALE0, RESAMPLE0 | off | one output stream only |

### 1.3 BE buffers and internal buffers

- **Two outputs?** No. Only output 1 is enabled. When a request carries no output-1 buffer, the pipeline queues a `nullptr`, and the
  stream substitutes one of its **2 internal buffers**, so the BE still runs. CONFIRMED,
  `libcamera-apertar/src/libcamera/pipeline/rpi/common/pipeline_base.cpp:795-808@6b0b49f`,
  `rpi/common/rpi_stream.cpp:124-145@6b0b49f`, allocation `pisp.cpp:1305-1307@6b0b49f`.
- **Resident BE buffers (memory, not bandwidth):** 2 TDN + 2 stitch buffers, each 7680 x 2200 = 16.9 MB, are allocated even though
  stitch is never enabled: **67.6 MB of CMA, 33.8 MB of it unused.** CONFIRMED, `pisp.cpp:1296-1307,1325-1337@6b0b49f`
  (`disable_hdr` defaults to false, `pisp.cpp:1632`). There are also 2 internal CFE raw buffers on top of Core's 8:
  `max(2, 4 - numRawBuffers) = 2` (`pisp.cpp:1278@6b0b49f`).
- **When the raw buffer is released.** It goes back to the request only on the BE **input** dequeue (`beInputDequeue` ->
  `handleStreamBuffer(cfe Output0)`, `pisp.cpp:2272-2284@6b0b49f`). The request completes, and the state returns to `Idle`, only after
  that (`pipeline_base.cpp:1525-1542@6b0b49f`). The whole BE run is therefore inside the serial per-frame cycle. CONFIRMED.

## 2. Bytes the BE moves per frame

The tiler output is from the simulation (libpisp v1.3.0, BCM2712 variant, the configuration above):

```
num_tiles 10, one stripe (MaxStripeHeight 3072 > 2200)
tile input widths: 408, 432 x 8, 408   (x offsets 0, 360, 744, ... 3432), rows 4..2195 (height 2192)
output-1 tile widths: 128 px each (1280 = 10 x 128)
```

- **Tile geometry (CONFIRMED by simulation; reasons PROBABLE).** Max tile width is 640 px (`libpisp/src/libpisp/variants/variant.cpp:31,48@v1.3.0`).
  Context is 16 px per side (`backend/tiling/pisp_tiling.cpp:26-27`). The tiles come out narrower than 640 because the output tile is
  aligned to 128 px: YUV420 planar with 64-byte chroma alignment (`backend_prepare.cpp:431-436,724-726`). Each 128-px output column
  needs 128 x 3 = 384 input px, plus context, which gives 432. Rows: crop y 20..2179 +/- 16 px of context = rows 4..2195 = 2192 rows.
- **Re-read factor.** Tile widths sum to 408 + 8 x 432 + 408 = 4272 px. 4272 x 2192 = 9,364,224 px against 3840 x 2200 = 8,448,000:
  **1.1085**.

| Stream | Arithmetic | MB/frame | GB/s at 30 fps | Label |
| --- | --- | --- | --- | --- |
| Raw input read | 9,364,224 px x 2 B | **18.73** | 0.562 | CONFIRMED (simulation) |
| TDN reference read (16-bit) | same tile regions: TDN addresses use the tile input offsets (`backend_prepare.cpp:916-919`) | **18.73** | 0.562 | CONFIRMED that it is on and 16-bit; PROBABLE that it covers the overlap |
| TDN output write (16-bit) | same; lower bound without overlap 3840 x 2192 x 2 = 16.83 | **18.73** (>= 16.83) | 0.562 | PROBABLE |
| Stitch in/out | disabled | 0 | 0 | CONFIRMED |
| Output 1, YUV420 1280x720 | 1280x720 + 2 x 640x360 = 1,382,400 B | **1.38** | 0.041 | CONFIRMED |
| Config + tiles (`pisp_be_tiles_config`) | 16,720 B (struct size from the simulation) | 0.02 | ~0 | CONFIRMED |
| BE statistics | none (HOG rejected, `backend.cpp:44-45`) | 0 | 0 | CONFIRMED |
| **Total** | 18.73 x 3 + 1.38 + 0.02 | **57.6** (>= 53.8) | **1.73** (>= 1.61) | PROBABLE |

For comparison, the brief's other full-frame passes per frame: CFE write 16.9, swap 33.8 (r+w), Core copy 33.8 (r+w), NVMe DMA 16.9 MB,
plus the stats read (row step 4: about 4.2 MB, PROBABLE). Total with the BE: about 163 MB/frame = 4.9 GB/s at 30 fps. **The BE is about
35 % of it and TDN alone about 23 %** (PROBABLE; Q3 owns the full budget). The CFE also writes the 23,200 B `pisp_statistics` buffer
(size from the simulation), which is negligible.

## 3. How fast the BE is

### 3.1 How the hardware is driven (CONFIRMED)

- libpisp packs the whole frame into one job: config plus up to 64 tiles (`PISP_BACK_END_NUM_TILES`, `pisp_be_config.h:32`). The kernel
  writes the registers and the tile pointer, then `CONTROL = COPY_CONFIG | QUEUE_JOB | NUM_TILES(n)` (`pisp_be.c:265-322@5bd564a`). The
  **hardware walks all 10 tiles by itself**, with one interrupt per job (`pisp_be.c:651-702`). There is no per-tile CPU involvement.
- The hardware has a **running slot and a queued slot** (`queued_job, running_job`, `pisp_be.c:240`; `PISP_BE_STATUS_QUEUED`). The driver
  keeps a job queue and starts the next job from the ISR (`pispbe_schedule`, `pisp_be.c:597-631`). Back-to-back BE jobs are a hardware
  capability. libcamera never queues a second job, because `tryRunPipeline` runs only when the state is `Idle` (`pisp.cpp:3112-3117`).
  That is Q2's topic.
- A job is formed once config + input are queued, and output/TDN/stitch buffers only when their enables are set
  (`pispbe_prepare_job`, `pisp_be.c:473-560`). The kernel also sanitises the TDN enables: no TDN input is used while `tdn.reset`
  is set (`pisp_be.c:409-418`).
- **Clock.** Firmware clock 7 (ISP), `bcm2712-ds.dtsi:386-394@5bd564a`. The driver only enables it and never sets a rate
  (`pisp_be.c:1677-1684`; no `clk_set_rate` in the file). The rate is UNCONFIRMED (X0).
- **AXI QoS 0.** `PISP_BE_AXI_REG = 0x32703200` with the comment "AXI QOS=0" (`pisp_be.c:1716-1720`). If the BCM2712 arbiter honours
  QoS, the BE has the lowest priority under DRAM contention. That effect is UNCONFIRMED; no public BCM2712 arbiter documentation was
  found.
- **Access pattern.** Each tile reads 2192 rows of 864 B (432 px x 2 B) out of a 7680 B stride, and does the same for TDN in and out:
  short strided bursts rather than linear streams. PROBABLE that this costs DRAM efficiency compared with a linear copy. The size of the
  cost is UNCONFIRMED.

### 3.2 Public throughput figures (UNCONFIRMED)

I could not open `datasheets.raspberrypi.com`, `raspberrypi.com`, `forums.raspberrypi.com`, `docs.kernel.org` or
`bugs.libcamera.org`: DNS failed in this container. A web-search summary (not the pages themselves) says the PiSP spec PDF lists a
throughput target of "up to 4Kp60, dependent on clock rate". The same summary attributes "nearly 1 GPixel/s" for the BCM2712 ISP to a
Raspberry Pi forum post. Treat both as **UNCONFIRMED** until someone opens
`https://datasheets.raspberrypi.com/camera/raspberry-pi-image-signal-processor-specification.pdf`. The 380 Mpix/s figure that
libcamera and Cinemate use is the **FE/CFE** limit (RP1 CLK_SYS x 2 px/clk - 20), not the BE
(`libcamera-apertar/src/ipa/rpi/controller/controller.cpp:103-147,195-215@6b0b49f`). CONFIRMED.

### 3.3 Comparison with what was measured

`be_start` and `be_done` in `working/tools/libcam_stages.py:15-16` are the log lines "Input re-queue to ISP" (start of `prepareBe`) and
"Stream ISP Input buffer complete" (`beInputDequeue` on the CameraManager thread). So 13.4 ms is the hardware time **plus**
`be_->Prepare`, the qbuf ioctls, the IRQ-to-poll latency and any wait for the thread. It is an upper bound. CONFIRMED.

| Quantity | Arithmetic | Result | Label |
| --- | --- | --- | --- |
| Share of the frame period at the idle rate | 13.4 / 33.33 | **40 %** | CONFIRMED arithmetic |
| Minimum pixel rate while running, idle | 9,364,224 px / 13.4 ms | **>= 0.70 Gpix/s** | PROBABLE |
| Minimum bandwidth while running, idle | 57.6 MB / 13.4 ms | **>= 4.3 GB/s** | PROBABLE |
| Compute floor if the BE did 1 Gpix/s | 9.36 Mpix / 1e9 | 9.4 ms (28 % of 33.3) | UNCONFIRMED input |
| Recording figure 34.6 ms (before L1/L2; 78 % of completions logged right after swap/stats) | 57.6 MB / 34.6 ms | 1.66 GB/s *if* all of it were BE time | thread delay included, so not BE time |
| BE time if it slowed like the CPU passes (x1.44 cycles, x1.62 swap) | 13.4 x 1.44 .. 13.4 x 1.62 | 19.3 .. 21.7 ms | PROBABLE |
| BE time needed to be the sole cause of a 36.2 ms cycle | >= 36.2 - (IPA + dispatch, a few ms) | >= ~30 ms, i.e. >= 2.2-2.5x idle | PROBABLE |

**Reading (PROBABLE).** At the idle rate the BE uses 40 % of the frame. To be the limiter by itself while recording, it would have to slow
more than twice as much as the CPU passes did under the same contention. That is possible: its traffic is twice the swap's, it is
strided, and its AXI QoS is 0. But nothing yet shows it. The brief's "BE >= 33 ms" (§4) is not measured: the 34.6 ms includes thread
delay. X1 measures the BE's hardware time directly. The TDN-off test (X2) also tells memory-bound from compute-bound: a memory-bound BE
falls with its bytes (-65 %), a compute-bound one barely moves.

## 4. Ways to render the 1280x720 preview from less data

All BE MB figures are from the simulation (`q1-pisp-be-sim.cpp`, cases A-F) unless marked.

| Option | BE MB/frame (now 57.6) | Feasible? | Source / label |
| --- | --- | --- | --- |
| **TDN off: tuning copy without `tdn`** (keeps SDN/CDN, uses their `*_no_tdn` values) | **20.0 (-65 %)** | Yes. No rebuild: Core's `tuning_file` setting, or `LIBCAMERA_RPI_TUNING_FILE` when that setting is empty (`CameraController.cpp:7941-7952,1135-1145@f60e301`). The SW-stats weights read a fixed path and are unaffected (`pisp/tuning_helpers.cpp:18-20@6b0b49f`) | CONFIRMED path (`denoise.cpp:55,161`); PROBABLE that d9f00d4 keeps the setting |
| **TDN off: `controls::draft::NoiseReductionMode = Off`** from Core | 20.0 (also turns SDN/CDN off) | Yes, a one-line Core change | CONFIRMED, `ipa pisp.cpp:557-571`, `denoise.cpp:136` |
| TDN off: pipeline config `disable_tdn: true` (`LIBCAMERA_RPI_CONFIG_FILE`) | 20.0 | **Risky.** The stream erase runs before `platformRegister` fills `streams_` (`pipeline_base.cpp:855` vs `916`), and it tests `TdnInput` twice instead of `TdnInput`/`TdnOutput` (`pisp.cpp:1659-1665`). TDN Output stays in `streams_` with **0 buffers** (`pisp.cpp:1299-1301`), and `vb2_core_streamon` returns `-EINVAL` with no buffers (`kernel videobuf2-core.c:2321-2324@5bd564a`), so `start()` fails | PROBABLE (same bug in libcamera-qbc `:1478` and Cinemate's libcamera `:1370`) |
| TDN kept, but stored compressed (libcamera patch: TDN nodes get `PISP_COMP1` instead of `cfeFormat`) | 18.73 + 9.36 + 9.36 + 1.38 = **38.8 (-33 %)** | Patch to `pisp.cpp:1901-1905`; `configureBe` already enables TDN compress/decompress for a compressed TDN format (`:2572-2582`) | PROBABLE (8 bpp: 9,364,224 px x 1 B) |
| Preview 640x360 instead of 1280x720 | 55.3 (-4 %) | Trivial, but useless: the Bayer stage dominates | CONFIRMED (case C) |
| Request with no preview buffer | 57.6 (no change) | The BE runs into an internal buffer | CONFIRMED (§1.3) |
| Run the BE only every Nth frame (libcamera patch in `prepareIspComplete`: for a request without an output-1 buffer, do what `!beEnabled_` does) | avg 57.6/N (N=2: 28.8; with TDN off: 10.0) | Patch + rebuild. TDN must be reset after a skipped frame (or off), and the IPA still runs | PROBABLE, `pisp.cpp:2363-2389`, `:2378-2384` |
| No ISP output at all (raw-only configuration) | 0 | libcamera supports it (`beEnabled_ = false`, no BE buffers, `pisp.cpp:2033,1296-1298,2378-2384`). Core would need another preview path (GPU/CPU from raw) | CONFIRMED in libcamera; Core work UNCONFIRMED |
| ScalerCrop 2x punch-in (1920x1080 centre) | 15.4 (-73 %) | Runtime control, retile on change; changes the framing, so a diagnostic only | CONFIRMED (case D: 4 tiles, 2.33 Mpix) |
| Bayer-domain downscale inside the BE | n/a | **Does not exist.** The BE pipeline is input -> context -> split -> per-branch crop -> downscale -> resample (`pisp_tiling.cpp:56-110`). Downscale/resample are RGB-branch blocks (`pisp_be_config.h:60-79`); only branch 1 has a downscaler (`variant.cpp:34`). DEBIN only corrects binned sensors | CONFIRMED |
| Half-size Bayer (1920x1100) made by the CPU in the pass that already reads the frame (swap worker), fed to the BE instead of the raw | 15.0 with TDN / **5.9** without | Big libcamera patch: separate BE input pool and format, plus 4.2 MB of CPU writes per frame. Bonus: the raw buffer can complete before the BE | CONFIRMED arithmetic (cases E/F); feasibility PROBABLE |
| FE output 1 as a downscaled Bayer (FE has 2 branches with downscalers, max width 6144/4096, `variant.cpp:28-30`) | n/a | **Not at RAW16.** The FE input is byte-swapped big-endian. The IPA's own note says FE Decompand/BLA/DPC/**Downscale**/Compress must be off at 14/16-bit (`ipa pisp.cpp:697-717`). njhollinghurst, 2025-06-26, github.com/raspberrypi/libcamera/issues/99: "RAW16 cannot be byte-swapped in hardware" and "compression and ISP-FE statistics will also be unavailable for RAW16 and RAW14". The FE output-1 link is disabled (`pisp.cpp:2697`) | CONFIRMED (issue opened via GitHub); "downscale is equally broken" PROBABLE (same byte order) |
| CSI-2 channel to memory and to the FE at the same time | n/a | The channel feeding the FE runs in `CSI2_MODE_FE_STREAMING` (`cfe.c:855-870`), and the FE source is a single channel (`cfe.c:1845-1856`). The sensor image goes to one CSI-2 sink pad/channel (`cfe.c:2037-2077`). Duplicating one VC/DT to two channels would need driver work; whether the hardware can do it is UNCONFIRMED | CONFIRMED (driver) |
| Does the FE accept 16-bit at all? | — | Yes: 16-bit bus formats carry `CFE_FORMAT_FLAG_FE_OUT` and `csi_dt = 0` "to avoid RP1 HW mismatch" (`cfe_fmts.h:196-224`); `cfe.c:855-857` allows dt 0 only for depth 16. The FE passes the data through to `fe_image0` with its pixel blocks no-op'd | CONFIRMED |

## Experiments this suggests

Ranked by information per effort. "Takes" means `working/tools/takes.sh 3 10` at 30 fps, uncompressed, Clear HDR 16-bit, L2 on
(`QBC_RAW_CPU_WORKER=1`, `QBC_RAW_STATS_ROW_STEP=4`) unless stated otherwise. Patrik does every restart, drop-in edit and `sudo`.

**X0. Read the facts the arithmetic depends on (no change).**
`vcgencmd measure_clock isp`; `ldd ~/opt/libcamera-apertar/lib/aarch64-linux-gnu/libcamera.so.* | grep -i pisp`;
`pkg-config --modversion libpisp`; `ls -l /usr/lib/aarch64-linux-gnu/libpisp.so* /usr/local/lib/aarch64-linux-gnu/libpisp.so* 2>/dev/null`.
Prediction: libpisp 1.3.0. A different version may tile differently, in which case rerun the simulation on that tag. The ISP clock
gives a compute floor (9.36 Mpix / (clock x px per clock)).

**X1. Measure the BE's hardware time directly (no change; Patrik, sudo).** Map minors first with
`for d in /sys/class/video4linux/video*; do echo "$(cat $d/name) $(cat $d/dev)"; done | grep pispbe`. Then, idle at 30 fps and again
during a take:
`sudo sh -c 'T=/sys/kernel/tracing; echo 0 > $T/tracing_on; echo > $T/trace; echo "name == \"pispbe\"" > $T/events/irq/irq_handler_entry/filter; echo 1 > $T/events/irq/irq_handler_entry/enable; echo 1 > $T/events/v4l2/v4l2_qbuf/enable; echo 1 > $T/tracing_on; sleep 5; echo 0 > $T/tracing_on; cat $T/trace > /tmp/be-trace.txt; echo 0 > $T/events/irq/irq_handler_entry/enable; echo 0 > $T/events/irq/irq_handler_entry/filter; echo 0 > $T/events/v4l2/v4l2_qbuf/enable'`
(the spaces around `>` matter: `echo 1>file` would redirect fd 1, not write "1").
Why these events: `v4l2:v4l2_qbuf` carries the video minor (`kernel v4l2-ioctl.c:3477-3479@5bd564a`). The BE ISR is registered as
"pispbe" (`pisp_be.c:1758-1759`). The driver enables "both interrupt flags" (`pisp_be.c:1722-1723`) and the ISR keeps separate
started and done counters (`pisp_be.c:663-690`), so 2 `pispbe` IRQs per frame is PROBABLE. If there is only one per frame, it is the
done IRQ, and the start is the config qbuf.
`vb2_v4l2_buf_done` is defined but never emitted in this tree (only `vb2:vb2_buf_done`, which has no minor), so do not use it.
BE hardware time = the interval between the two `pispbe` IRQs of one frame (start, then done). The `v4l2_qbuf` on `pispbe-config` (the
last buffer `prepareBe` queues, `pisp.cpp:2772-2797`) shows which pair belongs to which frame. The tracepoint fires after the ioctl
returns (`v4l2-ioctl.c:3475-3479`), so the start IRQ can appear just before it. Prediction: 2 IRQs per frame (60/s at 30 fps); idle
8-13 ms; recording 13-22 ms (1.0-1.6x idle).
Rule-out: if recording BE time is >= 30 ms, the BE is the limiter, and X2/X4 are the fix. If it is <= 22 ms while frames are still lost,
the missing time is elsewhere in the cycle (IPA, dispatch latency), which is Q2. If the events are missing, check
`ls /sys/kernel/tracing/events/v4l2` (kernel tracing support is UNCONFIRMED).

**X2. TDN off by tuning file (no rebuild; preview gets a little noisier, the DNGs do not change).** Copy the tuning file the Pi uses (the
journal's "Using tuning file ..." line), delete the three `"tdn": {...}` objects in `rpi.denoise` (`imx585.json:53,70,87` in this
tree), and point Core's `tuning_file` setting, or `LIBCAMERA_RPI_TUNING_FILE` in the drop-in, at the copy. Measure: one
`LIBCAMERA_LOG_LEVELS=RPI:0` window parsed with `libcam_stages.py`, plus X1 if available, then 3 takes. Prediction: BE traffic
57.6 -> 20.0 MB/frame and 1.13 GB/s less DRAM traffic overall. Idle BE start->done falls from 13.4 ms to <= 8 ms if memory-bound
(4.7 ms by bytes alone). Recording: <= 3 missing per take, delivered >= 29.8 fps. Rule-out: missing frames per take still >= 7 (the
best L1 result) and BE start->done within 15 % of the TDN-on value. Then the BE is neither memory-bound nor the limiter, and the lever
lies outside Q1.

**X3. Dump the BE configuration once (no rebuild).** Add `LIBCAMERA_RPI_PISP_CONFIG_DUMP=/tmp/be-cfg.json` to the drop-in (honoured at
`pisp.cpp:2782-2795`; it dumps the first frame only), restart, and wait for preview. Then
`python3 -c "import json;j=json.load(open('/tmp/be-cfg.json'));c={k:v for b in j['config'] for k,v in b.items()};print(hex(c['global']['bayer_enables']),hex(c['global']['rgb_enables']));print(c['tdn_output_format']);print(len(j['tiles']),[t['input_width'] for t in j['tiles']])"`.
Prediction: `0x47074d` (frame 0, TDN_INPUT not yet set) or `0x47075d`, rgb `0x925ba`. `tdn_output_format` 3840x2200, stride 7680, format
3. 10 tiles of width 408/432. Rule-out: TDN bits (0x40, 0x100) absent, or a compressed TDN format. Then §2 is wrong, and the BE moves
about 20 MB, not 57.6.

**X4. Skip the BE on frames without a preview buffer (libcamera L3 patch, build on the Pi; only if X1/X2 point at the BE).** In
`prepareIspComplete`, when the request has no `Isp::Output1` buffer, return the raw as the `!beEnabled_` path does
(`pisp.cpp:2378-2384`) and force a TDN reset on the next BE frame (or run with X2's tuning). Core attaches a preview buffer only every
2nd request. Prediction: average BE traffic 28.8 MB/frame (10.0 with TDN off), preview at 15 fps, 0-2 missing per take. Rule-out:
missing frames unchanged from L2.

**X5. Diagnostic punch-in (only if Core has a zoom/punch-in control).** Record with ScalerCrop at 2x (centre 1920x1080). BE traffic
drops to 15.4 MB/frame. Prediction: 0-2 missing per take while punched in, if BE bandwidth is the limiter. Rule-out: the same loss as
at full view.

**Ideas from brief §6 that the arithmetic already rejects (CONFIRMED):** "preview stream as small as libcamera allows" saves 4 % of BE
bytes, so expect no measurable change. "No ISP output buffer in the request" still runs the BE into an internal buffer (§1.3). Neither
is worth a take unless it is combined with X4.

## Unknowns

- The Pi's installed libpisp version and ISP clock rate (X0). The tiling numbers are exact only for v1.3.0.
- The BE's true hardware time, idle and recording, with L2 (X1). Every "is the BE the limiter" statement here is PROBABLE until then.
- Whether the TDN output DMA writes the 48-px tile overlaps once per tile (assumed: 18.73 MB) or only the non-overlapping region
  (16.83 MB). Only the PiSP spec or a bus counter can settle it. It changes the total by 1.9 MB.
- How the BCM2712 DRAM arbiter treats the BE's AXI QoS 0 against the CPUs, the RP1 (CFE writes over PCIe) and the NVMe DMA. No public
  documentation was found.
- Public BE throughput figures: the PiSP spec ("4Kp60") and the forum ("~1 GPixel/s") could not be opened from here.
- Whether Core `d9f00d4` still has the `tuning_file` setting and never sets `NoiseReductionMode` (checked on `f60e301` only).
- Whether `disable_tdn: true` really fails at start on the Pi (PROBABLE from code; do not use it in a take without a dry run).
- Preview quality with TDN off at the ISO in use. SDN uses `deviation_no_tdn` 3.2 instead of 0.6, so it denoises more strongly.

## Verification

Verifier: adversarial pass (Claude Opus 5.5), 2026-10-26. Every cited line opened in the trees at the cited commits (working trees of
libcamera-apertar `6b0b49f`, libcamera-qbc `7e9fef0`, libcamera (Cinemate) `bfe0b76`, libpisp `v1.3.0`, kernel-rpi `5bd564a`; Core via
`git show f60e301:`). The simulation was rebuilt from a scratch copy of libpisp v1.3.0 in the session scratchpad and re-run: all six cases
reproduce the report's numbers exactly (A 57.568, B 19.953, C 55.268, D 15.367, E 15.005, F 5.857 MB/frame). The X3 parsing one-liner was
run against a `GetJsonConfig()` dump of case A and prints `0x47075d 0x925ba`, the 3840x2200/7680/format 3 TDN format and the 10 tile widths.
The PiSP spec PDF and the forum could not be opened from here either (proxy 403 on `datasheets.raspberrypi.com`). Verdicts:
CONFIRMED (holds as labelled), CORRECTED (holds, but the cite, number or label is wrong), REFUTED, UNVERIFIABLE (needs the Pi or a blocked page).

| # | Claim | Verdict | Evidence |
| --- | --- | --- | --- |
| 1 | Simulation build recipe and "numbers CONFIRMED for v1.3.0" | CORRECTED | Numbers reproduce exactly. The recipe as written does not build: `backend_default_config.cpp:20` includes the meson-generated `backend/pisp_build_config.h` (`libpisp/src/libpisp/backend/meson.build:6-8@v1.3.0`), which must be stubbed (`#define PISP_BE_CONFIG_DIR "..."`), and the link needs `-ldl` |
| 2 | Core raw mode streams `{VideoRecording, Raw}`, YUV420 1280x720 Rec709 | CONFIRMED | `apertar-core/src/camera/CameraController.cpp:6364-6369,6415-6419,1043-1044,2920-2931@f60e301` |
| 3 | A single output stream goes to BE output 1 | CONFIRMED | `libcamera-apertar/src/libcamera/pipeline/rpi/pisp/pisp.cpp:1944-1947@6b0b49f` |
| 4 | 16-bit sets `Needs16bitEndianSwap`; `rawStats_` forces unpacked CFE; stride 7680 | CONFIRMED | `pisp.cpp:1744-1750,1813-1820,1846,1870-1874@6b0b49f`; `computeOptimalStride` calls libpisp `compute_optimal_stride` (`pisp.cpp:259-275`), 64-B alignment (`libpisp/src/libpisp/common/pisp_utils.cpp:115-119@v1.3.0`): 3840 x 2 = 7680 |
| 5 | BE input is the CFE buffer itself | CONFIRMED | `pisp.cpp:1907,2752-2757@6b0b49f` |
| 6 | BE input format word `BPS_16 + UNCOMPRESSED`, no DECOMPRESS | CONFIRMED | `pisp.cpp:166-169,2510-2517@6b0b49f` |
| 7 | TDN and stitch node formats = `cfeFormat` (16-bit unpacked) | CONFIRMED | `pisp.cpp:1902-1905,2566-2582@6b0b49f`; the BE driver accepts `SRGGB16` etc. (`kernel-rpi/drivers/media/platform/raspberrypi/pisp_be/pisp_be_formats.h:336-345@5bd564a`), so no fallback to YUV420 (`pisp_be.c:1136-1142`) |
| 8 | CFE nodes and links | CORRECTED | Links CONFIRMED at `pisp.cpp:2686-2697`; `rp1-cfe-fe_image0` is at `pisp.cpp:1364`, not 1366 (1366 is `fe_stats`) |
| 9 | Output-1 crop (0,20) 3840x2160 | CONFIRMED | `pisp.cpp:1999-2000@6b0b49f`: 3840x2200 bounded to 16:9 = 3840x2160, y = (2200-2160)/2 = 20. Runtime ScalerCrop PROBABLE as labelled |
| 10 | SmartResize: downscaler 3840->1920 x 2160->1080, resampler -> 1280x720 | CONFIRMED | `libpisp/src/libpisp/backend/backend_prepare.cpp:572-597@v1.3.0`: clamp(1280x2, 480, 1920) = 1920; clamp(720x2, 270, 1080) = 1080 |
| 11 | "The simulation reproduces `bayer_enables 0x47075d`, `rgb_enables 0x0925ba`" | CORRECTED | The Bayer bits and most RGB bits are hand-set in the simulation (`working/research-30fps/q1-pisp-be-sim.cpp:37-48`); `Prepare()` only adds DOWNSCALE1/RESAMPLE1. The values rest on the code reading in §1.2, which holds: 0x400000+0x40000+0x20000+0x10000+0x400+0x200+0x100+0x40+0x10+0x8+0x4+0x1 = 0x47075d; 0x80000+0x10000+0x2000+0x400+0x100+0x80+0x20+0x10+0x8+0x2 = 0x925ba (`libpisp/src/libpisp/backend/pisp_be_config.h:35-78@v1.3.0`) |
| 12 | DPC, GEQ, BLC, WBG, LSC on; CAC, TONEMAP, DEBIN, SAT_CONTROL off | CONFIRMED (for the tree's tuning) | `libcamera-apertar/src/ipa/rpi/pisp/pisp.cpp:767-778,870-880,697-746,620,764,1128-1137@6b0b49f`; `src/ipa/rpi/controller/rpi/cac.cpp:56-58,98-99@6b0b49f`; `src/ipa/rpi/pisp/data/imx585.json:23,34,1126,1948@6b0b49f`, no `rpi.tonemap`/`rpi.saturation` (grep of `"rpi.` keys) |
| 13 | TDN, TDN_OUTPUT, TDN_INPUT on (CONFIRMED) | CORRECTED (label) | CONFIRMED for `libcamera-apertar/src/ipa/rpi/pisp/data/imx585.json:53,70,87@6b0b49f`, `denoise.cpp:55,76,161-166`, `ipa pisp.cpp:846-851`. For the Pi it is PROBABLE only: in Clear HDR, Core's automatic tuning picks `<sensor>_clearHDR.json` when it exists (`apertar-core/src/camera/CameraController.cpp:5587-5596@f60e301`, `src/camera/DefaultTuningSelection.hpp:183-197@f60e301`), and for a log preview it loads a derived copy (`CameraController.cpp:5679-5697@f60e301`). Neither file is in any tree here |
| 14 | Stitch off: `rpi.hdr` dropped in `16f1e271` (2026-05-17); the kernel clears stitch enables and ignores stitch buffers | CONFIRMED | `git show 16f1e271` (libcamera-apertar, dated 2026-05-17, ancestor of qbc `7e9fef0`); `ipa pisp.cpp:447-458`; `kernel-rpi/.../pisp_be/pisp_be.c:422-430,541-551@5bd564a` |
| 15 | One output; a request without a preview buffer queues `nullptr` and uses one of 2 internal buffers | CONFIRMED | `libcamera-apertar/src/libcamera/pipeline/rpi/common/pipeline_base.cpp:795-808@6b0b49f`, `rpi/common/rpi_stream.cpp:131-145@6b0b49f`, `pisp.cpp:1305-1307` |
| 16 | 2 TDN + 2 stitch buffers = 67.6 MB, 33.8 MB unused; 2 internal CFE buffers | CONFIRMED | `pisp.cpp:1278,1299-1307,1325-1337,1632@6b0b49f`; 4 x 7680 x 2200 = 67,584,000 B; max(2, 4-8) = 2 |
| 17 | The raw buffer returns only on BE input dequeue; Idle only after that | CONFIRMED | `pisp.cpp:2272-2284`, `pipeline_base.cpp:1525-1542@6b0b49f`; also `prepareIspComplete` sets `IpaComplete` right after queueing the BE (`pisp.cpp:2385-2387`) |
| 18 | 10 tiles, widths 408/432x8/408, x stride 384, rows 4..2195 | CONFIRMED | Re-run of the simulation (case A) |
| 19 | "Each 128-px output column needs 384 input px, plus context [16 px per side], which gives 432" | CORRECTED | 384 + 2 x 16 = 416, not 432. The overlap is 432 - 384 = 48 px (24 per side; the edge tiles are 384 + 24 = 408). The extra 8 px per side come from the downscaler's right context and the resampler's start/end context (`libpisp/src/libpisp/backend/tiling/pisp_tiling.cpp:26,83-106@v1.3.0`). The numbers are right; only the explanation is wrong |
| 20 | Re-read factor 1.1085 | CONFIRMED | 408 + 8 x 432 + 408 = 4272; 4272 x 2192 = 9,364,224; / 8,448,000 = 1.10846 |
| 21 | Raw read 18.73 MB/frame | CONFIRMED | 9,364,224 x 2 = 18,728,448 B |
| 22 | TDN read and write 18.73 MB each (overlap PROBABLE); lower bound 53.8 MB | CONFIRMED (as labelled) | TDN tile addresses use the input offsets (`backend_prepare.cpp:916-919@v1.3.0`). Lower bound = 18.73 + 16.83 + 16.83 + 1.38 = 53.77 MB (assumes both TDN read and write without overlap; 3840 x 2192 x 2 = 16,834,560); x 30 = 1.61 GB/s |
| 23 | Output 1.38 MB; config + tiles 16,720 B; FE stats 23,200 B | CONFIRMED | 921,600 + 2 x 230,400 = 1,382,400; `sizeof(pisp_be_tiles_config)` = 16,720 and `sizeof(pisp_statistics)` = 23,200 (compiled against libpisp v1.3.0 headers) |
| 24 | HOG rejected at `backend.cpp:44-45` | CORRECTED (cite) | The throw is at `libpisp/src/libpisp/backend/backend.cpp:46-47@v1.3.0` |
| 25 | Total 57.6 MB = 1.73 GB/s; TDN 65 % of BE traffic | CONFIRMED | 3 x 18.728 + 1.382 + 0.017 = 57.58; x 30 = 1.727 GB/s; 37.46 / 57.58 = 65.1 % |
| 26 | Frame budget about 163 MB = 4.9 GB/s; BE 35 %, TDN 23 % | CORRECTED | Arithmetic of the brief's list holds (16.9 + 33.8 + 33.8 + 16.9 + 4.2 + 57.6 = 163.2). The list omits the buffered `write()` copy into the exFAT page cache (no O_DIRECT, T24 not in, brief §1/§2): about 16.6 MB read + 16.6 MB write per frame (DNG 16,590,340 B, hardware-log T25 entry). PROBABLE total about 196 MB/frame = 5.9 GB/s; BE 57.6/196 = 29 %, TDN 37.6/196 = 19 % |
| 27 | One job per frame, up to 64 tiles, hardware walks the tiles | CONFIRMED | `libpisp/.../pisp_be_config.h:32@v1.3.0`; `kernel-rpi/.../pisp_be.c:265-322@5bd564a` |
| 28 | "with one interrupt per job" (§3.1) | CORRECTED | The driver enables both interrupt flags (`pisp_be.c:1722-1723`) and the ISR keeps separate started and done counters (`pisp_be.c:663-690`), so up to two IRQs per job. The report's own X1 says 2 per frame is PROBABLE; §3.1 contradicts it |
| 29 | Running + queued hardware slot, driver job queue; libcamera never queues a second job | CONFIRMED | `pisp_be.c:240,597-631,651-704@5bd564a`; `libcamera-apertar/.../pisp.cpp:3112-3117@6b0b49f` |
| 30 | Job formation rules and TDN sanitising | CONFIRMED | `pisp_be.c:408-420,473-566@5bd564a` |
| 31 | Firmware clock 7, no `clk_set_rate` | CONFIRMED | `kernel-rpi/arch/arm64/boot/dts/broadcom/bcm2712-ds.dtsi:386-394@5bd564a`; `pisp_be.c:1677-1684`, grep finds no `clk_set_rate`. Rate UNVERIFIABLE |
| 32 | AXI QoS 0 | CONFIRMED (comment); effect UNVERIFIABLE | `pisp_be.c:1715-1720@5bd564a` |
| 33 | Strided access, 864 B per row per tile | CONFIRMED (arithmetic) | 432 x 2 = 864 B out of 7680; DRAM cost UNVERIFIABLE |
| 34 | Public BE throughput ("4Kp60", "~1 GPixel/s") | UNVERIFIABLE | Spec PDF blocked here as well; a web search showed only the spec's v0.5 table of contents and the kernel docs (https://docs.kernel.org/6.12/userspace-api/media/v4l/metafmt-pisp-be.html), no throughput figure |
| 35 | 380 Mpix/s is the CSI-2 -> FE limit, not the BE | CONFIRMED | `libcamera-apertar/src/ipa/rpi/controller/controller.cpp:103-147,191-215@6b0b49f` |
| 36 | `be_start`/`be_done` are "Input re-queue to ISP" / "Stream ISP Input buffer complete"; 13.4 ms is an upper bound | CONFIRMED | `working/tools/libcam_stages.py:15-16`; `pisp.cpp:2754,2277@6b0b49f`. See Missed 1: the same log line already carries the hardware done time |
| 37 | §3.3 arithmetic: 40 %, >= 0.70 Gpix/s, >= 4.3 GB/s, 9.4 ms, 1.66 GB/s, 19.3-21.7 ms, 2.2-2.5x | CONFIRMED | 13.4/33.33 = 0.402; 9.364/13.4 ms = 0.699 Gpix/s; 57.6/13.4 ms = 4.30 GB/s; 57.6/34.6 ms = 1.66 GB/s; 13.4 x 1.44 = 19.3, x 1.62 = 21.7; 30/13.4 = 2.24, 33/13.4 = 2.46. The measured medians leave 36.2 - 34.6 = 1.6 ms for "IPA + dispatch", so the sole-cause threshold is nearer 34 ms (2.5x) |
| 38 | "The CPU passes slowed 1.44-1.62x" | CORRECTED | Hardware log: cycles 25 M -> 36 M = 1.44x, swap 6.1 -> 9.9 ms = 1.62x, but raw stats 5.8 -> 7.1 ms = 1.22x. The range is 1.22-1.62x; the conclusion is unchanged |
| 39 | TDN off by a tuning copy: 20.0 MB/frame, no rebuild, via `tuning_file` or `LIBCAMERA_RPI_TUNING_FILE`; SW-stats weights read a fixed path | CONFIRMED | Simulation case B 19.953 MB; `denoise.cpp:55-70@6b0b49f`; `apertar-core/src/camera/CameraController.cpp:7941-7952,1135-1145@f60e301`; `libcamera-apertar/src/libcamera/pipeline/rpi/pisp/tuning_helpers.cpp:18-20@6b0b49f`. A user-picked file is used as given (no `_clearHDR` substitution, `CameraController.cpp:5586-5592@f60e301`), so the copy must start from the file the journal names, as X2 says |
| 40 | `NoiseReductionMode=Off` also turns SDN/CDN off; Core f60e301 never sets it | CONFIRMED | `ipa pisp.cpp:557-571`, `denoise.cpp:136-137@6b0b49f`; `git grep -i NoiseReduction f60e301` has no hit |
| 41 | `disable_tdn: true` makes `start()` fail: TDN Output keeps 0 buffers, `vb2_core_streamon` returns -EINVAL | REFUTED (mechanism) | The erase runs on an empty `streams_` and tests `TdnInput` twice: CONFIRMED (`pipeline_base.cpp:855,916`, `pisp.cpp:1428-1441,1659-1665@6b0b49f`). But `queueAllBuffers()` calls `importBuffers(VIDEO_MAX_FRAME)` on every stream in `streams_` (`pipeline_base.cpp:957-960`), which does `VIDIOC_REQBUFS` for 32 DMABUF slots (`src/libcamera/v4l2_videodevice.cpp:1588-1597@6b0b49f`), so `q_num_bufs` is not 0 and `pisp_be` sets no `min_queued_buffers`; streamon passes (`videobuf2-core.c:2321-2330@5bd564a`). PROBABLE real failure: the IPA still enables TDN_OUTPUT (`ipa pisp.cpp:846`), the TDN output node streams with no buffer, so `pispbe_prepare_job` returns -ENODEV for every job (`pisp_be.c:533-566`) and no request ever completes. "Do not use it" stands |
| 42 | Same bug in libcamera-qbc `:1478` and Cinemate's libcamera `:1370` | CORRECTED | The `TdnInput`-twice typo is at `libcamera-qbc/.../pisp.cpp:1478-1479@7e9fef0` and `libcamera/.../pisp.cpp:1370-1371@bfe0b76`. The ordering half differs: Cinemate's tree registers before it loads the config (`libcamera/src/libcamera/pipeline/rpi/common/pipeline_base.cpp:854,858@bfe0b76`) |
| 43 | Compressed TDN: 38.8 MB (-33 %) | CONFIRMED (arithmetic) | 18.73 + 9.36 + 9.36 + 1.38 = 38.83; 1 - 38.83/57.58 = 32.6 %. Feasibility PROBABLE as labelled (`pisp.cpp:2572-2582`) |
| 44 | Preview 640x360: 55.3 MB (-4 %) | CONFIRMED | Simulation case C 55.268; 1 - 55.27/57.57 = 4.0 % |
| 45 | A request without a preview buffer saves nothing | CONFIRMED | Row 15 |
| 46 | X4 / "run the BE every Nth frame": patch in `prepareIspComplete`; "Core attaches a preview buffer only every 2nd request" | CORRECTED | Arithmetic holds (57.6/2 = 28.8; 19.95/2 = 10.0). But at f60e301 every request carries a preview buffer (`apertar-core/src/camera/CameraController.cpp:6813-6825@f60e301`), so alternating needs a Core change. And output-1 buffers, internal ones included, are queued to the BE node when the request is queued (`pipeline_base.cpp:781-808`, `rpi_stream.cpp:131-152@6b0b49f`); the kernel takes them first-in first-out (`pisp_be.c:557-563@5bd564a`). PROBABLE: if the BE is skipped, that internal buffer stays queued. The next job writes into it while the app's preview buffer stays pending, so that request cannot complete. The next BE job only starts from `Idle`, so the pipeline stalls. The patch must also stop queueing an internal output-1 buffer for skipped frames |
| 47 | Raw-only configuration: `beEnabled_ = false`, no BE buffers | CONFIRMED | `pisp.cpp:2033,1296-1298,2377-2384@6b0b49f` |
| 48 | ScalerCrop 2x: 15.4 MB (-73 %), 4 tiles, 2.33 Mpix | CONFIRMED | Simulation case D 15.367; 1 - 15.37/57.57 = 73.3 % |
| 49 | "The PiSP has no Bayer-domain downscaler" (Short answer 6) | CORRECTED | True for the BE only (`libpisp/src/libpisp/variants/variant.cpp:34,51@v1.3.0`, `pisp_tiling.cpp:51-112`). The FE has Bayer-domain downscalers on both branches (`variant.cpp:29-30,46-47`), unusable at RAW16 (row 51) |
| 50 | CPU-made half-size Bayer: 15.0 / 5.9 MB, plus 4.2 MB of writes | CONFIRMED (arithmetic) | Cases E 15.005, F 5.857; 1920 x 1100 x 2 = 4,224,000 B |
| 51 | FE output 1 cannot carry a downscaled Bayer at RAW16; njhollinghurst quotes | CONFIRMED | `ipa pisp.cpp:697-719@6b0b49f`; https://github.com/raspberrypi/libcamera/issues/99 (opened): comment dated Jun 26, 2025 says "RAW16 cannot be byte-swapped in hardware" and "compression and ISP-FE statistics will also be unavailable for RAW16 and RAW14". It does not mention downscale, so "downscale is equally broken" stays PROBABLE |
| 52 | The FE is fed by one CSI-2 channel; one VC/DT to two channels would need driver work | CONFIRMED (driver) | `kernel-rpi/drivers/media/platform/raspberrypi/rp1_cfe/cfe.c:860-871,1846-1856,2037-2077@5bd564a` |
| 53 | The FE accepts 16-bit (`cfe_fmts.h:196-224`, `cfe.c:855-857`) | CORRECTED (cite) | `cfe_fmts.h:196-226` CONFIRMED; the depth-16 exception is the `WARN_ON` at `cfe.c:858`, with the comment at 854-857 |
| 54 | X0 readings (libpisp version, ISP clock) | UNVERIFIABLE | Needs the Pi. Whether `vcgencmd measure_clock isp` reports the BE clock on a Pi 5 is also unconfirmed; `sudo grep -i isp /sys/kernel/debug/clk/clk_summary` is an alternative |
| 55 | X1 tracepoints: `v4l2:v4l2_qbuf` carries the minor; `irq_handler_entry` can be filtered on `name`; IRQ name "pispbe"; `vb2_v4l2_buf_done` is never emitted | CONFIRMED | `kernel-rpi/drivers/media/v4l2-core/v4l2-ioctl.c:3475-3479@5bd564a`; `include/trace/events/irq.h:53-66`; `pisp_be.c:40,1758-1759`; only `v4l2-trace.c:9` exports it, and there is no `trace_vb2_v4l2_buf_done(` caller under `drivers/media` or `include`. Outcome UNVERIFIABLE |
| 56 | X2 predictions: 20.0 MB, 1.13 GB/s, 4.7 ms "by bytes", "<= 3 missing per take, >= 29.8 fps" | CORRECTED (minor) | 57.568 - 19.953 = 37.615 MB, x 30 = 1.128 GB/s; 13.4 x 19.95/57.57 = 4.64 ms: CONFIRMED. The two delivery thresholds disagree: 3 of ~287 missing is 284/287 x 30 = 29.69 fps, and 29.8 fps is <= 1.9 missing. The 13.4 ms baseline predates L1/L2, so X2 needs a TDN-on window on the same build |
| 57 | X3: `LIBCAMERA_RPI_PISP_CONFIG_DUMP` dumps once per file name; the one-liner parses the v1.3.0 JSON; frame-0 value 0x47074d | CONFIRMED | `pisp.cpp:2791-2797@6b0b49f`; `libpisp/src/libpisp/backend/backend_debug.cpp:482-522@v1.3.0` ("config" is a list of one-key objects, "tiles" a list); script run on a simulated dump; 0x47075d - 0x10 (TDN_INPUT) = 0x47074d |
| 58 | Brief §6 ideas rejected (smallest preview, no ISP buffer) | CONFIRMED (bytes) | Rows 44-45. "No measurable change" is PROBABLE, not CONFIRMED: it is a prediction |

Counts: 58 claims. **CONFIRMED 41, CORRECTED 14, REFUTED 1, UNVERIFIABLE 2.**

### Corrections that change substance

1. **"TDN is on" holds for the libcamera tree, not yet for the Pi (row 13).** Core loads `<sensor>_clearHDR.json` automatically in Clear HDR when it
   exists, and a derived copy for a log preview (`apertar-core/src/camera/CameraController.cpp:5587-5596,5679-5697@f60e301`). Neither file is in
   any tree here. If that file has no `tdn`, the BE moves about 20 MB, not 57.6 MB, and X2 cannot help. Read-only check before X2:
   `journalctl -u apertar-core -b | grep -i "tuning file"`. Then, on the named file:
   `python3 -c "import json,sys;d=json.load(open(sys.argv[1]));print([list(a['rpi.denoise'].keys()) for a in d['algorithms'] if 'rpi.denoise' in a])" <file>`.
   X3's dump settles it too. Either check should come before X2.
2. **`disable_tdn` does not make `start()` fail (row 41).** `queueAllBuffers()` gives every node 32 DMABUF slots, so streamon passes. The
   PROBABLE failure is worse: no BE job ever forms while the IPA enables TDN_OUTPUT, so the camera stalls. The advice not to use it stands.
3. **X4 as written would stall the pipeline and needs a Core change (row 46).** Core f60e301 puts a preview buffer in every request. The
   pipeline queues an output-1 buffer (internal when the request has none) to the BE when the request is queued, and the kernel uses those
   buffers first-in first-out. Skipping the BE leaves one queued, and the next request then waits forever. X4 needs a third piece: no internal
   output-1 buffer for skipped frames.
4. **The TDN share of all memory traffic is about 19 %, not 23 % (row 26).** The budget leaves out the buffered `write()` copy into the page
   cache (about 33 MB/frame). TDN off is still the largest cut that needs no rebuild.

### Missed

- **The BE's hardware done time is already in the RPI:0 log** (q2 found this, q1 did not). `pispbe_isr_jobdone` stamps every buffer of the job with
  `ktime_get_ns()` (`kernel-rpi/.../pisp_be.c:637-644,1454@5bd564a`). libcamera logs that value as `timestamp:` on "Stream ISP Input buffer
  complete" (`pisp.cpp:2277-2279`, `v4l2_videodevice.cpp:1899@6b0b49f`), and the log prefix uses the same monotonic clock (`log.cpp:857`,
  `include/libcamera/base/utils.h:82@6b0b49f`). So (done timestamp - "Input re-queue" log time) bounds the hardware time without the thread
  delay, and (log time - done timestamp) is the thread delay. This needs no sudo and no ftrace: one RPI:0 window with L2 (already on the
  brief's §6 list) answers X1's question, and the 20:50 windows can be re-parsed if they are still on the Pi. X1 becomes a fallback.
- The Clear HDR tuning-file selection (correction 1), and the X4 FIFO stall (correction 3).
- Framing that supports X2 (PROBABLE). The BE's bytes are the same idle and recording, and preview-only at 30 fps is clean. What recording
  adds is Core's copy 33.8 + page-cache copy ~33.2 + NVMe DMA 16.9 = ~84 MB/frame (2.5 GB/s). TDN off (37.6 MB) offsets about 45 % of that.
- `disable_hdr: true` is PROBABLY safe in this tree, unlike `disable_tdn` (not run). Stitch is never enabled, so the kernel ignores the missing stitch buffers
  (`pisp_be.c:541-551`), and prepareBe stops queueing them (`pisp.cpp:2766`). It frees 33.8 MB of CMA and two qbuf/dqbuf per frame on the
  CameraManager thread. It saves no bandwidth, so its value is low.
