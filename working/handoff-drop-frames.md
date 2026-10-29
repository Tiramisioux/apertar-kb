# Handoff: fewer dropped frames in Apertar + CineMate Log (Mac, Claude Code in VS Code)

For: the next `apertar-dev` session on the Mac, in Claude Code inside VS Code, with Sonnet workers
for the scoped tasks. Written 2026-10-29 in a cloud session from source. Paste the part below the
line as the first message, or say "read `~/Documents/Apertar/apertar-kb/working/handoff-drop-frames.md`
and start".

The project page with the evidence and the design is `working/drop-frames/README.md`. This file is
the work order.

---

You are driving the drop-frames project on Apertar-Core from the Mac. Read, in this order:
`~/Documents/Apertar/apertar-kb/llm/README.md`, `working/mac-driven-loop.md`,
`working/drop-frames/README.md` (the evidence, the plan and the Log design), then
`working/cinemate-lessons.md` §1 (method rules). Then run
`~/.claude/skills/apertar-dev/scripts/apertar_status.sh` and report the Core branch tips on the Mac,
the Pi and GitHub before anything else.

## Patrik's rules for this effort

- **Claude edits; Patrik decides when.** He has asked for this work to be made directly (not
  tutorial-first). Confirm that at the start. Say what changed after each edit; verify with a
  read-only check.
- Work on Core branch **`cinemate-port`**. Commits: `<area>: <imperative>` title, `Why:` / `What:` /
  `Tested:` body, `Co-Authored-By` trailer. One change per commit, each behind its env knob or
  setting so the A/B matrix keeps working. A fork-log row for every commit.
- The loop (`working/mac-driven-loop.md`): edit and commit on the Mac, push to the Pi's staging
  branch (`git push ssh://apertar/home/pi/ApertarCore cinemate-port:cinemate-port-mac`), on the Pi
  `git merge --ff-only cinemate-port-mac`, build on the Pi (`cmake --build ~/ApertarCore-build -j2`),
  never while a take runs. Publish to GitHub only when Patrik asks (`apertar_publish.sh`).
- **Patrik runs** `sudo`, service restarts, drop-ins, the sudoers install, reboots. Give him the exact
  command block each time.
- Measurements on the Pi: `bash ~/apertar-kb/working/tools/takes.sh N secs` with nothing else running
  on the Pi; then `ssh apertar "journalctl -u apertar-core --since '-15min' | grep -E 'drop\[|recording stats|synced to the medium'"`.
  Every result goes to `lessons/hardware-log.md` as a dated entry (Tested / Seen / Why / Confirmed by)
  only after Patrik confirms the interpretation.
- Losing in-take fsync is **approved by Patrik** ("I can lose fsync if we need to"). The stop-time
  `syncfs` and the audio raw fsync stay.
- Do not copy cinepi-raw or cinemate code into Core. Port the mechanism and the numbers; cite the
  source in the commit body.

## How to use the Sonnet workers

Spawn one worker per task below with the Agent tool (model `sonnet`), one at a time unless the table
says they are independent. Each prompt must contain: the goal; the files and **grep anchors** (not
line numbers); the exact change; the host check it must run; what to return. Workers return a diff
summary and the paths they touched; **you** review the diff against the design, run the host checks
again, commit, push to the Pi and hand Patrik the build/restart/test block. Never let a worker commit,
push, or touch the Pi.

Host checks available on the Mac (no aarch64 libcamera here): `g++ -std=c++20 -fsyntax-only` on a
header with a tiny test main (pattern: `working/tools/media_profile_test.cpp`); `python3 -c` for any
JSON/table; `git diff --stat`. Everything else is proven on the Pi.

Give every worker this preamble:

```text
You are a worker on Apertar-Core (~/Documents/Apertar/Apertar-Core, branch cinemate-port). Read
~/Documents/Apertar/apertar-kb/llm/README.md §2 and §5 first: find code with grep anchors and read
~100 lines around a hit; never read CameraController.cpp or ApertarCoreApp.cpp whole. Make exactly
the change described, nothing else. Do not commit, do not push, do not run anything on the Pi. When
done, return: the files touched, a unified diff, the host checks you ran with their output, and any
place where the code differed from what the task assumed.
```

## Step 0 (Patrik + you, no code): the A/B matrix

Goal: learn **which counter** carries today's drops and which knob stops it. 4K, 25 fps, Clear HDR
16-bit, uncompressed, same card at < 50 % full, 10 minutes per run, Core idle between runs.

Prepare a systemd drop-in Patrik installs once (he edits the `Environment=` line between runs):

```bash
# Patrik, on the Pi
sudo mkdir -p /etc/systemd/system/apertar-core.service.d
sudo tee /etc/systemd/system/apertar-core.service.d/ab-test.conf >/dev/null <<'EOF'
[Service]
Environment=APERTAR_MEDIA_SYNC_MS=1000 APERTAR_DNG_WRITEBACK=1 APERTAR_CDNG_QUEUE_FRAMES=12 APERTAR_RAW_CAMERA_BUFFERS=8
EOF
sudo systemctl daemon-reload && sudo systemctl restart apertar-core
```

| Run | Environment line | Isolates |
| --- | --- | --- |
| A0 | the defaults above | baseline: which `drop[...]` counter moves |
| A1 | `APERTAR_MEDIA_SYNC_MS=0 APERTAR_DNG_WRITEBACK=1` | the once-a-second fsync |
| A2 | `APERTAR_MEDIA_SYNC_MS=0 APERTAR_DNG_WRITEBACK=0` | all in-take sync (kernel writeback only) |
| A3 | A2 + `APERTAR_CDNG_QUEUE_FRAMES=64` | queue depth (4× cushion) |
| A4 | A3 + `APERTAR_RAW_CAMERA_BUFFERS=10` | camera buffers |
| A5 | A4 + `APERTAR_MEDIA_TUNE=1` (needs §W3's install block first) | kernel knobs |

Record per run: frames written/expected, each `drop[...]` total, `peak_queue`, stop `syncfs` ms,
`grep -E 'nr_dirty|nr_writeback' /proc/vmstat` sampled by `working/tools/writeback_watch.py`.
Write one hardware-log entry for the matrix. Then pick the order of W1–W5 from what moved; the
default order below assumes `queue-full` and `capture-gap` both appear.

## Workers (in order; W4 and W5 are independent of W1–W3)

### W1: RAM-bounded write queue that blocks instead of dropping (plan item 1)

- Files: `src/camera/CameraController.cpp`, class `DngRecordingQueue`. Anchors: `defaultQueueFrames`,
  `maxQueuedFrames_ = unsignedEnvValue(`, `bool hasCapacityForFrame(`, `bool enqueue(std::vector<uint8_t> rawBytes`,
  `void copyLoop()`, `acquireRawBuffer(`, `pooledRawBytes_`, `struct Stats {`, `currentQueueDepth`.
  `src/ApertarCoreApp.cpp` anchor `\"recording_stats\"` or the `get_state` writer near `\"recording_format\"`.
- Change: add `queueBudgetBytes_`, computed in `start()` from `MemAvailable` (`/proc/meminfo`) ×
  `APERTAR_CDNG_QUEUE_RAM_FRACTION` (default 0.6), minus 512 MiB floor, capped by
  `APERTAR_CDNG_QUEUE_FRAMES` × frame bytes (raise that env's max from 64 to 1024, default = budget).
  `enqueue` counts bytes; when `queuedBytes_ + frameBytes > budget`, the **copy worker waits** on `cv_`
  (bounded wait, 5 s → treat as the existing write-stall path that ends the take as media error) instead
  of dropping; `hasCapacityForFrame` on the completion thread keeps returning true while the copy-slot cap
  holds (that cap is the only drop left). Add `queueBytes`, `queueBudgetBytes` to `Stats` and to the
  stats log line and `get_state` (`queue_bytes`, `queue_budget_bytes`). Keep the raw pool from growing
  past the budget (`acquireRawBuffer` recycles beyond it).
- Why this matches cinepi-raw: `cinepi/dng_encoder.cpp` anchors `RAM_FRACTION = 0.90` and
  `ram_cv_.wait`; the capture loop's `RAM pool exhausted` stop in `cinepi/cinepi_raw.cpp`. Cite both.
- Host check: `g++ -std=c++20 -fsyntax-only` is not possible for this file (libcamera); return the diff
  and a 20-line walkthrough of the wait/notify pairs (who notifies `cv_` after a write completes).
- Pi test: A2 environment + the build; `takes.sh 1 600`; expect `dropped_queue_full=0`, `queue_bytes`
  peak reported, no deadlock at stop (stop within 2 s + syncfs).

### W2: no in-take sync by default (plan item 2)

- Files: `src/camera/CameraController.cpp` anchors `APERTAR_MEDIA_SYNC_MS`, `APERTAR_DNG_WRITEBACK`,
  `static bool startWritebackPerFrame()`, `void syncLoop(`, `void noteWrittenFile(`.
- Change: `APERTAR_MEDIA_SYNC_MS` default 1000 → 0; `APERTAR_DNG_WRITEBACK` default true → false.
  `syncToMedium()` at stop unchanged; the audio writer's once-a-second raw fsync unchanged
  (`src/audio/AudioRecordingSession.cpp`, anchor `fsync`). Update the three comments that say "once a
  second" so they describe the opt-in. README: the pulled-card promise changes from "~1 s" to "up to the
  kernel's writeback window (W3 bounds it to ~1.5 s + the dirty cushion)".
- Host check: `grep -n 'unsignedEnvValue("APERTAR_MEDIA_SYNC_MS"' src/camera/CameraController.cpp`
  shows the new default.
- Pi test: A0 environment line removed (defaults now = A2); `takes.sh 1 600`; then one pull test
  (T28 protocol) and count readable frames: expect fewer than before, and the number goes into the
  hardware log as the new promise.

### W3: media tuning on by default, installed by the repo (plan item 3)

- Files: `src/ApertarCoreApp.cpp` anchor `APERTAR_MEDIA_TUNE` (the gate from `e9dd6b2`);
  `scripts/apertar-media-tune`; `config/apertar-media.sudoers`; `config/apertar-media.tmpfiles.conf`;
  `README.md` install section; `CMakeLists.txt` if there is an install target for `scripts/`.
- Change: gate becomes "on unless `APERTAR_MEDIA_TUNE=0`"; Core logs one line when the helper is missing
  or `sudo -n` refuses (it already does: keep it, make it say the install command). Add `install/` steps
  or a `scripts/install-media-tune.sh` that installs the three files. In the helper: the `usb-storage`
  and `usb-uas` rows keep their 256/512 MiB cushions; add a `cfe` alias to `pi-nvme`. Nothing else.
- Host check: `sh -n scripts/apertar-media-tune`; `visudo -cf config/apertar-media.sudoers` if available.
- Patrik's install block (give it verbatim):

```bash
sudo install -m 0755 ~/ApertarCore/scripts/apertar-media-tune /usr/local/libexec/apertar-media-tune
sudo install -m 0440 ~/ApertarCore/config/apertar-media.sudoers /etc/sudoers.d/apertar-media
sudo install -m 0644 ~/ApertarCore/config/apertar-media.tmpfiles.conf /etc/tmpfiles.d/apertar-media.conf
sudo systemd-tmpfiles --create && sudo systemctl restart apertar-core
# proof: the values the kernel actually holds
cat /proc/sys/vm/dirty_bytes /proc/sys/vm/dirty_background_bytes /sys/block/nvme0n1/queue/scheduler
```

- Pi test: `takes.sh 1 600` with W1+W2; read the sysctl values back (the handbook's "a default is a
  claim" rule).

### W4: cached buffers for SDR raw, 8 of them (plan item 4; independent)

- Files: `src/camera/CameraController.cpp` anchors `kConfiguredBufferCount = 4`,
  `kClearHdrBufferCount = 8`, `unsigned int rawCameraBufferCount(`, `const bool cachedRaw =`,
  `allocateCachedBuffers(`.
- Change: `kConfiguredBufferCount` 4 → 8 for raw formats (H.264/ProRes counts untouched); the cached
  condition gains `|| rawStreamInfo_.packing == PixelPacking::Unpacked` for SDR when
  `recordingCapabilities().rawCompression` (Pi 5). Log the heap used (the line `RAW buffers: CPU-cached
  heap=` exists). The held-request cap stays `buffers-2`.
- Host check: none possible; return the diff plus the CMA arithmetic for 4K 16-bit (8 × 16.9 MB) and
  12-bit (8 × 12.4 MB, or 8.3 MB for COMP1).
- Pi test: `grep Cma /proc/meminfo` before/after a restart in SDR 12-bit 4K; `takes.sh 3 60` at 50 fps
  12-bit (T34 M3 case): expect `dropped_copy_slot=0`.

### W5: scheduling parity (plan item 5; independent, Patrik installs)

- Files: `scripts/start-apertar-core.sh`; `config/apertar-core-capture-priority.conf` (add
  `LimitRTPRIO=80`); README.
- Change: in the start script, when `APERTAR_RT=1` and `chrt -f 70 /bin/true` succeeds, `exec chrt -f 70
  ionice -c2 -n0 taskset -c 1-3 "$CORE_BIN" ...`; else log one line and exec as before. Keep the
  `nice -5` code in `requestComplete` (harmless under SCHED_FIFO).
- Source for the numbers: cinemate `src/module/cinepi_multi.py` `run()` and the unit's
  `LimitRTPRIO=80`; cite them.
- Patrik's block: install the drop-in, `daemon-reload`, restart; proof: `ps -eLo pid,tid,cls,rtprio,comm | grep apertar`.
- Pi test: `takes.sh 1 600` with everything on; watch the WebUI preview during the take (open question 4).
  If the WebUI stalls, fall back to SCHED_FIFO on the completion + copy threads only
  (`pthread_setschedparam` in `requestComplete` and `copyLoop`), a second commit.

### W6: CineMate Log for Apertar (plan item 6), four workers in sequence

Design: `working/drop-frames/README.md` §4. Each worker gets that section pasted in.

**W6a, the curve (pure header).**
- New `src/cdng/LogCurve.hpp` (+ `tools/log_curve_test.cpp` host test): params (mu, black, white,
  source bits, target bits, footroom codes, footroom lsb), `encodeCode`, `decodeLevel`, dense
  `forward[2^source]` / `inverse[2^target]`, `buildComposed(expansionTable)` for the 12-bit Clear HDR
  source. Port the math from cinepi-raw `cinepi/log_lut.hpp` (mu-law above black, linear footroom
  below, `nearbyint`, bin-centre decode); constants per depth pair from a generator script
  `tools/gen_log_curve.py` committed next to it (mu and footroom per pair; black/white come from Core's
  tables at runtime). Property tests in the host test: monotonic, `inverse[forward[L]]` within 1 LSB
  of L above black for every L, inverse size = 2^target, last entry = white.
- Host check: `g++ -std=c++20 -O2 tools/log_curve_test.cpp -o /tmp/lct && /tmp/lct` passes.

**W6b, the setting, command, state, persistence, presets.**
- Files: `include/apertar/core/Types.hpp` (anchor `enum class CdngCompression`), `src/ApertarCoreApp.cpp`
  (anchors `"set_cdng_compression"`, `"set_raw_bit_depth"`, `\"raw_bit_depth\"` in the state writer,
  `apply_preset`, the command list string `\"set_cdng_compression\",`), `src/camera/CameraController.cpp`
  (anchor `setCdngCompression`, persisted load near `cdngCompression` in `CaptureSettingsPersister`),
  `src/camera/ModeLadder.hpp` (anchors `knownCompression`, `WIDTHxHEIGHT:BITS:hdr|sdr`).
- Change: `enum class CdngLog { Off, Auto, Bits12, Bits10, Bits8 }` + `toString`/`fromString`;
  `set_cdng_log value=`; refusals in H.264/ProRes only (Log combines with every compression and with
  Lossy, Patrik's rule); state `cdng_log`, `cdng_log_bits`,
  `cdng_log_available`; conf key `[camera] cdng_log`; carried across formats like `fps_phase_lock`
  (anchor `a56eae7` pattern); preset allow-list; ladder sixth field `log|log10|log8` and `log_bits` in
  the ladder JSON; `estimatedRawBytesPerSecond` uses `cdng_log_bits`.
- Host check: none for C++; return the diff and the command-list diff.

**W6c, the encoder path.**
- Files: `src/camera/CameraController.cpp` anchors `compressClearHdrFrame(`, `mapCodes12`,
  `struct PendingCopy`, `copy.view.data = rawData`; `src/cdng/CdngEncoder.cpp` anchors
  `metadata.linearizationTable`, `whiteLevel(layout.bitDepth)`, `writeDngRowBytes`;
  `src/cdng/CdngEncoder.hpp` `struct Metadata`.
- Change: in `copyLoop`, after the memcpy (and after `compressClearHdrFrame` is *replaced* by the
  composed curve when log is on in 12-bit Clear HDR), apply `LogCurve::forward` per sample into the
  same buffer; set `copy.view.bitDepth` to the target; attach the inverse table to the job's metadata;
  the writer packs with the existing 8/10/12-bit row packers; `BlackLevel` stays the linear value.
  Lossless JPEG consumes the log codes unchanged. **Lossy + Log**: in `src/lossydng/LossyDngEncoder.cpp`
  (anchors `buildCompanding`, `cachedGradation_`, `outputMetadata.linearizationTable = inverseQuantized_`)
  the square-root companding is replaced by the log curve at the target depth when Log is on, the ratio
  quantisation and SOF3 run unchanged on the log codes, and the file's table is the log inverse composed
  with the quantisation. One companding per file, never two.
- Host check: none; return the diff and a table of bytes per frame for 16→12, 12→10, 10→8 at 3840×2160,
  uncompressed and at Lossy 3:1.
- Pi test: one 10 s take per pair; `exiftool -LinearizationTable -BlackLevel -WhiteLevel -BitsPerSample`
  on a frame; open in Resolve (open question 5); then `takes.sh 1 600` at 16→12.

**W6d, the two UIs.**
- WebUI: `src/web/WebControlPage.cpp` anchors `settingsCdngCompressionSelect`, `settingsRawBitDepthNote`,
  `dispatchCdngCompressionSelection`, `ladderCompressions`, the resolution badge (anchor `16-bit` near
  `8492488`'s change). Add the Log storage select (live in every compression, Lossy included), the
  badge suffix, the `LOG` pill on the Live preview row, the ladder editor's log column.
- Touch UI (Apertar-UI, branch `cinemate-port`): `qml/SettingsPage.qml` `recordFormatComponent`
  (anchor `applyRawBitDepth`), `src/ApertarControlBridge.cpp` (anchor `applyCdngCompression`),
  `qml/CameraPage.qml` `formatDisplaySubtext`. Add `applyCdngLog`, the row, the subtext.
- Host check: `node -e` syntax check of the extracted JS is not practical; return the diff; Patrik
  checks the page.

## After each worker

1. Review the diff against `working/drop-frames/README.md`; rerun the host checks yourself.
2. Commit on the Mac (`cinemate-port`), fork-log row, push to the Pi staging branch, give Patrik the
   merge/build/restart block, wait for his test report.
3. Hardware-log entry (Patrik confirms the interpretation), `tutorials/progress/T35.md` via
   `tutorial.py log` once T35 exists.
4. Update `working/drop-frames/README.md` §3 status column and §5 open questions.

## Done means

See `working/drop-frames/README.md` §3 "Done means". Then: `apertar_publish.sh` on Patrik's word,
and a fork-log pass marking which commits are `offer` upstream (the Log option and the RAM-bounded
queue are candidates).
