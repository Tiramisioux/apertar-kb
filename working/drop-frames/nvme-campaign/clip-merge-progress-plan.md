# Clip merge progress: plan (2026-11-09)

Goal (User): see the merges happen in real time, so it is clear **when the card can come out**: the current clip and
all clips still to merge. Playback must keep working on a split clip and on one that is being merged.
Base: Core clip-split (b5e9e68 on the Mac: the split/merge settings), UI 53fe704. Nothing here is built yet.

## Where it shows

| Place | What |
| --- | --- |
| WebUI, settings, Media card (under "Merge split clips") | two bars: **current clip** (C0004, 62 %, 2,812 / 4,503) and **all clips** (3 clips, 40 %, about 4 min left) |
| WebUI, first page, System, Storage tile ("Space left") | a second thin blue bar under the space bar: all clips; the sublabel reads "Merging 3 clips · about 4 min" instead of "Media root" |
| Touch UI, Media section, first card (under Merge Split Clips) | the same two bars as the WebUI |
| Touch UI camera page, MEDIA line (the "min" value), and the HDMI monitor's minutes (ExternalMonitorWindow) | when the merge is on and a clip waits: a **blue pill behind the minutes**, filled left to right by the all-clips progress (the PRE-ROLL blue of StatusChip) |

States, the same text everywhere:
- merging: the two bars;
- paused (recording, standby, media delete…): the bars hold, "Paused (recording)";
- merge off with split clips on the card: "3 split clips, merge off";
- **nothing waiting: no pill, "Nothing to merge"**. The missing pill is the "card can come out" signal.

Pulling the card mid-merge stays safe (clip-split verify step 7): the clip stays split and merges when the card is back.

## Core

1. **Progress from the disk, not a new state file** (User: use the mechanics that already survive a power-off). The merge
   keeps the prefix invariant: the main folder holds frames 0..k-1, and the rest are in the part folders. So:
   - clip done = frames in the main folder;
   - clip total = done + frames still in the parts.
   After a power-off the worker's next scan reads the same numbers, and a bar at 80 % comes back at 80 %.
2. **Cheap counts at scan time.** For each split clip, read the main folder (a few entries while it is still split) and count
   only the first remaining part (the only partial one, since parts merge in order) and the last part. The parts in
   between hold `frames_per_folder` each (from `.parts`). This is two listings of at most N files per clip, done while idle.
3. **Live counters.** The rename loop updates the done counter after every rename. That is one relaxed atomic store,
   against a rename of 0.1–0.7 ms.
4. **Time left.** Estimated from the measured model: about 0.1 ms per file plus 0.32 µs per file already in the main
   folder (`probe-exfat-dir.md`, `clip-split-verify.md`). The constant is corrected by the rate measured in the clip being
   merged. Shown rounded ("about 4 min").
5. **State fields.** Extend `clipMergeStateJson` (it is already in `/api/state`'s system block and the `set_clip_merge`
   reply) with:
   - `clip_merge_clip_done`, `clip_merge_clip_total`;
   - `clip_merge_all_done`, `clip_merge_all_total`, `clip_merge_all_clips`;
   - `clip_merge_eta_s`, `clip_merge_paused` (the reason, or "").
   Add it to the socket `get_state` too.
6. **A `clip_merge` event for the touch UI.** The touch UI polls `get_state` only every 30 s, so it needs a push. The event
   is sent from the buffer-event thread, which already loops every 250 ms to 1 s:
   - when a field changed, at most once a second;
   - once more when the queue empties;
   - nothing while nothing is pending.
   During a take the merge is paused, nothing changes, so no events are sent.
7. **Playback across a merge: resolve a frame's path from `.parts`, not from a stale listing.** Frame names don't change
   across parts, and `.parts` gives the pattern and N. So frame i is either at `part_<i/N>/<name>` or at `<name>`.
   - Try the part first, then the main folder. Frames only move part → main folder (one atomic rename each), so a miss
     in the part means it is already in the main folder. There is no race and no re-listing.
   - The route keeps its cached facts for a clip with `.parts` (the frame count doesn't change during a merge), instead
     of re-listing the whole clip on every frame because the main folder's mtime moved.
   - Without `.parts` (flat, or a merge that has finished) nothing changes.

## UI

8. **WebUI:**
   - the two bars in the Media card, with the existing `progress-track` / `progress-fill`;
   - the thin blue bar and sublabel in the Storage tile.
   Both read the new fields through the system-block filter (which already copies `clip_merge_*`).
9. **Touch UI bridge:**
   - properties for the fields, set from `get_state` and the `clip_merge` event (the `buffer` event pattern);
   - the two bars in the Media card;
   - the blue pill behind the MEDIA minutes and in ExternalMonitorWindow, shown only while the merge is on and the
     all-clips total is above 0.
10. **Touch UI player** (`ClipFrameFiles.hpp`): the same part-first, then main-folder lookup as item 7, for a clip with
    `.parts`.

## Shooting

Nothing here runs during a take:
- The merge already pauses within about 30 ms of `record_start`, and the bars and the pill hold still.
- The counters are atomics.
- The scan-time counts happen while idle.
- The event is silent while nothing changes.
- Redraws are about once a second, only while merging.

The campaign rule stands: WebUI closed for measured takes.

## Verify (on the Pi, after Patrik's restart)

1. Merge a 4,503-frame split clip with the WebUI open: both bars move, and the time left is within about 30 % of the actual time.
2. Power off mid-merge (`power_off_system`) and power on: the bars come back at the same %, and the merge finishes.
3. A take mid-merge: the bars and the pill hold and say "Paused (recording)"; 0 dropped frames; the merge resumes after the take.
4. Play a clip in the WebUI player while it merges: every frame plays, there are no 404s, and the frame time is close to a flat clip's.
   The same in the touch UI player.
5. Eject mid-merge: "3 split clips" after mounting again, and the merge starts.
6. Nothing waiting: no pill, "Nothing to merge".

## Commits (one per feature)

- `media: merge progress from the disk, in the state and a clip_merge event` (Core 1–6)
- `playback: read a clip being merged through its .parts layout` (Core 7)
- `web: merge progress bars in the Media card and the Storage tile` (8)
- `qml: merge progress bars, the blue pill behind the minutes, and the player across .parts` (9–10)
