# v2 rules adopted from the statistics critique (C1), to merge into plan v2 section 7 and the stage table

Adopted (with the critic's finding number):

- F1 Walk the record's bracket, not the mode top: HDR16 uncompressed 25-29 fps starting at 28; SDR12 uncompressed from a meter take at 50 fps
  then capacity - 1 / - 2; HDR12 from 30 (no record). Step 1 fps inside the bracket. Every screening verdict needs two concordant takes
  (2 clean = clean at 3 min; 2 drops = the cell is out; 1-1 = a third take decides). The take still stops at its first drop (R4); the cell's
  elimination waits for its confirmation take, which costs only its time-to-drop.
- F2 An unscored 60-s warm-up take (same mode, the arm's fps) after every Core restart, reboot and mode switch, stored as `warmup`;
  `takes_since_restart`, `uptime_s`, MemFree, buddyinfo order-8 count on every take record; a lever pair never starts a block.
- F3/F10 Controls: every baseline take at the block's edge fps is a control (the walk produces them); one control at the start and one at
  the end of each mode block at the edge fps; "better" = beats every pooled control AND matches the lever's pre-registered direction AND
  replicates in a second pair (ABBA); "no difference at 3 min" is "not shown (n = 1 pair)", not terminal; at most one lever variant per
  mode goes to the long tiers (best + runner-up cap); if the end control differs from the start control by more than the pooled spread,
  the block's lever verdicts are flagged "drift".
- F4 Split design: drop the 15-min split pair; at 15 min one unsplit take per mode, reading Core's CPU slope (the in-take c) and the buffer
  curve as the directory meter; at 30 min (or fit) UNSPLIT FIRST; the split member runs only if the unsplit take drops late with the directory
  signature, or as the mode's soak take (the A/B in the conservative order, no extra bytes). Pre-registered attribution signatures per
  late drop: Core CPU slope at the probe's c + buffer rising in the last minutes + flat device latency -> directory; device write ticks per
  write rising with fill -> drive state; temperature rising with latency -> heat; dirty/writeback KB rising -> page cache; none of these ->
  capture side. One pair per mode gives "consistent with" readings only; the strong statement is the probe's c plus the in-take c.
- F5 Budget: keep the record's `buffer_ram_fraction 0.6` / `buffer_ram_floor_mb 512` (every take on record ran at ~1.4 GB) unless the
  fixed-MiB key exists (then 1,400 MiB); log `queue_budget` per take; report every buffer_full as seconds of input absorbed (budget / rate),
  never raw seconds; read the regime from the counters AND the buffer curve.
- F6 No fitted log(T) prognosis on the capture side. The next fps comes from the failing take's mechanism: a steady back-end deficit gives
  the capacity directly (fps_c = 1000 / cycle_ms, be_overlap-style reading of the per-second samples), rare single frames mean step 1 fps
  with two concordant takes. The prognosis is a survival table per cell: clean exposure (frames, pooled across tiers of the same cell), its
  95 % rate bound (3/n), the losses that bound allows in a 30-min take, the model expectation with its label and unmeasured terms.
- F7 A pre-registered claims table (claim, evidence needed, label). After one clean 30-min take: "recorded once at these settings; rate
  < 6.7e-5 per frame (95 %), up to 3 losses per 30 min still compatible"; after two: "2 of 2; rate < 3.3e-5". Never "30 min drop-free in
  all 4K modes" as a property. The single most valuable extra take: the second 30-min take of each mode's winning arm (as the split soak).
- F8 Meter takes: fps set from the budget (overshoot 5-10 %, 30-60 s long), the integral identity (sum of fps - drain = final buffer
  level) and the device cross-check (/sys/block sectors per second) part of the take record; the smoke test must show `buffer_used` at
  1 Hz and byte resolution before any capacity number is believed; capacity reported with its window and spread, not "to 1 %".
- F9 Honest labels: crops "predicted from the full-frame result, untested beyond 3 min" unless a 30-min crop take is bought; the CFe
  results "one take per card".
- F11 Lever takes with a known outcome are removed: TDN on at the edge (deterministic failure) becomes ONE unlogged TDN-on 3-min take at
  25 fps (tests the instrumentation hypothesis of O1: 0-2 lost supports it, >= 10 confirms TDN off for real use); phase lock at most one 60-s
  probe if the owner wants the 11-04 {d, d+1} fix exercised, no bearing on elimination; compression arms get a manual `storage_preroll`
  reading first (encoder capacity, ~1 GB each: HDR16 lossless 16.84 fps, SDR12 lossless 48.13 fps already on record), then 3-min takes
  only for arms whose capacity exceeds the uncompressed edge (SDR12 lossless; HDR16 lossless + Log if its pre-roll says > 25 fps).
- F12 State the elimination reasoning: under every known mechanism the hazard grows within a take (files, fill, heat, process age), so a
  drop at t < L implies the arm is out at L and above; a single late frame is repeated once (F1); reproduced = out for the goal whatever the
  mechanism; not reproduced = both recorded, the arm carried.

Minimum design (C1 §2), to compare with v1 §6/§8: ~70 takes, 8.5-11 TB on the test card; warm-ups ~250 GB; the S2 walk ~800 GB;
levers ~900 GB; controls ~400 GB; S3 ~400 GB; S4 one unsplit take per mode ~1.2 TB; S5 unsplit first ~2.3 TB (+ MLV only if both drop
late); the soak as the split variant ~2.3 TB; the CFe transfer on the cards. On the 500 GB Kingston the long tiers are the fit lengths, so
the test-card total is lower (~6-8 TB); the 30-min takes move to the Corsair cards.
