# Feasibility verification brief

You verify ONE analyst report (F1..F6, named in your assignment) from the feasibility phase. Read `FEAS-BRIEF.md` and `../BRIEF.md` first, then
the report. Your job is to REFUTE its verdicts and its load-bearing numbers if you can. Work through three lenses:
1. CODE REALITY: open every cited `path:line` and check that the code says what the report says. Where the report relies on the Apertar
   libcamera fork (not local), check the upstream tree at /home/user/raspberrypi/libcamera and the kb's fork citations (working/research-30fps/q2, q7)
   and say what remains unverified.
2. EVIDENCE CONSISTENCY: check every measured number against its cited log line in /home/user/apertar-kb/lessons/hardware-log.md,
   /home/user/apertar-kb/working/drop-frames/README.md, the handbook /home/user/tiramisioux/cinemate-handbook/lessons/hardware-log.md. Find any
   measurement the report ignored that contradicts it. Check the arithmetic of every derived number.
3. MECHANISM AND DOMAIN: is each hardware or kernel claim true and quantitatively plausible? Load WebSearch/WebFetch via ToolSearch
   ("select:WebSearch,WebFetch") and read primary sources where a claim is load-bearing (drive specs, Pi 5 bandwidth, libcamera behaviour,
   kernel exfat via https://raw.githubusercontent.com/raspberrypi/linux/rpi-6.12.y/<path>).

Default to "refuted" or "weakened" when you cannot confirm. Do not change the report; write your verdict to
`/home/user/apertar-kb/working/dng-chain/F/V-F<n>.md` with this structure:
1. Verdict per mode on the report's INSIDE/MARGINAL/OUTSIDE call: CONFIRMED / WEAKENED / REFUTED, with the one fact that decides it.
2. Table of the report's load-bearing numbers: claimed, what you found, label, path:line or URL.
3. Errors found (wrong code reading, wrong arithmetic, ignored measurement, unsupported hardware claim), each with the correction.
4. What the report missed that changes the verdict, if anything.
5. The corrected verdict and margin you would state, with confidence.
Return as final text a compact summary under 300 words: the verdict per mode, the decisive fact, the corrections.
