# Prognosis before the S2 resume (written 2026-11-10 after night 1)

- HDR16: 28 fps out (capture gaps at 136 s and 153 s). 27 fps: one clean 3-min take; owed: the 5-min take. Prognosis
  (probable): 27 fps carries; 28 fps's gaps were on the capture side, not the card, so 27 is the 3-5 min ceiling
  for HDR16 on this card at 16:9.
- SDR12 (meter start 44/46/50) and HDR12 (start 30): not reached. The card's worst 10-s window (596 MB/s) is above
  SDR12 at 44 fps (547 MB/s, derived) but close; at 46 fps the card itself becomes the probable limit.
- Heat: expect the NVMe near or above 76 C within the first hour of back-to-back takes; the first hourly break
  will give the cooling curve.
- Audio: unless the UI's dmabuf failure is found, expect silent takes after about 25 min (night 1), each a void;
  two voids end the night.
