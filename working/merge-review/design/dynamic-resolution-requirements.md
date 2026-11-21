# Dynamic resolution: the owner's requirements (2026-11-21)

Collected from Patrik's messages of 2026-11-21, in order; a later line wins over an earlier one.

1. The user-defined Mode Ladder goes. It becomes **"Dynamic resolution"**: automatic, **on by default**. The ladder pane
   stays, greyed out (no editing): it shows the current limits and why.
2. Purpose: it automatically gives the user the known limits, and applies them.
3. Order when the user raises the fps past a threshold: **first the resolution is lowered; after that the bit depth is
   lowered; after that the mode goes from HDR to SDR** (Clear HDR to normal on the IMX585). Bit depth and HDR/SDR are
   kept as long as possible.
4. Thresholds at the fps steps **25, 30, 33, 50, 60, 70, 80, ...** (increments of 10 above 60), conservative.
5. **Sensor agnostic**: the caps use only fps, resolution and (IMX585) HDR/SDR.
6. Limits are for **30-minute sustained takes**, assuming a **hot NVMe**. They depend on the **storage type** and the
   **Pi version**.
7. Only activated modes are used.
8. Levers are taken into account (TDN, phase lock, audio, WebUI client, aids, Log, split): the limit depends on them.
9. Dynamic resolution may also control **TDN**, as an optional on/off switch.
10. Every lever's switch gets a brief info line: how it affects performance and when it is best used.
11. The clip-folder split becomes **off / on / automatic**; automatic engages it only when the chosen fps and compression
    need it.
12. Use the latest findings in the KB: `working/drop-frames/estimator-campaign/pre-analysis.md`,
    `working/drop-frames/nvme-campaign/findings.md` (P6 warm takes: pauses from 108-190 GB), the T7 SSD campaign.
