# Handoff: inspect the 2026-11-01 drop-frames results and course-correct the next tests (Fable)

For: a fresh Fable session on the Mac, in Claude Code with the `apertar-dev` skill, working with Patrik. Written
2026-11-01 23:40 by the session that ran the tests. Paste the block below as the first message, or say "read
`~/Documents/Apertar/apertar-kb/working/handoff-drop-frames-fable.md` and start".

**Status 2026-11-02 (cloud session, desk only):** the analytical half is done: night report section 8 (verdict, answers to the five question groups, test plan B0-B8, code decisions). The Pi tests are for the VS Code session; start at B0 and M1 (copy the `pgscan_direct`/`allocstall_*` deltas of #70-#80 from the 2026-11-01 Mac transcript into section 2). `../tools/drop-frames-2026-11-01/take3v2.sh` prints the per-minute reclaim deltas (M2).

---

/apertar-dev You are the independent test lead for the Apertar drop-frames campaign. The last session reached a
conclusion late at night after several changes of mind; your first job is to check whether it holds, and then to steer
the next tests. You may disagree with it. Patrik decides.

**Goal (Patrik's targets):** 4K Clear HDR 16-bit uncompressed cDNG at 25 fps with 0 lost frames while the touch UI shows
the live picture at full rate with focus peaking and zebra on (first priority); 4K SDR 12-bit at 33 fps (second).

**Read first, in this order** (all in `~/Documents/Apertar/apertar-kb/`):
1. `working/drop-frames/night-2026-11-01.md`: the night report (result, the take-by-take comparison, code/runtime state,
   traps, open questions). Start here.
2. `working/drop-frames/takes-2026-11-01.md` (every recording from Core's journal, numbered; raw lines in
   `takes-2026-11-01.raw.txt`; generator and test scripts in `working/tools/drop-frames-2026-11-01/`).
3. `lessons/hardware-log.md`, the 2026-11-01 entries (what Patrik confirmed), and `lessons/upstream-issues.md` #44.
4. `llm/README.md` §2 and §5 before reading any code (grep anchors; never read the 8-12k-line files whole).

**The claim to test:** the capture losses (single frames missing at capture, `dropped_gap_estimate`; the write queue never
filled) came from page-cache pressure. Core's old default `APERTAR_DNG_DONTNEED=writer` calls `posix_fadvise(DONTNEED)`
right after each DNG write on still-dirty pages (frees nothing, drains the per-CPU LRU lists on every core per frame);
the cache fills and kswapd reclaims during the take; the touch UI's display work is the last straw. Evidence: after a
reboot, `writer` lost 1, 34, 153, 71 per 3 minutes as the cache filled; `sync` (drop after the once-a-second fsync) lost
0 and 0 in 3 minutes, then 25 of 15,023 in 10 minutes (18 in the last minute, drive 97 % full); `sync` plus CineMate's
dirty limits (`vm.dirty_bytes` 1 GiB, `dirty_background_bytes` 256 MiB, `min_free_kbytes` 64 MiB) on an empty drive lost
0 of 15,025 with no kswapd reclaim (take #80).

**Questions to answer before any new change** (write your answers into the night report under a new heading):
- Is `sync` vs `writer` real or chance? n is small and the take-to-take spread was large all evening. What does a sound
  A/B look like (interleaved, same uptime band, same drive fill, enough frames to tell 0.05 % from 0)? Estimate how long it
  takes and propose the order.
- Take #80 changed two things at once (the dirty limits and an empty drive). How do you separate them, and does drive
  fill matter on its own (exFAT near full, the NVMe's state)?
- Which of the evening's UI conclusions (peaking cost, the CPU mask, the DRM display plane, the preview cap) survive once
  the cache pressure is gone? Which UI commits on `drop-frames` should stay, which should be reverted? Keep in mind that
  with `hdmi_external_only=true` the HDMI picture comes from the external-monitor window.
- Is the mechanism right? The per-frame LRU drain was inferred from the code and the README, not measured. Name the
  cheapest direct measurement (for example `perf`/ftrace on `lru_add_drain_all`, or `/proc/vmstat` per second during a take).
- Anything the last session did not consider: the 1782 Mbps CSI link above the RP1 PHY range, the NeoRotary 4 poll (~570
  IRQs/s on CPU0), all camera/GPU/display interrupts on CPU0, the WebUI preview cost, why A0 (2026-10-30) was clean.

**Then:** give Patrik a short verdict (does the claim hold, what is still unproven) and a test plan in order, each test
with its question, setup, duration, and the result that would change the plan. Run the tests one at a time with him.

**State you inherit (details in the night report §4-§5):** Core `drop-frames` @ `adac040` (sync as the default) is on
GitHub and in the Pi's checkout but **not built**; the running Core has `sync` from a `/run` drop-in; the dirty limits
were set by hand with `sysctl`. A reboot drops both, so build `adac040` (`cmake --build ~/ApertarCore-build -j2`, never
during a take) before relying on the default, and make the dirty limits permanent the Apertar way (Core's existing
`APERTAR_MEDIA_TUNE` path and its root helper `scripts/apertar-media-tune`; see the Core README knob table) rather than a
new mechanism. UI `drop-frames` @ `c13b846` (all A/B switches off by default). `main` is untouched everywhere.

**Rules from Patrik for this work:**
- Claude edits and drives the Pi over ssh (`ssh apertar`); Patrik runs everything with `sudo` (restarts, drop-ins,
  sysctl, installs). Give him exact command blocks; say what changed after each step.
- Measuring: nothing else on the Pi during a take (check for `cc1plus|gmake|cmake` before and after; another session
  compiled during two takes last night), WebUI closed (the scripts refuse with a client on `:8000`), 3- or 10-minute takes,
  per-minute counts; restore Patrik's settings after a take (his ladder: rung 1 4K Clear HDR 16-bit lossless JPEG <= 25,
  rung 2 4K SDR 12-bit lossless JPEG 25-30; note that 16-bit lossless encodes at ~17.5 fps). Watch the drive fill (each
  10-minute take writes ~250 GB of a 932 GB drive); Patrik decides when to format.
- Commits: `<area>: <imperative>`, `Why:` / `What:` / `Tested:`, Co-Authored-By trailer, "User" not names; one commit per
  feature; a fork-log row for every commit; push only when Patrik asks. KB: label claims confirmed / measured / probable;
  a hardware-log entry only after Patrik confirms the reading.
- Prefer the least intrusive change consistent with Apertar's existing code (extend an existing knob or setting before
  adding one).
