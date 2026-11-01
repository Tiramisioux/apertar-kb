# Synthesis brief (read after BRIEF.md)

Nine readers wrote reports in this directory: R1 (cinepi-raw write chain), R2 (cinemate storage/mount/kernel/scheduling/pre-roll/docs/history),
R3 (Apertar write chain), R4 (mounting, exFAT), R5 (evidence pass: kb + handbook), R6 (domain: exFAT internals, NVMe HMB, trim, bandwidth,
writeback, libcamera; may still be missing when you start — say so if it is), R7 (Apertar capture side), R8 (Apertar encoder path and data
rates), R9 (libcamera configuration, PiSP back end, link). Read EVERY available report in full first (they are the evidence), then go back
to the source for anything you build on. Where readers disagree (e.g. R4 says Core writes one write() per frame, R3/R8 say 34 chunked
writes; R1 says Apertar copies on the completion thread, R7 says the copy worker does), settle it in the source and say who was right.

Produce, from your lens but covering the whole question:
1. comparison: a stage-by-stage table of the two chains (cinemate/cinepi-raw vs Apertar drop-frames): sensor/link format and tuning,
   libcamera streams, camera buffers and requests in flight, the hand-off from libcamera's thread, copies, LUT/log/COMP1 work, encoder
   threads, write queue policy, files per frame and syscalls, sync policy, mount options and cluster size, kernel knobs, scheduling, trim,
   pre-roll, stop behaviour, preview paths, and what each difference plausibly means for drops at 4K25 16-bit and 4K50 12-bit.
2. hypotheses: an explicit ranked list (ids <your id>-1, -2, ...) of (a) causes of the residual drops in the two operator cases,
   (b) improvements to Apertar for exFAT on NVMe and on USB SSD (writing and mounting), (c) assessments. Each with: claim, mechanism,
   evidence for and against (with refs), the single A/B test or measurement that settles it on the Pi (knob, command, what to read back),
   expected effect (numbers), risk. Mark anything that merely restates the kb as such. Include hypotheses you consider likely false if the
   operator believes them, so they get verified.
3. assessments: better_in_general, preroll_effect, clearhdr16_residual, sdr50_residual: each a paragraph that says what is established,
   what is inferred, what is unknown.

Write your full synthesis to the file named in your assignment and end your final message with a JSON object (nothing after it):
{"comparison":[{"stage":"...","cinemate":"...","apertar":"...","matters":"..."}],
 "hypotheses":[{"id":"...","title":"...","kind":"cause|improvement|assessment","claim":"...","mechanism":"...","evidence_for":"...",
   "evidence_against":"...","how_to_test":"...","expected_effect":"...","risk":"...","refs":["..."],"priority":1}],
 "assessments":{"better_in_general":"...","preroll_effect":"...","clearhdr16_residual":"...","sdr50_residual":"..."},
 "report_path":"..."}
