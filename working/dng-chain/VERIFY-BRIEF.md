# Verification brief (read BRIEF.md first for the repositories, the problem statement and the labelling rules)

You verify ONE hypothesis from M.md (this directory), named in your assignment. Your job is to REFUTE it if you can. Work through all three lenses:
1. CODE REALITY: go to the actual source (grep anchors, read around them) in Apertar-Core (/home/user/Apertar-Core at 92d0970), cinepi-raw,
   cinemate, apertar-ui, the upstream libcamera tree at /home/user/raspberrypi/libcamera (c682979) and check every code claim the hypothesis rests
   on. Report path:line for each check. The kb's own reader reports (R1..R9, S1..S3) are evidence to check, not to trust.
2. EVIDENCE CONSISTENCY: check the hypothesis against every measurement in /home/user/apertar-kb/lessons/hardware-log.md (2026-10-26 to
   2026-11-01), /home/user/apertar-kb/working/drop-frames/README.md and the handbook /home/user/tiramisioux/cinemate-handbook/lessons/hardware-log.md.
   Does any measurement contradict it? Is the proposed test able to settle it?
3. MECHANISM AND DOMAIN: is the kernel / filesystem / drive / libcamera mechanism real and quantitatively plausible? Load WebSearch and WebFetch via
   ToolSearch (query "select:WebSearch,WebFetch") and read primary sources where a kernel or hardware claim is load-bearing. Kernel source:
   https://raw.githubusercontent.com/torvalds/linux/v6.12/<path> or https://raw.githubusercontent.com/raspberrypi/linux/rpi-6.12.y/<path>
   (elixir.bootlin.com and git.kernel.org are not reachable). libcamera upstream is on disk; the Tiramisioux forks are at
   https://github.com/Tiramisioux/libcamera (fetch raw files via raw.githubusercontent.com/Tiramisioux/libcamera/<branch>/<path>).
Verdict: 'refuted' when a load-bearing claim is false or unsupported; 'plausible' when consistent and mechanistically sound but not established;
'confirmed' only when code and evidence establish it. Give corrections (what to reword, which number or ref is wrong) and a better test if the
proposed one is weak. Write your full verification to V/<id>.md and end your final message with a JSON object (nothing after it):
{"id":"H?","verdict":"confirmed|plausible|refuted","confidence":0.0,"reasoning":"...","corrections":"...","refs":["..."],"better_test":"..."}
