# Long-take campaign, 16-bit 4K Clear HDR: findings (2026-11-07)

Data: `longtakes-2026-11-06/depth4/` (results.csv, samples/, journal/ per take). Rig: CM5 Lite, IMX585, Kingston SKC3000S512G 477 GB
(exFAT, trim on by default), Core `f4a1393`, FE config queue **depth 4**, storage tuning file (8 raw buffers, workers 4, queue 12,
`dontneed=sync`), audio on (USB PnP, format auto). 64 configs, 384 takes, 30 -> 25 fps, stop at the first dropped frame.
Labels: **measured** / **probable** / **unconfirmed**.

## Result

**No config reached a clean fps down to 25 fps** (no 30-min or drive-full pass). The best takes: baseline 453 s at 25 fps, baseline +
WebUI client 446 s, phase lock on + trim off 276 s. (measured)

## What the logs show

1. **Every one of the 384 drops is a capture gap** (CFE had no free raw buffer). No write failures; the drive was at most 37 % full.
   (measured) Four takes also had queue-full drops (lossless, 24-frame queue). (measured)
2. **The write path is not the limit.** Uncompressed takes peaked at 2 of 12 queue slots; no throttle flag at any drop
   (`get_throttled` 0x0 in all 384); Pi 56-66 C, NVMe 33-60 C. (measured)
3. **Drops are single missed frames**: 341 of 556 events lost 1 frame, 209 lost 2, 6 lost 3-4. They are isolated gaps, not
   a stall. (measured)
4. **Time to first drop grows smoothly as fps falls** (uncompressed, Log off, TDN off; median s): 30 fps 2.0, 29 2.8, 28 3.5, 27 5.5,
   26 8.0, 25 27.0. That looks like a loss rate that falls steeply with fps, not a fixed start-up event. (measured; reading it as a
   rate is probable)
5. **Never clean enough to see a plateau.** A fixed 30-min pass would need the rate to fall by a further factor of ~4 below the
   25 fps baseline rate (453 s). The user's floor is 25 fps, so 24 and below were not tried. (probable)
6. **Immediate failure (2-3 s at every fps) with** lossless (fits the ~17.5 fps encoder limit, recipe row 2), **TDN on** (recipe
   row 7) and **Log on**. Frames lost at the stop: unc median 1, unc +Log 4, unc +TDN 6, unc +Log +TDN 7. **Log on failing is
   unexplained**: it writes fewer bytes, so it is not the drive. (unconfirmed)
7. **Long takes**: Pi 60 -> 64 C, NVMe 36-47 -> 50-55 C, CPU 49-54 -> 63-64 %, free RAM flat (no leak), drive 17-36 % full.
   The drops came while Pi ~64-65 C; nothing was throttled. Temperature as a cause is not supported. (measured; cause unconfirmed)
8. **Factor effects are not separable yet** (one take per cell; the baseline itself swung 213 s at 26 fps / 453 s at 25 fps).
   Only the baseline and baseline + WebUI reached 440+ s at 25 fps; trim off (19 s) and phase lock on (35 s) look worse, except
   phase lock + trim off (276 s). WebUI client cost: 446 s against 453 s at 25 fps. (measured, weak)

## Against the earlier recipe

The recipe had 25 fps clean for 10 min on the Corsair drive and 28 fps clean for 3 min with depth 4. Here the same settings drop
at 25 fps after 453 s at best and at 28 fps after ~4 s. Differences: a different drive (Kingston), audio recording, WebUI/HDMI UI
load during the take, and a fresh camera reconfigure before every take. Which one matters is unconfirmed. Depth 2 -> 4 helped
(baseline 25 fps: 74 s -> 453 s, 26 fps: 24 s -> 213 s; one take each, probable).

## Side observation

The touch UI froze its preview and showed "no media" during the campaign (it logs `MESA: error: Export failed` while Core
reconfigures the camera every ~20 s). Core reported `media_state: mounted`, no NVMe errors. UI-side display only. (probable)

## Suggested next steps (not run)

- Repeat the baseline 25 fps take 5 times to get its spread before reading any factor effect.
- Try 24 and 23 fps on the baseline to find where a 30-min take is clean.
- Repeat with the audio off and with the HDMI UI stopped to see what the other load costs.
- Find out why Log on fails at once (it should be the easiest load).
