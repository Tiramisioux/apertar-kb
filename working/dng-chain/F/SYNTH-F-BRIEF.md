# Synthesis brief: the feasibility verdict page

You write `/home/user/apertar-kb/working/dng-chain-feasibility.md`, the answer to the operator's question: "Can we achieve drop-frame-free
(A) 4K SDR 12-bit 50 fps and (B) 4K Clear HDR 16-bit 25 fps on Apertar?" Read, in this order: `FEAS-BRIEF.md`, then every analyst report
F1..F6 and every verification V-F1..V-F6 in this directory (the verifications override the reports where they disagree; where a verification
says WEAKENED or REFUTED, carry the corrected number, not the original), then `../../dng-chain-answer.md` sections 0, 2, 5, 6 for the
earlier conclusions and the E-plan this page must connect to. The work is about Apertar; cinemate appears only as the reference point the
operator raised, never as a goal.

Rules: every number carries its label (measured / derived / estimated / unverified / web) and its source (F<n> §x, V-F<n>, or the kb
file:line). Prefer a measured datum over any model. Where two reports disagree after verification, say so and state which the page
follows and why. Nothing here has run on the Pi; the page must say so once, plainly. Do not invent levers or numbers not in the reports.
Write the skeleton first and fill it section by section, so work survives if you are cut off. Format like the kb's other answer pages
(`../../storage-answer.md`, `../../research-30fps-answer.md`): a header with date, sources and the one-paragraph status, then sections.

Structure:
0. Short answer. For each mode: YES / YES UNDER CONDITIONS / NOT WITH THE CURRENT CONFIGURATION / UNKNOWN, the conditions, the margin,
   the confidence, and the single measurement that decides it. Eight bullets at most. A reader who stops here must have the answer.
1. The chain as budgets. One table: stage; (A) budget, estimated use, margin, label, source; (B) the same. Stages: sensor/link/RP1,
   CFE raw pool and FE config queue (depth 2, from V-F1), serial cycle (IPA + BE incl. TDN + Core callback), CPU, DRAM, writers and
   page cache, exFAT metadata, drive sustained rate and free space (a 10 min (A) take is 373 GB), stall cushion (frames mode vs RAM mode).
2. Mode (A): the two gates (serial cycle; storage over 10 minutes), what the record shows (M3 22.7 ms on 4d5fdd1; the 2 s pre-roll at
   60 fps on d44b177 with probably 8 buffers; no take at 2160 or on the current build; the 2026-10-28 shooting-day clips as a possible
   free datum via DNG clock forensics), the corrected cycle brackets (V-F2), the storage verdict (F4/V-F4), the formats that fit
   (10-bit 518 MB/s, 3840x2076 598 MB/s, lossless), the free-space precondition, and the ordered path to a drop-free take with a stop
   criterion at each step.
3. Mode (B): what the record shows (A0/A1/C0101 clean 10 min; A2; the WebUI-open short takes; Log unverified), the margin (+2.0 to +5.3 ms
   at the A0 load, load-dependent), the A0 protocol, what TDN off adds (19-24 ms), Log's status, and the ordered path.
4. Levers, one table: lever; stage; expected gain with label; cost; risk; how to apply today; exists in 6ef0ddc or needs code (size).
   Order by expected gain per unit cost. Include: no-tdn tuning copies (two files; set_tuning_file; the LIBCAMERA_RPI_TUNING_FILE /
   APERTAR_TUNING_FILE nuance from V-F2: adopted only when no tuning is persisted, then persisted, and a persisted path disables the
   automatic _clearHDR substitution); NoiseReductionMode=Off in start controls (~10 lines; clean per V-F2's kernel reading; V-F6's libpisp
   caveat); WebUI preview pause; 8 raw buffers; FE config queue depth; per-thread FIFO; DONTNEED=sync; O_DIRECT (T24, promoted by V-F6);
   RAM mode; 10-bit; 2076 mode; Log for (B); trim before every series; swap off; speed ramp off; first-take discard; pipelining (fork).
5. Corrections this phase makes to `dng-chain-answer.md` and `dng-chain/STATUS.md`, as a list with the exact old statement and the new one:
   CFE pools are 4/8 not 6/10 (V-F1); jitter tolerance N*T - R (V-F1); FE config queue depth 2 (V-F1); R9's 19-23 ms SDR estimate is
   contested, bracket now -2.7 to >= +2.5 ms (F2/V-F2); APERTAR_TUNING_FILE is not dead but conditional (V-F2); exFAT O_DIRECT i_size_aligned
   statement (F4/V-F4, whichever V-F4 decides); writer-side levers cost 4-10 ms/frame in two takes, not <= 1-3 ms (V-F6); the drive is
   the E27T revision with a small pSLC cache (V-F6/V-F4); the pre-roll ran with 8 buffers (V-F2); 733 MB/s was a 5 s in-cache figure (F4).
6. The decisive tests, in order, each with: what it measures, tool, minimum duration, pass criterion, what it decides, and the E-plan step
   it maps to (E0, E4, E5, E2, ...). Rig-free first (DNG clock forensics of the 2026-10-28 clips; fio sustained-write curve with Core
   stopped), then the 60 s cycle windows, then the 10 min soaks.
7. Open questions and unverified claims that remain after verification.
8. Where the detail is: F1..F6, V-F1..V-F6, with one line each.

Return as final text a compact summary under 400 words: the two short answers, the three decisive numbers, the first three tests.
