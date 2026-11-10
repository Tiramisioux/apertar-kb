# Prognosis before S2 resumes (written 2026-11-10 evening, after the day run)

Changed since the day run: the UI fd fix (`25eeb47`, measured to work), the Core stranded-writer fix (`7e6e2a3`, built,
not exercised), the fill gate keeps 10 % of the card free after every take.

- HDR16: done in S2 (27 fps carried; Log, TDN 25 and lossless+Log out). The runner skips what is recorded and continues.
- SDR12: the meter (44/46/50 fps), then the walk. Card worst 10-s window 596 MB/s; SDR12 at 44 fps needs ~547 MB/s, so the
  card itself becomes the probable limit at 46-48 fps (derived). Probable carried: 44-46 fps.
- HDR12: starts at 30 fps; 12.4 MB/frame x 30 = 373 MB/s, well within the card; the capture side decides (probable 30+).
- SDR12 lossless: walked only if its pre-roll beats the uncompressed edge.
- Sound: expected in every take (UI fix). A silent take counts and gets a full snapshot.
- Card: at most 90 % full after any take; no stall expected (none below 94 % so far).
- S4 (15 min, each mode at its S2 best): HDR16 27 probable pass (27 fps passed 5 min twice); S5 runs only if all pass.
