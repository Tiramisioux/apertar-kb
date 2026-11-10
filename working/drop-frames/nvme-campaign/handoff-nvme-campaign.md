# Handoff: NVMe 4K campaign (revised 2026-11-10)

One prompt for a Claude Code session on the Mac (VS Code, `/apertar-dev`), driving the Pi over ssh. Plan:
[plan.md](plan.md), its "Revision 2026-11-10" section first. Build work: [build-list.md](build-list.md) (section H, then section R).
Patrik edits the defaults below before pasting.

```text
/apertar-dev Run the NVMe 4K campaign on the Corsair MP600 Mini card(s) as planned in apertar-kb
working/drop-frames/nvme-campaign/plan.md, starting with its section "Revision 2026-11-10", which wins where it conflicts with
the rest. You build what is missing in the runner first, then run the stages night by night. Nobody answers questions during a
night: every decision below is pre-made; anything not covered is recorded in status.md and skipped, never asked.

WHY: on the Samsung T7 (SSD nights 1-2, working/drop-frames/ssd-campaign/README.md) a flat clip folder made Core's per-frame cost
grow until a 30-min take stopped near minute 29; split at 5000 frames per folder the same take was clean 4 times of 4. Split is
now the camera default. The NVMe question is which 4K modes and fps hold 30 min drop-free, split as Patrik shoots, and whether a
flat folder would also hold (one control per mode). Night 2's four dropped frames were three copy-slot drops at a part-folder
boundary (fixed in Core e298d4a's parent 8ec2f1a) and one numbering gap with no lost picture (now logged as "frame index jump").

READ FIRST (Mac ~/Documents/Apertar/apertar-kb/): working/drop-frames/nvme-campaign/plan.md (the revision section, then §0, §3,
§6, §7, §9, §10, §11), build-list.md (H and R), working/drop-frames/ssd-campaign/README.md (Night 1, Night 2, the dropped frames,
the folder-budget formula), ssd-campaign/night2/{night2.sh,poweroff-after-night2.sh,merge-test-after-night2.sh} (the patterns to
copy), the docstring of working/tools/longtakes.py, fork-log.md. Then run the skill's status script.

STATE AT HANDOFF: Pi Core on branch clip-split at e298d4a, built; Patrik restarts Core on it before S0 (check /proc/<pid>/exe
mtime and an "index_jumps=" field in the first smoke take's stats line). Camera defaults: frames_per_folder 5000, merge on.
Runner ~/longtakes/bin/longtakes.py = KB cf0b37e: it does NOT yet have the plan's tiers, GO sentinels, fill gate or card
detection (build-list H) nor section R. The T7 may still be mounted: the campaign needs the Corsair card on /media/RAW (check
model and serial before any write; a T7 or any other medium = stop and record).

PHASE 1, BUILD (desk + Pi, no takes): implement build-list H (as far as the plan's S0-S6 need it) and R1-R5 in
working/tools/longtakes.py and nvme-campaign/scripts/; test each with --dry-run on the Mac and one 20 s smoke take on the Pi
(its clip deleted by the runner); commit in the KB, one commit per item group; copy to ~/longtakes/bin with an md5 check and a
.bak of the old file. Then stop and tell Patrik in five lines what S0 needs from him.

PHASE 2, S0 WITH PATRIK (he is present; he runs every sudo command, you give them exactly): plan §6 S0 with the revision applied.
Patrik offloads his footage first. The drop-in armed, the timers masked (--runtime), the merge off, frames_per_folder 5000.

NIGHTS (S1 ... S6, then Part B per card, plan §6 and §10): one night = one chain script under nvme-campaign/scripts/ started as
ssh -n apertar '( setsid nohup bash <chain> </dev/null > ~/nvme-campaign/<night>.log 2>&1 & )', with 10 min idle between runs,
the merge off at its start and on at its end, and the power-off watcher started right after it:
ssh -n apertar '( setsid nohup bash ~/nvme-campaign/poweroff-after-night.sh <chain pid> </dev/null > ~/nvme-campaign/<night>-poweroff.log 2>&1 & )'.
THE PI POWERS OFF AFTER EVERY NIGHT AND AFTER THE LAST ONE, through Core's power_off_system, only after: nothing recording, no
writes pending, the restore list written and read back (frames_per_folder 5000, merge on, settings as found). Patrik powers it on;
each new night starts with his re-arm of the drop-in and the timer masks. No @reboot crontab (denied; do not work around it).
Before a night that needs a GO sentinel (plan §10), stop and ask Patrik for it in the session, not during the night.

PRE-APPROVED (by starting this prompt): writes to the campaign card within the plan's 10 TB cap; deleting the runner's own clips
through POST /api/media/delete?kind=folder&id=<name> (database-keyed, never a glob, never rm); KB commits and pushes of the KB;
~/longtakes/bin and ~/nvme-campaign on the Pi overwritten with the KB's tools. NOT approved: sudo, formatting, editing Core
source or pushing Core/UI, touching any folder on the card the database did not create, defaults-pisp or installed libcamera
files, the timecode mechanics.

DURING A TAKE: nothing else on the Pi (no journalctl, no listings, no builds, WebUI closed). Between takes: cat status.md only.
Commit messages say "User", not names, and end with the Co-Authored-By line from your session's attribution reminder.

AFTER EACH NIGHT (when Patrik has powered the Pi on): pull the night's results into nvme-campaign/ (results, runner.log, the
per-take journals, samples, the night and power-off logs), write the findings in the plan's pages (prognosis-S<n>.md,
findings.md) with measured / derived / probable labels, note every numbering_gap and boundary drop separately, update fork-log
if a Core commit was involved, push the KB, and tell Patrik the result in ten lines with the next night's GO question.

AT THE END: every campaign clip deleted through the media route, fstrim, the restore list read back, the timers unmasked, the
merge on, frames_per_folder 5000, a final findings.md with the 30-min recipe per mode (split, and the flat verdict per mode),
the Pi powered off by the watcher, and a summary for Patrik: what he disarms (drop-in, sudoers helper).
```
