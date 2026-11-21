# G1: what the knowledge base records about 12-bit Clear HDR (IMX585)

Assignment G1 of the "12 bit clear HDR shows strange output" investigation. Read-only. Nothing ran on a camera.
Written 2026-11-17 in a cloud session.

| Ref used | What |
| --- | --- |
| KB `e11e438` | every `path:line` without a repo name is a KB page at this commit (the cited pages are unchanged since `95c391a`) |
| Core `main` `f60e301`, Core `cinemate-port` `01f170c` | to pin a KB claim to code (`git show <ref>:<path>`) |
| libcamera `apertar` `6b0b49f` (`/home/user/tiramisioux/libcamera`) | the fork the brief names; its base `7e9fef0` is what the KB says is installed |
| driver `apertar` `e5b74d3`, `cinemate-port` `cd548ef` | `/home/user/imx585-v4l2-driver` |
| cinepi-raw `63a08d5` | Cinemate's CCMP table, for the binning claim |

Labels: **confirmed** (read at the ref, or recorded in the KB as measured on the Pi), **probable** (inferred, reason
given), **unconfirmed** (the command that settles it is named). A KB page is a record of intent and of past
measurements, not proof of what today's build does.

## 1. Short answer

- The KB holds two beliefs, both from the evening of 2026-10-25. Until 22:05: the 12-bit mode reaches Core as
  **companded 12-bit codes**. From 22:05: the installed libcamera expands the codes in software and Core receives
  **linear 16-bit** samples (black 3200, white 65520). The second belief is the one built into Core `e1c10cd` and
  `57c8fb0`, it is on fork main, and the port carries it unchanged (section 4).
- That belief was measured on the Pi **once**: 4K (3840x2160), driver `apertar` `e5b74d3`, Core `e1c10cd` / `57c8fb0`,
  libcamera `v0.7.1+qbcfork.20260522-7-7e9fef0b`. The KB holds no later sample measurement of a 12-bit Clear HDR
  frame: not on driver `cd548ef`, not in a binned (2K) mode, not with Log on, not on any port build.
- Nobody ever recorded **looking** at 12-bit Clear HDR: no entry says a DNG was neutral in a raw converter, none
  describes the HDMI or WebUI preview, none plays a 12-bit Clear HDR clip in either player, none opens an MLV.
  Every check after 2026-10-25 is a tag, a sample statistic, a frame count or a file size.
- Three things changed around the 12-bit path after the last measurement and are recorded only as side notes:
  the driver now offers **binned 2K** in 12-bit Clear HDR (the KB's own Cinemate answer says a binned mode needs a
  different curve), **Log** replaces the CCMP table by a composed one, and **4K 12-bit Clear HDR drops frames at
  every fps from 30 down to 25** on the port (2026-11-11).

## 2. Timeline

Times are the Pi's clock as the KB pages give them. "Open" is what the page itself left open.

| # | When | Code that ran | Seen or done | Confirmed on the Pi | Left open | KB ref |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 2026-10-23 | none (handoff prompt) | 12-bit CCMP declared out of scope; CCMP controls +2/+3/+4 "not used in this effort" | - | "12-bit CCMP" as a follow-up | `sources/2026-10-23-clearhdr16-handoff.md:11`, `:31`, `:182` |
| 2 | 10-25 20:43 | Core T16 step 3 (WDR write only, uncommitted); driver `e5b74d3`; libcamera qbc `7e9fef0b` in `/usr/local` | With WDR=1 the driver offers SRGGB12 3840x2160 **and** SRGGB16 3840x2200. Core came up in 12-bit companded Clear HDR: **"very dark preview"**. Reverted | WDR read back; frame sizes listed | why the preview was dark | `tutorials/progress/T16.md:8`; `working/clearhdr-design.md:18`, `:25` |
| 3 | 10-25 20:43 | - | Decision (Patrik): both depths, user picks. 12-bit "experimental or hidden" until linearised | - | "Does 12-bit look right with blend 5 and gain adder 1, or is the table unavoidable?" | `T16.md:9`; `clearhdr-design.md:7-14`, `:25`, `:30` |
| 4 | 10-25 21:22 | Core WIP | 16-bit frames were pedestal only: `rpi.hdr` in Core's tuning file pins exposure 135 / gain 0 in Clear HDR. Fix: tuning without it (`imx585_clearHDR.json`) | 16-bit: registers 2700 / 60, median 6469 (C0017) | never re-checked against the 12-bit "very dark preview" | `clearhdr-design.md:43`, `:54-63`; `T16.md:15` |
| 5 | 10-25 21:34 | Core `631721d` | Committed: "16-bit working, 12-bit experimental" | - | "Open: 12-bit LinearizationTable, frame drops, UI/WebUI, ISO cap" | `T16.md:16`; `fork-log.md:25` |
| 6 | 10-25, before 22:05 (the page gives no time) | Core `631721d` (probable: the page names no commit) | **DNG symptom**: recognisable picture with a strong purple/magenta cast, green-yellow edge fringes, blown posterised highlights, magenta speckle in transitions. Median 1634, p99 4073, max 4086 of 4095 (SDR, same exposure: 468 / 1312 / 1368) | sample statistics | - | `working/clearhdr-12bit-request.md:7` |
| 7 | 10-25 (Mac) | Cinemate sources only | Answer: Cinemate stores the codes plus a LinearizationTable (output `L + 200`, BlackLevel 200, WhiteLevel 63265 full-res / 62704 binned), **one table per binning**, a measured knee 1; blend menu 0 gives speckle; Cinemate's libcamera does not decompand; the log line seen on the Pi is not in Cinemate's fork | nothing | which libcamera the image runs, and whether its decompand reaches the image or only the statistics | `working/clearhdr-12bit-answer.md:14-31`, `:64-95`, `:107-136`, `:138-151` |
| 8 | 10-25, before 22:05 | Core uncommitted (`src/cdng/CcmpLut.hpp`) | Cinemate's table attached to 12-bit frames | tag 50712 with 4096 entries (t[700]=700, t[1634]=23889, t[4095]=63265), BlackLevel 200, WhiteLevel 63265; SDR and 16-bit carry no table | "that the picture is now neutral"; MLV has no table; "the live preview is untested" | `clearhdr-design.md:65-68` |
| 9 | 10-25 22:05 | bench `bench12.sh`, Core stopped | **Correction**: in the 12-bit mode libcamera delivers linear 16-bit samples, black about 3200. The purple picture was Core keeping `src & 0x0FFF` in `packDng12Row` (values 3200-16662 wrapped). Table code removed | 12-bit mode median 6222 / p99 15730 / max 16662 against 16-bit mode 6242 / 15941 / 16930, same scene | - | `clearhdr-design.md:71-74` |
| 10 | 10-25 22:09 | Core `e1c10cd` | 12-bit mode stored as linear 16-bit; lossy refused in all Clear HDR | C0030, C0031: 16 bps, median 6286, p99 about 15700; 16-bit C0028: 6294 / 15943 | frame drops (0-4 frames per 2-3 s) | `clearhdr-design.md:75-76`; `fork-log.md:26` |
| 11 | 10-25 22:20-22:32 | Core `57c8fb0` | libcamera's table read from the installed library (`libcamera::CcmpUnwrap`); `ClearHdrCcmp.hpp` reproduces it; cDNG = 12-bit codes + table, black 3200, white 65520; MLV keeps linear 16-bit; Clear HDR forces 4K | C0032-C0035: 12.5 MB uncompressed, 5.9 MB lossless, decoded median 6033 / p99 15066 against 16-bit 6053 / 15168; all 4096 entries equal libcamera's | a look in a raw converter; MLV in Clear HDR at 4K; the table holds only at the driver's default CCMP controls | `clearhdr-design.md:78-83`; commit message of `57c8fb0`; `fork-log.md:27` |
| 12 | 10-25 22:46 | Core `9fa7918`, UI `4415a55` | WebUI and touch UI: "4K Clear HDR" resolution, 16-bit depth, "Clear HDR is 12/16-bit only" | - | - | `fork-log.md:28`, `:239` |
| 13 | 10-25 22:55 | Core `9fa7918` | Frame drops traced to libcamera's CPU passes on uncached buffers, measured in 16-bit. "12-bit mode: not measured; expected worse" | 12-bit takes: 0-4 of about 75 frames | - | `clearhdr-design.md:93-105`; `working/handoff-clearhdr-buffering.md:22`, `:31` |
| 14 | 10-26 00:10 | Core `94ac68d` | Cached buffers for the unpacked Clear HDR stream | 12-bit: camera thread 38 %; lossless takes 244/245 and 242/244 at 25 fps | - | `clearhdr-design.md:107-113`, `:137` |
| 15 | 10-26 00:55 | Core `f60e301` | Probe: Clear HDR 12-bit 3840x2160 max 30 fps. At 30 fps: 12-bit lossless 228/291, camera thread 72 % | measured | 30 fps | `working/sensor-capabilities.md:51-54` |
| 16 | 10-26 (cloud, source only) | libcamera qbc `7e9fef0`, Core `f60e301` | `CcmpUnwrap` rewrites the raw buffer **in place**, before the ISP back end and before Core; the source comments that say "the raw buffer is NOT rewritten" are stale. Engaged for imx585 + 12 bpp + WDR=1 + the three vendor controls. The CFE is forced to unpacked u16 | code read only | "which libcamera runs on the Pi" stays open in a later page | `working/compare-raw/b2-libcamera-16bit.md:80-84`, `:134`; `working/clearhdr-compare-answer.md:107`, `:166`; `working/clearhdr-compare-notes.md:33` |
| 17 | 10-26 21:36 | driver `cinemate-port` `24172e6` | Real crop rectangles per mode | `list_sensor_modes` | - | `fork-log.md:272`; `architecture/drivers.md:227-235` |
| 18 | 10-26 evening | libcamera `apertar` `889567a`, `6b0b49f` in `~/opt/libcamera-apertar`, loaded by a drop-in | L1 (stats row step), L2 (swap, CCMP unwrap and stats on a worker thread, default off) | measured in 16-bit only | 12-bit never run with L1 or L2 | `lessons/hardware-log.md:204-233`; `working/handoff-30fps-clearhdr16.md:23`, `:114-116`; `fork-log.md:264-265` |
| 19 | 10-28 19:46 | Core `b5847c7` | "Clear HDR 12-bit and SDR 12 keep 30". "16-bit only sticks after Clear HDR is on (set before: stays 12, no error)" | `set_fps` and state readings | the order dependence (no later row fixes it) | `tutorials/progress/T32.md:7` |
| 20 | 10-28 | Core `4f7975f`, driver `24172e6`, 4K Clear HDR 12-bit lossless, preview only | ISO to gain code. 12-bit ceiling = code 57 = **ISO 720** (16-bit: code 80 = ISO 1585). Fixed DNG WhiteLevel ("the CCMP table's end in 12-bit") | `v4l2-ctl --get-ctrl analogue_gain` | whether the merge clamps below white at high gain | `lessons/hardware-log.md:503-516` |
| 21 | 10-28 20:09 | Core `8175273` | Clear HDR holds ISO and WB (auto off), caps ISO at 720 in 12-bit | six checks in preview | - | `lessons/hardware-log.md:518-526`; `fork-log.md:61` |
| 22 | 10-28 21:13 | Core `6d217c7`, UI `f1edf96` | `iso_max`: Clear HDR 12-bit 720 | `get_state`; Patrik: "work well" | - | `lessons/hardware-log.md:549-554` |
| 23 | 10-29 | design at Core `0296ed1`; Pi tests at `f91fafa`..`4fa0432` | Playback design fact F4: "Clear HDR 12-bit cDNG is also stored as 12-bit codes with a LinearizationTable". Touch UI shows "16-bit" for it (probable); WebUI FORMAT row "Clear HDR 12-bit companded" | Pi playback measured with Clear HDR **16-bit** uncompressed and SDR 12-bit clips only | no 12-bit Clear HDR clip was played | `working/playback/design-playback.md:150`, `:844-846`; `working/playback/r2-apertar-ui-player.md:395`, `:624`; `working/playback/measurements.md:12-22`; `lessons/hardware-log.md:650-663` |
| 24 | 10-31 22:26 | Core `drop-frames` (later squashed into `d44b177`) | Log built. Journal: `CineMate Log 16->12 mu=10000 black=3200 white=65520 footroom=32/487`; one DNG 12,451,344 B | the journal line and the file size | "Not opened in Resolve yet" | `lessons/hardware-log.md:813-823` |
| 25 | 11-01 | same branch | "Log works in Clear HDR 16-bit only" (SDR is PiSP COMP1) | the SDR journal line | "Open one Log frame in Resolve" | `working/drop-frames/README.md:116-120`, `:144`; `lessons/hardware-log.md:857-864` |
| 26 | 11-01 18:55 | driver `cd548ef`, Core `4b2eeac` | Cinemate's mode tables merged. Probe: "CCMP default-on for colour". 187 modes | dmesg, `get_state` ready. **"No takes yet"** | any picture on the new driver | `lessons/hardware-log.md:899-904`; `fork-log.md:273` |
| 27 | 11-03 | Core `31d5418`, UI `c153c33`, libcamera `/usr/local` `7e9fef0b`, driver `cd548ef` | 16-bit preview flicker study. "12-bit Clear HDR also runs RawStats on the CPU". `imx585_clearHDR.json` serves both depths. T55 section 3 plans a "12- against 16-bit" look | read-only Pi state | T55 has no progress file: the look never happened | `working/clearhdr16-preview.md:11-12`, `:50-51`, `:71`; `working/handoff-clearhdr16-preview.md:205-207`; `ls tutorials/progress/` |
| 28 | 11-07 / 11-08 | Core `f4a1393`, CM5 Lite, USB SSD, 189 takes | **2K binned Clear HDR 12-bit** and 4K Clear HDR 12-bit recorded. Log in 12-bit: same file size (2K 3.12 MB with and without), journal `CineMate Log 16->12 ... composed with the CCMP expansion`. 4K lossless 6.1 MB, lossless + Log 8.5 MB | frame counts, file sizes, journals | the picture of any take | `working/drop-frames/tests-2026-11/findings-longtakes-ssd-2026-11-07.md:3`, `:18-20`, `:30`, `:35-37`; `working/drop-frames/nvme-campaign/critique/C4-red-team-facts.md:15`, `:146`; `working/drop-frames/nvme-campaign/plan.md:156-158`, `:242`; `working/drop-frames/longtakes-test-structure.md:22-23` |
| 29 | 11-10 22:48 | Core `7e6e2a3`, UI `25eeb47` (named for the 21:06 run of the same evening; this run does not restate it: probable) | 4K HDR12 asked for 30 fps, Core set 25 (`fps_max` 25). Probable cause: an attached IMX283 filled the startup probe | measured | - | `working/drop-frames/nvme-campaign/findings.md:131`, `:140-143`, `:155-158` |
| 30 | 11-11 02:51-03:01 | same, IMX283 unplugged | **4K HDR12 uncompressed drops frames at 30, 29, 28, 27, 26 and 25 fps**, first drop after 2-93 s; 200 dropped in the 60 s warm-up at 30 fps. No passing fps | measured (capture gaps) | open | `findings.md:170-171`; `working/drop-frames/nvme-campaign/run-20261110/report-S2-S4-S5.md:136-153` |
| 31 | 11-11 05:31-09:44 | same | 60 s probes at 30 fps: uncompressed 291 dropped, lossless 164 dropped, MLV buffer full at 9 s | measured | open | `findings.md:207`, `:229`; `run-20261110/report-EST.md:32`, `:51`, `:61` |
| 32 | 2026-11-17 | Core `01f170c`, UI `7ea9afc`, driver `cd548ef` | Owner: "12 bit clear HDR shows strange output"; 16-bit fine | - | this investigation | task text |

## 3. Every symptom description of 12-bit Clear HDR in the KB

| # | Symptom, in the page's words | Where it showed | Code | Closed? | KB ref |
| --- | --- | --- | --- | --- | --- |
| S1 | "very dark preview" | preview | Core WIP before `631721d` | **Not closed in the text.** The page's own guess ("Core reads its values as linear", `clearhdr-design.md:25`) was overtaken by row 9. Probable real cause: the `rpi.hdr` exposure pin of row 4, which acts in any Clear HDR mode. No page re-looked at the 12-bit preview | `T16.md:8` |
| S2 | "strong purple/magenta cast, green-yellow edge fringes, blown posterised highlights and magenta speckle in transitions" | DNG in a converter | Core `631721d` | **Closed** by numbers: low-12-bit wrap, fixed in `e1c10cd`, kept in `57c8fb0` (decoded median within 0.4 % of the 16-bit mode). Not closed by eye | `clearhdr-12bit-request.md:7`; `clearhdr-design.md:74-75`, `:83` |
| S3 | magenta speckle = blend menu 0 (the Mac's second cause) | DNG | - | **Dismissed**: "does not apply: Core writes blend 5 at every start" | `clearhdr-12bit-answer.md:14-31`; `clearhdr-design.md:67` |
| S4 | 0-4 of about 75 frames written; written frame numbers 0, 14, 15, 19 | clip (missing frames) | Core `57c8fb0`, `9fa7918` | **Closed at 25 fps** by `94ac68d` (244/245) | `handoff-clearhdr-buffering.md:22-24`; `clearhdr-design.md:113` |
| S5 | 30 fps loses about 20 % (12-bit lossless 228/291) | clip | Core `f60e301` | **Open** | `sensor-capabilities.md:54` |
| S6 | ISO above 720 leaves the sensor's combine window in 12-bit | exposure | Core `4f7975f` | **Closed** by the cap in `8175273` (preview test, 4K, driver `24172e6`) | `lessons/hardware-log.md:503-526` |
| S7 | `set_raw_bit_depth 16` before `set_clear_hdr true` "stays 12, no error" | the mode itself | Core `b5847c7` | **Open** (recorded, no fix row) | `T32.md:7` |
| S8 | BIT DEPTH reads "16-bit" on the touch UI for a 12-bit Clear HDR clip | clip metadata | UI `5aab7e2` (code read) | **Open by decision** D9: the WebUI copies "16-bit" and puts the stored depth in FORMAT | `r2-apertar-ui-player.md:624`; `design-playback.md:486` |
| S9 | Log on changes nothing in file size; lossless + Log files are larger than lossless | file | Core `f4a1393` | **Explained**, not judged: composed table, "12 bits in, 12 bits out" | `C4-red-team-facts.md:15`; `findings-longtakes-ssd-2026-11-07.md:35-37` |
| S10 | `fps_max` 25 where 30 was asked | the mode itself | Core `7e6e2a3` | **Closed** (probable cause: IMX283 probe modes) | `findings.md:140-143`, `:155-158` |
| S11 | drops at every fps 30..25 within 2-93 s; MLV buffer full at 9 s | clip | Core `7e6e2a3` | **Open** | `findings.md:170`, `:229` |

Not recorded anywhere: a description of the 12-bit preview after S1, a judgement of a 12-bit DNG after S2, any
12-bit Clear HDR clip in the clip browser or either player, any 12-bit Clear HDR MLV opened in a reader.

## 4. What the KB believes libcamera delivers in 12-bit Clear HDR

| Belief | Held from | Core commit it belongs to | Evidence in the KB |
| --- | --- | --- | --- |
| Companded 12-bit codes reach Core; Core must attach a table (Cinemate's, black 200, white 63265) | 2026-10-25 until 22:05 | `631721d` ("12-bit experimental") and the uncommitted `CcmpLut.hpp` | `clearhdr-12bit-request.md:7`; `clearhdr-12bit-answer.md:107-136`; `clearhdr-design.md:25`, `:65-68` |
| **Linear 16-bit** samples in an unpacked u16 buffer: black 3200, white 65520, `out = 3200 + L * 62320 / 63084`; codes 0-200 all become 3200; about 6 of the 500 linear codes merge. Expanded in software, in place, by `libcamera::CcmpUnwrap` on the pipeline thread, before the ISP back end and before Core | 2026-10-25 22:05 (measured), 22:20 (table read from the library) | `e1c10cd` (store linear 16-bit) and `57c8fb0` (store the codes + this table). Both are on fork main `f60e301` | `clearhdr-design.md:71-83`; `compare-raw/b2-libcamera-16bit.md:80-84` |

The second belief is the KB's last word. Pinned to code:

| Check | Result | Label |
| --- | --- | --- |
| Is the belief still in the port? | `src/cdng/ClearHdrCcmp.hpp` is byte-identical at `f60e301` and `01f170c` (`git diff --stat f60e301 01f170c -- src/cdng/ClearHdrCcmp.hpp` is empty). Comments: `ClearHdrCcmp.hpp:9-13`, `src/camera/CameraController.cpp:1682-1685@cinemate-port` ("libcamera hands over linear 16-bit samples in both sensor modes"), `:3989-3990@cinemate-port` ("the CCMP stream is linear 16-bit (libcamera expands the codes)") | confirmed |
| Does the fork the brief names still expand in place? | `src/libcamera/pipeline/rpi/pisp/pisp.cpp:3100-3104@6b0b49f` (`ccmpUnwrap_->process(rawPx + y * strideU16, width)`), engaged at `:1821-1823` (`model() == "imx585"`, 12 bpp, `initCcmpUnwrap()`), which needs WDR=1 and controls `0x00982902/3/4` (`:2950-2988`). The comment at `:1824-1831` still says "the raw buffer is NOT rewritten": stale, as the KB notes | confirmed |
| Where do the curve parameters come from? | libcamera reads them **live** from the driver: thresholds from control +2, slope indices from +3 and +4, black from `V4L2_CID_BRIGHTNESS x 4` (`pisp.cpp:2990-3023@6b0b49f`). Core's table is fixed: 500 / 11500 / 6 / 4 / 200 (`ClearHdrCcmp.hpp:24-30`) | confirmed |
| Did the driver change those values? | Same control ids and defaults on both branches: `imx585.c:36-38`, `:1822`, `:517-518`, `:149@e5b74d3`; `imx585.c:37-39`, `:3688`, `:557-558`, `:159@cd548ef` | confirmed |
| Recomputed table | From the formula: t[200]=3200, t[700]=3693, t[701]=3757, t[871]=14505, t[4095]=65520. Equal to `clearhdr-design.md:80` | confirmed |
| Measured on the Pi after 2026-10-25 22:32? | No entry | confirmed (absence) |

So for the 4K all-pixel mode at the driver's defaults, the code at the port refs agrees with the belief. The belief
has no measurement behind it for: driver `cd548ef`, any binned or cropped mode, Log on, MLV, or the port's Core.

Which libcamera build the camera runs is itself unsettled in the KB (section 6, C9). It does not change the 12-bit
path: `889567a` and `6b0b49f` add two environment switches, both default off (`fork-log.md:264-265`).

## 5. How the KB says each output stores or shows the 12-bit mode

| Output | KB statement | Code at `cinemate-port` | Ever checked on the Pi |
| --- | --- | --- | --- |
| cDNG uncompressed or lossless, Log off | 12-bit codes; LinearizationTable = libcamera's expansion; BlackLevel 3200 on all four; WhiteLevel 65520. 12.44 MB uncompressed at 4K (`clearhdr-design.md:82-83`; `longtakes-test-structure.md:22`) | `CameraController.cpp:1640-1644` (`clearHdrStoresCodes12`), `:1647-1658` (`compressClearHdrFrame`), `:4090-4096` (table and black 3200) | tags and decoded statistics, 2026-10-25, 4K only |
| cDNG, Log on | "composed with the CCMP expansion", 12 bits in and out (`C4-red-team-facts.md:15`) | `:3982`, `:3996-3998` (black 3200, white 65520), `:4031-4033` (`buildComposed`), `:4041` (the journal words) | file size and the journal line only |
| Lossy DNG | refused in all Clear HDR (`clearhdr-design.md:68`; `fork-log.md:26`; `lessons/hardware-log.md:633`) | not read here | refusal seen |
| MLV | "keeps the linear 16-bit samples (MLV has no table)" (`clearhdr-design.md:82`) | comment `:1637-1639` | never opened; "MLV in Clear HDR at 4K is untested" (`handoff-clearhdr-buffering.md:24`); only a buffer-full count on 11-11 |
| ProRes, H.264 | `set_clear_hdr true` returns an error (`clearhdr-design.md:83`) | not read here | error seen |
| HDMI and WebUI preview | rendered by the ISP back end from the expanded buffer (`compare-raw/b2-libcamera-16bit.md:81`) | libcamera, not Core | never described after S1 |
| Clip browser, players | apply the LinearizationTable; touch UI then says "16-bit" (`r2-apertar-ui-player.md:395`, `:527`) | `src/playback/ClipProbe.hpp:165-175` (label rule, section 7 F5) | no 12-bit Clear HDR clip on record |

## 6. Contradictions between pages

| # | Page A | Page B | Which is right | Risk |
| --- | --- | --- | --- | --- |
| C1 | `clearhdr-12bit-request.md:7`, `clearhdr-12bit-answer.md:107-136`, `clearhdr-design.md:65-68`: the stream is companded; attach Cinemate's table (BlackLevel 200, WhiteLevel 63265) | `clearhdr-design.md:71-83`: the stream arrives linear; "Cinemate's own table ... does **not** match this libcamera; do not use it here" | B. A is superseded only inside the design page; the request and answer pages carry no note | A fixer who opens only the answer page builds the wrong table |
| C2 | `clearhdr-design.md:73`: libcamera "decompands the 12-bit CCMP stream in the CFE" | `clearhdr-design.md:80`; `compare-raw/b2-libcamera-16bit.md:81`: in software, `CcmpUnwrap`, pipeline-handler thread | B (code `pisp.cpp:3100-3104@6b0b49f`) | wrong mental model of where it can fail |
| C3 | `clearhdr-12bit-answer.md:140-151`: the log line is not in "our" fork; stats-only would mean a magenta preview | `clearhdr-design.md:73`: the line "means exactly this" (the image is linearised) | B for the image the Pi runs. The log text itself still says "stats linearisation" (`pisp.cpp:1839@6b0b49f`) and the comment above it says the buffer is not rewritten | the journal line reads as if only statistics were corrected |
| C4 | `clearhdr-design.md:11`: goal table, 12-bit mode stored as "12-bit DNG/MLV" | `clearhdr-design.md:82`: MLV keeps linear 16-bit | B (code comment `CameraController.cpp:1637-1639@cinemate-port`) | a 12-bit Clear HDR MLV is a 16-bit file, 16.6 MB a frame |
| C5 | `clearhdr-design.md:34`: "12-bit Clear HDR keeps every resolution" | `clearhdr-design.md:82`: "Clear HDR forces 4K in both modes (libcamera rejects 1920x1080 in Clear HDR)" | B on 2026-10-25. Both are stale: a 2K Clear HDR 16-bit take exists from 11-01 (`lessons/hardware-log.md:957`), 2K Clear HDR 12-bit takes from 11-07 (`findings-longtakes-ssd-2026-11-07.md:18`) | no page says when the 4K rule was lifted, and no 2K picture check exists |
| C6 | `lessons/hardware-log.md:862`: `planCdngLog` "maps only unpacked 2-byte streams, which only Clear HDR 16-bit gives"; `drop-frames/README.md:120`: "Log therefore applies in Clear HDR 16-bit (unpacked) only" | `findings-longtakes-ssd-2026-11-07.md:35-36`; `C4-red-team-facts.md:15`; `nvme-campaign/plan.md:242`: in Clear HDR 12-bit Log is applied as a table "composed with the CCMP expansion" | B (code `CameraController.cpp:4031-4041@cinemate-port`). The 12-bit Clear HDR stream is unpacked 2-byte too | the page a reader finds first says Log does nothing in 12-bit |
| C7 | `drop-frames/README.md:70`: Log is "always one step down" (12 stored as 10) | same B pages: Clear HDR 12-bit with Log stays 12-bit | B | - |
| C8 | Cinemate, as the KB records it: 12-bit Clear HDR + Log is "only valid composed with the decompand to target 10" (`working/dng-chain/R1.md:175`; `clearhdr-12bit-answer.md:136`) | Apertar composes to 12 (`C4-red-team-facts.md:146`: `CineMate Log 16->12 ... composed`) | both describe their own stack | Apertar's combination has no reference to compare against |
| C9 | `fork-log.md:254`: the Pi runs `7e9fef0b` from `/usr/local` (confirmed 10-26); `clearhdr16-preview.md:11-12`, `:56-57` (11-03): `/usr/local`, and no `libcamera-test.conf` among Core's drop-ins | `handoff-30fps-clearhdr16.md:114-116` (10-26): Core loads `~/opt/libcamera-apertar` `6b0b49f` through `libcamera-test.conf`; the merge-review brief names `apertar` `6b0b49f` as "the fork the Pi runs" | open: `working/dng-chain-feasibility.md:387` lists it as unknown | none for the 12-bit curve; matters only if `QBC_RAW_CPU_WORKER=1` is set |
| C10 | `architecture/drivers.md:3-6`, `:216-225`; `llm/flows.md:208`: with WDR on, 12-bit goes to one 4K entry; "Binned modes are gone in Clear HDR"; no `ccmp` parameter | `lessons/hardware-log.md:899-904`: `cd548ef` loaded, "CCMP default-on for colour", 187 modes | B is what runs. The driver page has no `cd548ef` section. Code: binned 1920x1080 and the 1x1 crops are offered in 12-bit Clear HDR (`imx585.c:3052-3095@cd548ef`), `clearhdr_ccmp` default-on for colour (`:4641-4643`) | the KB's driver page describes a driver the camera no longer runs |
| C11 | `clearhdr-12bit-answer.md:115`, `:126`, `:155-159`: black is 200; do not take it from `SensorBlackLevels` | `clearhdr-design.md:82`: black 3200 under the table | both, each in its own table's output domain | mixing them gives a black level 16 times off |
| C12 | `clearhdr-design.md:137`: 12-bit lossless at 25 fps "loses 0-2 frames" | `findings.md:170`: uncompressed, every fps 30..25 drops within 2-93 s | both measured (10-26 `94ac68d`; 11-11 `7e6e2a3`) | "25 fps is clean in 12-bit" no longer holds on the port |
| C13 | `working/ramp-ladder/README.md:63`: 12-bit ISO cap "~716" | `lessons/hardware-log.md:507-510`: 720 = code 57 | B (measured) | none |
| C14 | `clearhdr-design.md:43`: the installed libcamera is a "Tiramisioux fork `v0.7.1+qbcfork.20260522`" | `fork-log.md:252-255`; `clearhdr-compare-answer.md:12`: will127534 `qbc-pisp-handler` `7e9fef0`; Tiramisioux `apertar` is a branch cut from it on 10-26 | B | a reader looks for the CCMP code in Cinemate's fork, which has none (`compare-raw/b2-libcamera-16bit.md:51`) |
| C15 | The investigation names Core `cinemate-port` `01f170c` | `fork-log.md:191-198`: the Pi was built from branch `clip-split` up to `7e6e2a3` on 2026-11-09/10 ("Pi only"); `findings.md:131` names `7e6e2a3` for the 11-10 run | both: `01f170c` is GitHub's `cinemate-port`, `7e6e2a3` (`origin/clip-split` in the local clone) is 8 commits later | none for the picture path: `git -C /home/user/Apertar-Core diff 01f170c 7e6e2a3` touches no CCMP, Log or level line (clip names, split and merge, drop logging; playback only changes how a frame file is opened) |

## 7. Findings for the investigation

Ranked by how directly the KB's own record points at them. Each says what the operator would see and where.

### F1. The "linear 16-bit" belief was measured once, in 4K, on the old driver (confirmed)

- Claim: every 12-bit Clear HDR output of the port rests on one bench of 2026-10-25 22:05-22:32
  (`clearhdr-design.md:71-83`). No sample statistic of a 12-bit Clear HDR frame exists for driver `cd548ef`, a 2K
  mode, Log on, or any Core after `57c8fb0`.
- If the expansion is not running, Core still pushes the raw values through `compressionLut()` and writes the
  expansion table. Symptom then: the level-dependent purple/magenta cast of S2, without the wrap, in the DNG **and**
  in the preview (HDMI and WebUI), in every 12-bit Clear HDR resolution; 16-bit fine.
- Code at the port refs says the expansion still runs (section 4), so this is a check, not a suspect.
- Settle (needs the Pi): in 12-bit Clear HDR, `journalctl -b -u apertar-core --no-pager | grep -E 'CCMP stats linearisation|CcmpUnwrap: rebuilt LUT'`.
  Expected: `T1=500 T2=11500 slope_L=1/64 slope_H=1/16 blc_u12=200; LUT[200]=3200 ... LUT[500]=3496 LUT[2048]=33164 LUT[4095]=65520`.

### F2. Binned 2K 12-bit Clear HDR probably uses the wrong curve (probable)

- KB fact: "Binning goes into the curve. The compander sees the binned sum, so binned modes put the knees 4x lower
  in L. Use one table per binning" (`clearhdr-12bit-answer.md:80`). Cinemate's source: "At code 400 the decode is
  200 full-res and 3387.5 binned" (`cinepi/ccmp_lut.hpp:39-45@63a08d5`).
- Code: libcamera's `CcmpUnwrap::Params` has thresholds, slopes and black, no binning
  (`ccmp_unwrap.h:57-67@6b0b49f`); Core's table has the same five numbers (`ClearHdrCcmp.hpp:24-30@cinemate-port`).
- The port's driver offers the binned 1920x1080 readout in 12-bit Clear HDR (`imx585.c:3052-3095@cd548ef`); the
  KB shows it was recorded for hours on 2026-11-07 (timeline row 28) with no picture check.
- Predicted, if Cinemate's measurement holds on this stack: between codes about 326 and 800 the decoded value is
  far too low (code 400: 200 instead of 3387; code 700: 500 instead of 8187), then jumps steeply to the right level
  near code 871. Above that the two curves agree within 5 %.
- Symptom: **2K (binned) 12-bit Clear HDR only**: mid-tones crushed dark with a hard tonal step and a colour cast
  that changes with level. Same in the HDMI and WebUI preview, the DNG in a converter, MLV, and both players, because
  all of them start from libcamera's expanded buffer. 4K 12-bit and the 1x1 crops are not affected. 16-bit is linear
  and fine in both sizes. It is the one candidate here that predicts a wrong picture in the preview, the file and
  the players at once, in 12-bit only, with the code doing exactly what it was written to do.
- Not confirmed: that the sensor on this rig behaves as Cinemate measured.
- Settle (needs the Pi): same scene, same exposure, 1920x1080, one uncompressed take in 12-bit Clear HDR and one in
  16-bit. Decode the 12-bit frame through its tag 50712. Compare medians as on 2026-10-25 (then: 6033 against 6053
  in 4K). A 2K 12-bit median far below the 16-bit one confirms it.

### F3. With Log on, 12-bit Clear HDR files carry a different table, and two KB pages say Log is not applied (confirmed)

- Code: `CameraController.cpp:4031-4033@cinemate-port` builds `cdnglog::buildComposed(params, ccmp::expansionTable())`
  and a copy table through `ccmp::compressionLut()`; `:4041` prints "composed with the CCMP expansion".
- KB: section 6, C6 and C7. The only checks are file size and the journal line. Open item "Open one Log frame in
  Resolve" (`drop-frames/README.md:144`) was never ticked for any depth.
- Symptom, if the composed table or its levels are wrong: tones wrong in the **recorded cDNG** (raw converter,
  clip browser thumbnail, both players) only while Log is on; live preview unaffected; MLV unaffected.
- Settle: `curl -s http://127.0.0.1:8000/api/state | grep -o '"cdng_log[a-z_]*":[^,]*'` (needs the Pi), then on any
  machine `exiftool -BitsPerSample -BlackLevel -WhiteLevel -LinearizationTable <frame.dng>` for a Log-on and a
  Log-off frame of the same scene and compare the decoded medians. Host side: the table can be built without a
  camera from `src/cdng/LogCurve.hpp` and `src/cdng/ClearHdrCcmp.hpp` (plain `g++`).

### F4. 4K 12-bit Clear HDR loses frames at every tested fps on the port (confirmed, measured)

- KB: 2026-11-11, Core `7e6e2a3` (probable, see row 29): uncompressed, first drop after 1.7-92.8 s at 30, 29, 28, 27,
  26 and 25 fps (the runner stops a take at its first drop); 200 dropped in the 60 s warm-up at 30 fps; 60 s probes
  at 30 fps: uncompressed 291 dropped, lossless 164, MLV buffer full at 9 s (timeline rows 30-31). On the same
  card 16-bit carried 27 fps for 3 + 5 min and ran 12.6 min at 25 fps with 0 dropped (`findings.md:119`, `:179`).
- The 12-bit mode costs more CPU than 16-bit: libcamera's scalar LUT pass over 8.3 Mpx (`ccmp_unwrap.cpp:154-160@6b0b49f`)
  plus Core's LUT pass back to codes (`working/dng-chain/R7.md:145`).
- Symptom: **not a wrong picture**. Index holes in the clip folder; the WebUI Clip Viewer draws a missing frame
  black (`lessons/hardware-log.md:662`; `fork-log.md:102`), so playback shows black flashes; an NLE shows a
  one-frame gap; the dropped-frames chip counts up during the take. 16-bit at 25 fps does not show it.
- Settle (needs the Pi): `journalctl -b -u apertar-core --no-pager | grep -E 'recording stats:|drop\['` after a 12-bit take;
  or count files against the last index in the clip folder.

### F5. The WebUI clip label "Clear HDR 12-bit companded" also covers 16-bit Clear HDR takes recorded with Log (confirmed)

- Code: `src/playback/ClipProbe.hpp:165-175@cinemate-port`: a clip whose first frame is not 16 bits and carries a
  LinearizationTable, outside a lossy folder, is labelled "Clear HDR 12-bit companded" and `"companded":true`
  (`src/ApertarCoreApp.cpp:7371@cinemate-port`).
- KB: the rule was written on 2026-10-29 as a "PROBABLE rule from F3, F4" (`design-playback.md:844-846`); Log, which
  stores 16-bit Clear HDR as 12 bits plus a table, was built two days later (timeline row 24).
- Symptom: in the WebUI Clip Browser and Viewer a 16-bit Clear HDR take recorded with Log on reads "Clear HDR
  12-bit companded". An owner report about "12-bit Clear HDR" clips seen in the player can therefore be about
  16-bit Log takes. The touch UI shows "16-bit" for all of them (`r2-apertar-ui-player.md:395`).
- Settle: read `ClipProbe.hpp:165-175`; or `curl` `/api/media/clip` for a 16-bit Log take and read `"format"`
  (`ApertarCoreApp.cpp:7399@cinemate-port`).

### F6. Core's table is fixed, libcamera's follows the driver's live controls (confirmed)

- KB caveat: "Constants are only valid while the driver's gradient-compression controls stay at their defaults"
  (`clearhdr-design.md:68`; commit message of `57c8fb0`).
- Code: section 4, third row. Core does not write controls +2, +3, +4 (`CameraController.cpp:7034-7037@cinemate-port`
  defines only +0, +1, +5).
- Symptom if a control differs from 500 / 11500 / 6 / 4 or the black level from 50: **preview right, DNG wrong**
  (Core maps libcamera's values to the nearest code of another curve: level errors and banding in a converter).
  That signature, file wrong and preview right, separates it from F1 and F2.
- Settle (needs the Pi): `v4l2-ctl -d /dev/v4l-subdevN --list-ctrls | grep -i -E 'gradient|brightness'` with Clear HDR on.

### F7. Sub-black values are clipped in the 12-bit mode only (confirmed)

- KB: "Codes 0-200 all give 3200" (`clearhdr-design.md:80`); "libcamera itself merges codes 0-200 ... that is not
  recoverable" (commit message of `57c8fb0`). Code: `ccmp_unwrap.cpp:121-122@6b0b49f`.
- 16-bit Clear HDR and SDR keep values below black (16-bit dark frame: median about 3222, `clearhdr-design.md:41`).
- Symptom: deep shadows of 12-bit Clear HDR have a one-sided noise floor; after white balance and a strong lift
  they can tint. Preview and file alike. Small; visible only in near-black areas.
- Settle: histogram of a lens-cap frame in each mode: the 12-bit one has no decoded value below 3200.

### F8. ISO above code 57 leaves the 12-bit combine window (confirmed for the cap, unconfirmed on the port)

- KB: 12-bit ceiling ISO 720, 16-bit ISO 1585 (`lessons/hardware-log.md:507-510`). Cinemate's trap: above the
  window "the merge collapses gradually (peak raw code 4095 to 3188 to 2408 in Cinemate's 12-bit sweep) and every
  knob looks inert" (`sources/2026-10-23-clearhdr16-handoff.md:147`).
- The cap exists in the port (`CameraController.cpp:2976-2978`, `ApertarCoreApp.cpp:5078@cinemate-port`). Last
  confirmed on the Pi 2026-10-28 on Core `8175273` / `6d217c7`, 4K, preview only.
- Symptom if a path bypasses the cap (a preset, the ladder, a held auto value): highlights top out well below
  WhiteLevel 65520, so they render grey or pink in a converter and in the preview; 16-bit at the same ISO is fine.
- Settle (needs the Pi): `get_state` `iso_max` reads 720 in 12-bit Clear HDR; `v4l2-ctl --get-ctrl analogue_gain` <= 57.

### F9. Mode selection traps recorded in the KB (probable)

- Order: `set_raw_bit_depth 16` before Clear HDR is on "stays 12, no error" (`T32.md:7`). The operator can be in
  12-bit Clear HDR while expecting 16-bit.
- Nearest size: "The driver's `v4l2_find_nearest_size` never fails: a missing mode silently becomes the nearest
  one" (`llm/README.md:128`, trap 9). On `cd548ef` the 12-bit Clear HDR list is a sub-range of the SDR list: it
  has no windowed 2x2 crops (`imx585.c:3052-3095@cd548ef`). A crop resolution carried over from SDR lands on
  another mode.
- fps: the startup probe decides `fps_max`; a second sensor changed it from 30 to 25 (`findings.md:155-158`).
- Symptom: wrong size, wrong crop, wrong fps, or an unexpected depth, in 12-bit Clear HDR only.
- Settle (needs the Pi): read `stream=` in Core's `camera configured:` journal line and `list_sensor_modes`.

### F10. The oldest symptom, the dark preview, was never closed (confirmed as a gap; not the differentiator)

- KB: S1. Probable cause: `rpi.hdr` in the tuning file (timeline row 4). `set_tuning_file <path>` is used as given
  in every mode (`llm/README.md:137`, trap 18), and `imx585_clearHDR.json` lives outside git and "must go into
  every image" (`fork-log.md:282`).
- Symptom: Clear HDR dark or pedestal only, preview and file. It would hit 16-bit too, and the owner reports
  16-bit fine, so it does not explain a 12-bit-only fault.
- Settle (needs the Pi): `journalctl -b -u apertar-core | grep 'tuning file:'`; `get_state` `tuning_file`.

### F11. Which libcamera build runs is unsettled (unconfirmed; no effect on the 12-bit curve)

- KB: section 6, C9. Both builds share the same `CcmpUnwrap`. With `QBC_RAW_CPU_WORKER=1` the expansion runs on a
  worker thread (`pisp.cpp:2141@6b0b49f`); the KB tested that switch in 16-bit only (timeline row 18).
- Settle (needs the Pi): `grep libcamera /proc/$(pgrep -nx apertar-core)/maps | sort -u`; `systemctl show apertar-core -p Environment -p DropInPaths`.

### F12. Stale pages that would mislead a fix (confirmed)

- `working/clearhdr-12bit-answer.md` gives the Cinemate recipe (BlackLevel 200, WhiteLevel 63265) with no note that
  it does not apply to this libcamera (C1).
- `architecture/drivers.md` and `llm/flows.md:208` describe driver `e5b74d3` (C10).
- `working/clearhdr-design.md:82` still says Clear HDR forces 4K (C5).
- `drop-frames/README.md:120` and `lessons/hardware-log.md:862` say Log is 16-bit only (C6).
- No effect on the camera. Fix belongs to the KB update task.

## 8. Five-minute checks, in one place

| Check | Command | Needs the Pi |
| --- | --- | --- |
| The belief is still the port's | `git -C /home/user/Apertar-Core diff --stat f60e301 01f170c -- src/cdng/ClearHdrCcmp.hpp` (empty) | no |
| Driver defaults unchanged | `git -C /home/user/imx585-v4l2-driver show cd548ef:imx585.c \| sed -n '37,39p;159p;557,558p;3688p'` | no |
| libcamera expands in place | `sed -n '1821,1823p;3100,3104p' /home/user/tiramisioux/libcamera/src/libcamera/pipeline/rpi/pisp/pisp.cpp` | no |
| No binning in the curve | `sed -n '57,67p' .../pisp/ccmp_unwrap.h`; `sed -n '24,30p'` of `ClearHdrCcmp.hpp`; `sed -n '39,45p' /home/user/tiramisioux/cinepi-raw/cinepi/ccmp_lut.hpp` | no |
| Binned 12-bit Clear HDR is offered | `git -C /home/user/imx585-v4l2-driver show cd548ef:imx585.c \| sed -n '3052,3095p'` | no |
| Log composes in 12-bit | `sed -n '4031,4041p' /home/user/Apertar-Core/src/camera/CameraController.cpp` | no |
| The clip label rule | `sed -n '165,175p' /home/user/Apertar-Core/src/playback/ClipProbe.hpp` | no |
| The expansion engaged, with which numbers | F1's `journalctl` line | yes |
| 2K 12-bit against 2K 16-bit | F2's pair of takes | yes |
| Drops in a 12-bit take | F4's `journalctl` line | yes |
| Live CCMP controls | F6's `v4l2-ctl` line | yes |

## 9. Not covered here

- The relayed user request of this run (reinsert the chip definition for GPIO, because GPIO can come from another
  chip such as a microcontroller) is a Controls code task. It is outside assignment G1 and was not acted on.
- The DNG write path, the players' rendering, MLV levels and the driver registers are other agents' angles. Code
  lines above were read only to pin a KB statement to a ref.
