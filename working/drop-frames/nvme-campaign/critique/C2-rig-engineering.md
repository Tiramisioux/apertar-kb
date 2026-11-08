# C2: rig, Core and runner engineering critique of plan v2 (NVMe 4K campaign on the Corsair cards, 2026-11-08)

Critic: rig / Core / runner engineering. Object: `scratchpad/draft/plan-v2.md` (the 13:00 Corsair-only revision, re-read after
its afternoon edits; cited as v2 §n) and `scratchpad/draft/build-list.md` (sections A-F, incl. A15 and A3'), against
`constraints-and-arithmetic.md` §11-15, `v2-rules-from-C1.md`, the KB (local HEAD `e2d2499` = origin/main `6e0df02` merged; the
brief's `2ba5b1b` is three commits behind: `4548e71` probe step 4 measured, `30eb37b` clip-split verified with two merge fixes,
`6e0df02`), the unmerged branch `origin/claude/practical-johnson-he481b` (now at `49c6f46`, four commits past the `676a089` R10 read:
`b7e602c` "longtakes.py runs the storage ladder unattended", `67514ac` merge of main), the tools named in the brief and the research
reports R1, R2, R3, R8, R10 and the critique C1. Labels are the KB's own (measured / derived / probable / unconfirmed / confirmed = read
in code or on the Pi; web). Line numbers for `working/tools/longtakes.py` are main's (`429019f`) unless marked "branch". Nothing ran on a
camera or the network; the only file written is this one.

Ranking: by consequence for the campaign's outcome (an unsafe delete, a wrong classification, a night that stops at the first gate, a
tier recorded under the wrong fixed state) first; build-list bookkeeping last. Stage letters: S0 preflight, S2 screening, S4 the 15-min
tier (first long unattended tier), S7 = v2's S6 soak + Part B (the brief's S7).

## 0. Facts the plan must start from that moved today

1. **origin/main moved past the plan's base.** `clip-split-verify.md` (steps 2-9 pass on the NVMe test card, Core `ba0658d` + fixes
   `68516f1`, `01f170c`; measured) and probe step 4 (cold unlink 263.8 ns x files-deleted-so-far, 13.6 s for 10,000 files; measured)
   are on main. v2 §2 and §6 S0 already say both; v2 §5a still says "reads ... at `ba0658d`" and §6 S0 says "binary `01f170c` or
   later": the running binary after the fixes is unconfirmed in the KB (fork-log `6e0df02` puts the fixes on GitHub `cinemate-port`,
   not on the camera). S0's first read must be the binary (`get_state` discriminator + `~/ApertarCore-build` commit).
2. **The runner the plan describes lives on the unmerged branch, not on main.** `b7e602c` (branch) adds to `longtakes.py`: the gate
   (`quiet_reasons`: probes, builds, foreign locks, Core ready, `storage_preroll_active`, `media_alive`, `ladder_enabled`,
   `media_trim_running`, `get_throttled & 0xF`, free space), the watchdog (`hardware_ok`: `journalctl -k` since the last check with
   `KERNEL_BAD` incl. `under-?voltage`, `media_alive`), `--budget-gb` with `projected_gb`, the `/run/apertar-media/longtakes.lock`,
   stages m/s/L/M/k/S (`long_runs`, `knob_stage` with `set_frames_per_folder value=` / `set_clip_merge enabled=`), `--fix-budget`
   (writes `buffer_ram_fraction 0.9`, `buffer_ram_floor_mb 256` into `/home/pi/apertar-hardware.conf`), plus the sampler columns v2 §9
   relies on (`buffer_used`, `dev_w_*`, `dirty_kb`, `trim_*`, `core_cpu_slope`, `queue_budget_mib`). Main's `429019f` has none of it.
   R10 read `676a089` (136 changed lines); the branch is now 595 changed lines and has merged main (`67514ac`). The build list cites
   R10's main anchors throughout.
3. **The branch corrects two of v2's storage facts** (`49c6f46`, derived/probable): the trim trigger after an outside delete "very
   probably fired after every delete" on the SSD (a warm unlink is 5 us/file), so v2 §2's "the trigger can miss slow small-file deletes
   (derived)" is now the branch's own low-priority note; and the 99 ns slope is read as the all-in per-entry cost of a take against the
   probe's 63.3 ns walk alone (1.6x; the remainder unconfirmed). v2 §3 uses 63.3 ns for the create-cost table and §7 "Core CPU slope at
   the probe's c" as the directory signature: the signature should expect ~99 ns all-in, not 63.3 (a 1.6x miss would read "none ->
   capture side").

## 1. Findings, ranked

### F1. v2 §9 + build list header: the build base is wrong; merging or choosing the branch is the unlisted first item (blocks S0)

- What is wrong: v2 §9 says the database carries "1 Hz samples incl. the buffer level, device counters, dirty pages, trim state" and S0's
  smoke test must prove `buffer_used` at 1 Hz. Those columns exist only on the branch (fact 0.2). The build list is "from the R10 map of
  longtakes.py @ 203204a" and every anchor (`Sampler` 309-399, `run_take` 847-1026, `main` 1029-1452) is main's. Built on main, A5, A10,
  A12 re-implement what `b7e602c` has (gate + watchdog, knob calls, budget); built on the branch, A5/A12 shrink to deltas and `--fix-budget`
  must be left unused because its 0.9 / 256 contradicts v2 §5 (0.6 / 512, C1 F5) and build-list E2 still says 0.9 / 256.
- Evidence: `git diff --stat origin/main origin/claude/practical-johnson-he481b -- working/tools/` = 595 lines in `longtakes.py`,
  `exfat_write_probe.py` (340), `storage_facts.sh` (36), `longtakes_fill.py` (236), all branch-only (confirmed); S1 names
  `storage_facts.sh` and `exfat_write_probe.py` (v2 §6 S1), i.e. S1 also needs the branch.
- Fix: **A0** = take `b7e602c`'s `longtakes.py` as the base (it already contains main's recursive count), re-anchor the build list to it,
  strike `--fix-budget` from every command line and E2 from the list; merge the branch into main first (KB hygiene) or build in the branch
  and merge at the end. Size 0 code, one merge; risk: the branch's `--stages 1d2rc` default and `clear_media` call sites are unchanged
  (F4, F2).

### F2. v2 §6 fill gate + build list A3: deletion by database name is unsafe on a rig with several Corsair cards, and the delete path should be Core's (blocks S2; safety)

- What is wrong: v2 deletes "the OLDEST campaign clips (from the database, never the owner's folders)" and Part B swaps cards. Clip names
  repeat across cards and after every format (`cDNG_..._C0001` reused: `lessons/hardware-log.md:879-888`, measured; `README.md` clip-name
  template `{format}_{date}_{clip}`, the counter restarts when the card is cleared). A database row "clip X" from the campaign card names
  a folder that may exist with the owner's footage on the next card. `PRESERVE` is filled once from `session.json` at the first start
  (`longtakes.py:1115`; R10 risk 4) and `run_take` attributes "the newest new `cDNG*` folder" to the take (943-944): a clip the owner
  starts in the post-take window is "the newest". A3 keeps names as the key.
- Also: the runner deletes with `shutil.rmtree` (1017; branch unchanged), outside Core. Core has **no socket delete command** (confirmed,
  `working/dng-chain/V/H6.md:16`: deletes exist only as `POST /api/media/delete` and `/api/media/delete-selected`, `APP:8645, 8727`). The
  HTTP delete trims deterministically (`trimMediaAfterDelete` when >= 1 GiB freed, `V/H6.md:25-26`, confirmed; verified live: "delete ok
  in 0.1 s, trim 479 ms", `clip-split-verify.md` step 8, measured), pauses the merge worker (`paused (media delete)`, same step) and is
  refused while recording (`working/playback/measurements.md:140`: delete 400 "Stop ..." during a take). The outside-delete trigger (>= 1
  GiB between two 1-s polls, `ApertarCoreApp.cpp:10863-10869@f4a1393` via the re-analysis §7) "very probably fires" for a fast unlink
  (branch `49c6f46`, probable), so A3's 60-s wait is a fallback, not the path.
- Fix (A3 rewritten): the deletable set is keyed by (card serial, clip folder name, folder mtime or inode, take_id) and is taken from the
  take's own `recording clip:` journal line (`parse_journal` sees it: `media_class=` is already read at 980-983), never from "newest new
  folder"; `PRESERVE` = every `cDNG*` present at EACH (re)start of the runner (not once per out dir), refreshed after every card change;
  delete through `POST /api/media/delete` on 127.0.0.1:8000 (the runner already uses `urllib` for `/api/state`, 511-518; `/api/buffer`
  on the branch), read `media_trim_last_unix` move as the trim confirmation, `rmtree` only as the fallback when the HTTP route is absent
  (then the 60-s wait + helper `fstrim` as A3 says); remove every `clear_media` call site (branch: walk 1701, A/B, bracket, `long_runs`
  1603, `log_probe` 537-538); the end-of-part delete runs in the boot that wrote the clips (cold unlink 263.8 ns x files-so-far, measured;
  a flat 45,000-frame clip ~4.5 min, derived: v2 §6 already budgets it). Size ~110 lines; risk medium (exact route payload is in
  `WebControlPage.cpp`, not in the KB: read it on the Mac first); blocks S2.

### F3. v2 §7 "a take ends at its first dropped frame (any Core counter)" + §6 S2 "limiter per failure": on this binary the runner's classification rests on journal lines that may not exist, and an audio fault steps the arm down (blocks S2)

- What is wrong: `first_drop_s`, `drop_kinds` and the capture/storage limiter all come from `drop[<kind>]: +N` journal lines
  (`parse_journal` 552-567; `limiter_of` 176-194) and the stats line keys (548-549). The clip-split verification found "this base
  (`f4a1393`) logs no `dropped_gap_estimate`" (`clip-split-verify.md`, measured); whether `drop[capture-gap]` lines print is
  unconfirmed; the SSD run had 0 `drop_events` rows, so the path never ran (R10 §6b q). The in-take stop reads `recording_dropped_frames`
  from `get_state` at 2 Hz (`Sampler` 367-387, loop 896-922): that counter is "0 at each take start, kept after the take" (`README.md:66`,
  measured), so the stop itself works; the time and the kind do not.
- The audio stop is logged as `recording failure: fault=write_error ... ALSA capture: Broken pipe` (`clip-split-verify.md`, measured). The
  runner maps `recording_error`/`recording_fault` to outcome `fault` (921-922) and the walk treats `fault` as a failure: `fps -= 1`
  (1226; branch 1707-1720 unchanged). v2 §5a / A13 / A15 say `audio_fault` "never prunes an arm", but the interception point (before the
  walk's decision, i.e. inside `run_take`'s outcome assignment, not in a post-hoc column) is not stated; A15 names the forced-drop check,
  not the parser's fallbacks.
- Fix: `first_drop_s` primary = the first 1 Hz sample whose `dropped` > 0 (samples exist; journal line secondary); limiter on this binary
  = storage when `buffer_safety_stop` was true or `queue_bytes_peak/queue_budget` >= 0.88 or `dropped_queue_full` > 0 (stats line), capture
  when `recording_dropped_frames` rose with `peak_queue` <= 3 and `buffer_used` flat, audio when the `recording failure` line carries
  `ALSA capture` (checked FIRST), drive event when the watchdog fired; the forced-drop check in S0 (v2 §6) records the exact lines and the
  parser is pinned to them (A15). The outcome `audio_fault` is assigned in `run_take` before `estimate_cause`, and the walk's `fps -= 1`
  branch excludes it (repeat once, as v2 says). Size 40 lines; blocks S2.

### F4. v2 §6-7 vs build list B: v2's stage machinery is not in the list, two B items contradict v2, and the branch's new stages implement the storage plan's ladder, not v2's (blocks S2, S4)

- What is missing or wrong: v2 needs, per mode block: a 60-s unscored warm-up after every Core restart / reboot / mode switch; a control
  at the block's start and end at the edge fps; the fps walk from a per-mode start (HDR16 28, HDR12 30, SDR12 from a meter take at 50 then
  capacity -1/-2) with two concordant takes per decision; ABBA lever pairs against pooled controls with the direction rule and the drift
  flag; one TDN-on take; manual `storage_preroll` capacity readings; S3 one take; S4 one unsplit take reading the CPU slope; S5 unsplit
  first with the signature-triggered split; S6 soak as the split variant; Part B per card. None of these is an item. B2 (log(T) fit) is
  forbidden by v2 §7 ("No fitted log(T) prognosis", C1 F6): drop. B4 (split pairs at 900 and 1800, back to back) is v2 v1's design, replaced
  by F4 of C1 (no 15-min pair; unsplit first at 30): change. The branch's `knob_stage` runs the back-to-back pair at 0.95 x capacity and
  `long_runs` uses `stop_on_drop=False` ("Core's safety stop ends a failing take", branch 1590-1592), the opposite of v2 §7's stop-on-drop
  at every tier; `split_stage` is 3 x 10 vs 1 x 30 (not in v2); `--fps-start` is one global value (1169) and the walk's start is
  `min(fmax, mode_cap_fps)` from `DISK_MBPS` (1167): the record's per-mode bracket is not expressible.
- Fix: one new stage driver ("stage `N`": the v2 night) that owns the mode blocks, the warm-ups, the controls, the two-concordant walk from
  a `--start-fps 4kHDR16=28,4kHDR12=30,4kSDR12=meter` map, the ABBA pairs, the tier loop with `stop_on_drop=True` and v2's S5/S6 rules,
  and emits `decisions.log` reasons; `bracket_search`, `smart_next_fps`, `prune_reason` and `storage_frontier` are not called by it (they
  remain for `--stages 1d2rc`). Size 300-400 lines + tests (B7); risk high (it is the campaign); blocks S2.

### F5. v2 §5 fixed state "WebUI stand-in CONNECTED": the runner's baseline is web OFF and a client dropout is a soft note, not a void (blocks S2)

- What is wrong: `Cfg`'s baseline is `web0` (`all_configs` 132-144, `distance()` 124-125, `RELEVANT['capture']` 173), the A/B and tier
  stages run the baseline config; v2 inverts it (client on fixed, "WebUI off" the lever). With `--web-remote` a take wants a client only
  when `c.web` is true (867-874); without it a Pi-local `webui_client.py` starts (875-879), which is Pi load, not the Mac's. `wait_peers`
  gives up after 30 s and the take runs with `mismatch = web_client_not_connected` (871-874): in v2 §7 "wrong client count" is a void.
  `webui_remote.py` reconnects its ssh after 5 s and starts a fresh `webui_client.py` per take (so Core restarts are survived by
  construction; the client itself reconnects after EOF and 5 s of silence, `webui_client.py` docstring, probable), but a Mac that sleeps,
  loses Wi-Fi or `apertar.local` mid-night leaves every later take without a client; nothing samples the client count during a take.
- Fix (A16): flip the campaign baseline to `web=True` (`distance()` counts `not web`), make `--web-remote` mandatory for stage N (refuse a
  local stand-in, as A7 says), sample `web_peers()` once a second into the samples (`clients` column; `ss` is cheap), void a take whose
  client count changed, and make a missing client at take start a GATE wait (up to e.g. 30 min, status "waiting for the Mac client") rather
  than a void or a stop; `webui_remote.py`'s hard-coded Mac log path (line 18) becomes an argument. Size 40 lines; blocks S2.

### F6. v2 §5-6 the campaign drop-in, pre-roll and merge: the e4 `arm` pattern switches the debug log on, the arm needs a restart and a per-boot YAML copy, and two mechanisms are named for each of pre-roll and merge (blocks S0)

- What is wrong: build list D says "pattern: e4-helper.sh". `e4-helper.sh arm` writes `LIBCAMERA_LOG_LEVELS=IPARPI:ERROR,RPI:0,RPiStream:0`,
  `LIBCAMERA_LOG_FILE`, `LIBCAMERA_RPI_PISP_CONFIG_DUMP` and `LIBCAMERA_RPI_CONFIG_FILE` (header lines 14-19, confirmed): the RPi debug log
  v2 §5 forbids ("no libcamera debug log and no tracefs"), and the instrumentation-cost hypothesis (R1 §4.2, unconfirmed) is exactly what
  the TDN-on take tests. `arm` requires `/run/apertar-media/pisp-pipeline.yaml` (regular file, uid 1000, contains `"target": "pisp"`) and
  does NOT restart Core ("the next apertar-b1-arm sync does", header line 22); `/run` is tmpfs, so after every reboot pi must copy the
  depth-4 YAML (`/home/pi/Tuning-Files/pipeline/pisp-depth4.yaml`, `findings-evening4-supervised-2026-11-04.md:51-55`) into `/run`
  before `arm`, then a restart, then the warm-up. v2 says "armed once per evening"; the unit of validity is the boot.
- Pre-roll: `[media] preroll` is "read at each request" and `set_storage_preroll` edits the key (`architecture/config.md` §2.4 `[media]`,
  confirmed): a socket command as pi, no sudo, no restart, restorable; `APERTAR_STORAGE_PREROLL=0` needs the drop-in and a restart and sets
  `storage_preroll_auto_env`. E3 names both. The branch gate already waits on `storage_preroll_active` (branch `quiet_reasons`), so the
  runner no longer needs the pre-roll off at all; R2 §5.16's "the loop waits for the pre-roll line" was `e3-unit.sh`, which v2 does not use.
- Merge: A10 says `set_clip_merge enabled=false` at start AND `APERTAR_CLIP_MERGE=0` in the drop-in. With the env set, whether the command
  still applies is unconfirmed (the trim switch has `media_trim_env_off` for this case, fork-log `ce0bd90`); `01f170c` makes the conf key
  hold at Core's start (fork-log, measured in verify step 7). One mechanism suffices.
- Fix: the campaign helper's `arm` writes only `Environment=LIBCAMERA_RPI_CONFIG_FILE=/run/apertar-media/pisp-pipeline.yaml` (plus
  `APERTAR_AUDIO_BUFFER_MS` only when the lever is on), daemon-reloads AND restarts Core in the same word (b1-arm's `restart_and_wait` +
  environ read-back pattern, `b1-arm.sh:173-186, 271-284`); the runner (as pi) copies the YAML into `/run/apertar-media` at start and
  before asking for `arm`; pre-roll and merge are set over the socket (`set_storage_preroll`, `set_clip_merge`; argument names
  unconfirmed in the KB: read back `storage_preroll_auto`, `clip_merge_enabled`) and restored at the end; the runner verifies
  `LIBCAMERA_RPI_CONFIG_FILE` in `/proc/<MainPID>/environ` (readable as pi: `take3v3.sh:50` does it) before every take and voids
  otherwise (see F7). Size: helper 150 lines (sh), runner 30; blocks S0.

### F7. v2 §7 "after a Pi reset the runner resumes once ... only if its last status was clean": no mechanism, and a resumed runner would record under the wrong fixed state (blocks S4)

- What is wrong: no build-list item implements the resume rule (the storage plan §7.1 describes a crontab `@reboot ... [ -f AUTORESUME ]`
  line; the branch code has no sentinel: `grep AUTORESUME` finds nothing). After a reboot the `/run` drop-in is gone (FE depth 2, merge
  on if the env was used), `compaction_proactiveness` back to 20, the override file gone (`/run/apertar-media/media-tune.override.conf`,
  tmpfs: `media-tune-file.md`), and Core starts the automatic pre-roll. A runner that resumes by `--out` would score takes under depth 2
  without knowing. The 2026-11-06 resets ("Voltage normalised", EXT5V 4.78 V) were on the Kingston rig (`longtakes-campaign-plan.md:5-6`,
  unconfirmed cause); on the Corsair rig EXT5V read 5.02 V (`hardware-log.md:308`, measured): the risk is lower but the rule stays.
- Fix (A22): a `RESUME` sentinel the runner writes only between takes with `last_status=clean`; the `@reboot` crontab line (pi, no sudo)
  starts the runner only if the sentinel says clean and at most once (it rewrites the sentinel `resumed=1`); at start the runner checks
  Core's environ for the drop-in and the `preview_tdn` / `frames_per_folder` / `clip_merge_enabled` / `buffer_setting` read-backs; a
  mismatch = status "WAITING: drop-in not armed (needs Patrik)" and no take. The gate's `get_throttled & 0xF` (now) must also read bits
  16-19 (since boot) as the "under-voltage event" of v2 §7, and the sampler's per-second `throttled` is the in-take record. Size 50 lines;
  blocks S4.

### F8. v2 §4 crops: a refused `set_resolution` stops the whole night, the 16-bit crop heights crash `mode_size_mb`, and the mode table is the installed driver's (blocks S2's crop block)

- What is wrong: `verify()` reports a resolution mismatch as `setup_mismatch`, which stops the campaign ("needs a human", 1138-1140; R10
  risk 10). `mode_size_mb` raises `KeyError` for any 16-bit height other than 2160/1080 (92; R10 risk 9; B5 addresses the size, not the
  refusal). The installed driver is `cd548ef` (187 probed modes, 3840x2072 and 1920x1036 at 10/12 bit, a duplicate-size audit warning:
  `hardware-log.md:899-903`, measured); the apertar driver `e5b74d3` has 3840x2076 and NO Clear HDR crops at all (`get_mode_table`
  partitions: Clear HDR 12-bit -> `[10]` 3840x2160 only, 16-bit -> `[20]` 3840x2200 only; `working/compare-raw/c1-probe-compare.md:219`,
  confirmed in source). Whether a crop must be in the "Activated sensor modes" list for `set_resolution` to accept it is unconfirmed
  (`longtakes-test-structure.md:26`: all eight modes were activated for the SSD run).
- Fix: S0 (with Patrik) runs `list_sensor_modes` and one `set_resolution` + read-back per planned crop and bit depth (no take), records
  the raw and active heights for B5; a crop refusal at night becomes `skipped_unavailable` for that mode, not a campaign stop; crops stay
  last in S2. Size 20 lines; blocks S2's last block only.

### F9. Runner safety gaps that survive on the branch: a dead sampler makes a dead drive look like a pass; `record_stop` is not in `finally`; SIGTERM waits for the tier (blocks S2)

- What is wrong: the sampler thread calls `os.statvfs(MEDIA)` unguarded (main 376, branch 646); if the medium dies mid-take the thread
  raises and dies silently, `sam.last()` goes stale, the loop keeps reading the stale `dropped`/`state` and ends the take at the tier
  length with outcome `pass_<tier>` (906-909) on a drive that stopped answering (R10 risk 5 names the crash, not the false pass). The
  main loop's own `statvfs` (904) raises a traceback instead. `record_stop` is only at 925, not in the `finally` (1432; branch 1953);
  SIGTERM only sets `stop['now']` between takes (1125; branch 1517). A5/A6 keep these; the branch's watchdog runs between takes only
  (`hardware_ok`), which is right for the journal rule but leaves the in-take case to the sampler.
- Fix: the loop requires a fresh sample (age < 3 s) and treats a stale sampler or a `statvfs` error as outcome `fault` with
  `record_stop`; `record_stop` in `finally`; SIGTERM/SIGINT checked inside the loop (A6 as written). Size 25 lines; blocks S2.

### F10. v2 §5 storage knobs as one group / build list C2: `workers` and `queue` may not be re-read between takes, so the SSD's null result and the campaign's variant may test nothing (S7, conditional)

- What is wrong: `architecture/config.md` §7.1 says `workers` and `queue` are read at "media change (`deriveMediaProfile`)" and `dontneed` /
  `writeback` once per process; only `sync_ms` is read each take (confirmed, code refs). `longtakes-test-structure.md` §6 says "Core
  re-reads it when a take starts" and the SSD A/B found "no effect" for workers 2/6, queue 24/48 (measured). The two statements conflict;
  if §7.1 is right, the SSD's A/B never changed the writer count and v2's "no effect on the SSD (measured)" is not evidence. The runner
  logs `tune_override=yes|no` from the clip line (`48f8b8c`) but the clip line carries `dontneed= writeback= sync_ms=` only.
- Fix: before C2 runs, read Core's `ApertarCore media tune: ... <every key> source:` line (once per process) and the `media profile` line
  after a `set` to see whether `workers`/`queue` follow the override without a restart; if not, C2 is a restart-batch item (C1's protocol)
  and the SSD result is relabelled. `workers 1` is not in `AB_VARIANTS` (806-808: 2 and 6): add it. Size 15 lines + one read; S7.

### F11. v2 §2 and §6 S1: the thermal curve "inside the CFe-B shell" is probably already the record's, and S1's "Core stopped" needs a sudo word the helper does not have (S0/S1, low)

- What is wrong: v2 §2 calls the shell's thermal effect "probable" and plans to measure the curve in S1 "not assume" it. The record's drive
  numbers (34 -> 54 C, 72 C after 10 min at 410 MB/s; the 0.9 TB stall; 733 MB/s) were measured on the same card, serial `A936B442006AC2`,
  in the camera's CFexpress hat ("CFE HAT NVMe `/dev/nvme0n1p2`", `hardware-log.md:296-300`; the CFE pull tests of 2026-10-26 pulled that
  card). If the card sat in its CFe-B adapter then (the KB names the hat, not the adapter: unconfirmed), S1's curve is a repeat, and the 72 C
  after 10 min is the shell figure. S1's 100 GB write "Core stopped" needs `systemctl stop/start apertar-core` (sudo; D has `restart-core`
  only). The probe of 2026-11-08 ran with Core idle (`probe-exfat-dir.md` step 0) and that is enough: Core's media watcher is a 1 Hz
  `statvfs`.
- Fix: ask Patrik whether the record's card was in the adapter (one line in §2); run S1 with Core idle, not stopped; `hwmon('nvme')` is
  resolved once at import (24-35): re-resolve per take so a card swap or controller reset does not blank `nvme_c`; the part number is not in
  sysfs (A4' typed in: fine) and `nvme id-ctrl` needs a helper word if the firmware family is wanted (`ERFM` = E27T, `ELFMB` = E21T,
  `working/dng-chain/R6.md:130`, unconfirmed as a rule).

### F12. v2 §5 "the ladder off for the take and restored after" and "TDN off (fixed)": the branch gate stops on a ladder that is on, and two TDN-off mechanisms exist (S0, low)

- Ladder: the branch's gate treats `ladder_enabled` as "NEEDS A HUMAN" and returns (branch `quiet_reasons`); `set_mode_ladder enabled=false`
  exists and `take3v3.sh:60,109` switches it off and restores it. Patrik's real use has the ladder ON (take3v3 restores it on). Fix: the
  runner switches the ladder off at session start and restores it in `finally` (10 lines), else the first night stops at the gate.
- TDN: the runner uses `set_preview_tdn enabled=false` (433; Core strips `tdn` into `~/.cache/apertar-core/tuning`, `fork-log.md:158`, the
  strip "byte-identical to the evening-3 copy", measured); the recipe's row 7 is the tuning copy `imx585_clearHDR_notdn.json` via
  `set_tuning_file`. If the camera still has the copy selected, both apply. Fix: `verify()` also reads `tuning_file` (expect automatic) and
  `tuning_file_active`, recorded per take; S0 sets the tuning back to automatic with Patrik.

### F13. v2 §9 status and decisions: what the runner can know is fine; what it cannot is the smart-log and the prognosis unless A11 gets them (S2)

- The status file can carry everything v2 §9 lists except: smart-log readings (needs the helper word `smartlog`, sudoers; A12 says so),
  the prognosis table (needs the survival computation per cell: exposure pooled across tiers, 3/n, the 30-min expectation; not an item) and
  the claims table (v2 §7; not an item). The samples CSV is flushed every second during a take (395) and is the one file ssh must not
  `tail` during a take by v2's own rule; status.md written atomically between takes is right (SD card, `~/longtakes/<run>`).
- Fix (A21): the survival and claims tables as a 60-line module fed from `results.csv`, written into `status.md` / `status.json` after
  every take; `decisions.log` lines come from stage N (F4).

## 2. Answers to the brief's rig questions, in one place

| Question | Answer (label) | Consequence |
| --- | --- | --- |
| Commands / knobs / files assumed that do not exist | `set_clip_merge`, `set_frames_per_folder`, `set_storage_preroll`, `set_mode_ladder`, `set_media_trim`, `set_preview_tdn`, `storage_preroll`, `list_sensor_modes`, `set_resolution` exist (fork-log, config.md, longtakes.py; confirmed); argument names of `set_clip_merge`/`set_frames_per_folder`/`set_storage_preroll` are unconfirmed in the KB (the branch uses `enabled=` / `value=`); **no socket delete command** (confirmed); `apertar-campaign-helper` and its sudoers do not exist (D); `exfat_write_probe.py`, `storage_facts.sh`, `longtakes_fill.py` exist on the branch only; `tools/longtakes_test.py` does not exist (B7); `--tiers`, `--plan-only`, `--write-cap-gb`, `status.md` do not exist (the branch has `--budget-gb`); `/run/apertar-media/pisp-pipeline.yaml` exists only after a copy in the current boot | F1, F2, F6 |
| The Core binary; what to set and verify | running: `ba0658d` + probably `68516f1`, `01f170c` (GitHub `cinemate-port`; on the camera unconfirmed); defaults `frames_per_folder 0`, `clip_merge on`, `preroll on`, `buffer=ram` 0.6/512, trim on, `preview_tdn` default off (fork-log `6bd002b`: "default off = TDN stripped by default", R2 §1); verify per take: `frames_per_folder`, `clip_merge_enabled`, `preview_tdn`, `tuning_file`, `buffer_setting`, `storage_preroll_auto`, `fps_speed_ramp` false, `ladder_enabled` false, `cdng_log_applied`, the drop-in in Core's environ | F6, F7, F12 |
| FE depth 4 drop-in | sudo (helper), one Core restart per BOOT, YAML re-copied to `/run` per boot by pi, then a 60-s warm-up; the e4 pattern's extra debug-log lines must not be copied | F6 |
| RAM budget keys | keep 0.6 / 512 (no edit); never `--fix-budget`; log `queue_budget_mib`/`budget_seconds` (branch) | F1 |
| Pre-roll off | `set_storage_preroll` over the socket (no sudo, no restart, "read at each request", confirmed) or leave it on: the branch gate waits on `storage_preroll_active`; a pre-roll writes 0.7-0.8 GB and deletes it (measured) | F6 |
| Fill gate / delete-when-needed | delete via `POST /api/media/delete` (trim `reason=delete`, merge paused, refused while recording; measured); keys per card; outside-delete trigger probably fires for a warm unlink (branch, probable); cold unlink 263.8 ns x files-so-far (measured), 4.5 min per flat 30-min clip (derived); 60-s trim wait only as the fallback | F2 |
| Stop-on-drop at every tier | `recording_dropped_frames` at 2 Hz (1 Hz after A7), 0 at take start (measured); the safety stop is read from `buffer_safety_stop` in the last 12 samples or `queue_bytes_peak/queue_budget` >= 0.88 (measured on the SSD); `first_drop_s` from the samples; `fault` with `ALSA capture` = `audio_fault` before anything else | F3 |
| WebUI stand-in after Core restarts | a fresh `webui_client.py` per take; the client reconnects after EOF / 5 s silence (docstring, probable); the Mac side is the single point of failure for the night | F5 |
| Status file / decision log | between takes, SD card, atomic; needs the survival + claims module and stage-N reasons | F13 |
| Per-take settings that need a Core restart | FE depth (YAML), `dontneed`, `writeback`, `APERTAR_AUDIO_BUFFER_MS`, any `Environment=`; `workers`/`queue` probably a media change (F10); `sync_ms`, trim, TDN, Log, compression, fps, resolution, bit depth, Clear HDR, `frames_per_folder`, `clip_merge`, pre-roll, buffer mode: no restart (config.md §2.4, §7.1) | F6, F10 |
| 4K crops | `set_resolution width= height=`; the table is the installed driver's (`cd548ef`: 3840x2072 at 10/12-bit; 16-bit crop heights unknown); refusal must not stop the night | F8 |
| Temperature without sudo | `/sys/class/nvme/nvme0/hwmon*/temp1_input` (an admin command per read, R1 §4.2); re-resolve the path per take | F11 |
| NVMe watchdog | branch `hardware_ok` + `KERNEL_BAD` between takes (pi is in `systemd-journal`: `working/diagnose.md:17`, confirmed); in-take: the sampler's `media_alive`/`statvfs` with the stale-sample guard | F9 |
| Pi reset / power loss | sentinel + `@reboot` line; refuse to resume without the drop-in; bits 16-19 of `get_throttled`; the Kingston under-voltage history does not transfer, the rule does | F7 |
| Kingston items | out of scope (Corsair-only rig); the KC3000 pSLC/post-cache probe is replaced by S1's 100 GB write on the Corsair (pSLC ~50 GB, post-cache ~800 MB/s, web) | - |
| Transfer to the other Corsair cards | labels `CFE-RAW`/`NVME-RAW`/`RAW`/`USB-RAW` are the only ones the automounter mounts (measured, `longtakes-test-structure.md:134`); `media_class=pi-nvme` for any card in the hat (measured, `clip-split-verify.md`); a serial that differs from the session's must be an explicit new card session (`--card`), not a void; the thermal path is the same slot (F11) | F2, F11 |

## 3. Build-list review (keep / change / drop; size in lines; risk; what it blocks)

Base for every size: the branch `b7e602c` (F1). "Blocks" names the first stage that cannot run without the item.

| Item | Verdict | Reason and change | Size | Risk | Blocks |
| --- | --- | --- | --- | --- | --- |
| A1 `--disk-mbps` / refuse the default | **change** | v2's walk starts from the record's bracket per mode, not from `mode_cap_fps`; add `--start-fps <mode>=<fps|meter>`; keep `DISK_MBPS` from S1's 60-s direct write only to keep `storage_frontier` and the A/B gate (>= 70 %) sane; keep the refusal | 25 | low | S2 |
| A2 `--modes` mandatory, order from the argument | **keep** (+ crops in the list) | as written | 10 | low | S2 |
| A3 deletion policy | **change** (F2) | keys per card from the clip line, `PRESERVE` per (re)start and card, `POST /api/media/delete` primary, `rmtree` fallback, remove all `clear_media` call sites incl. `long_runs`, end-of-part delete in the same boot; absorb A3' (cold-delete budget) | 110 | medium | S2 |
| A4 card detection + fit table | **keep**, absorb A4' | add the expected-serial rule and `--card` sessions for Part B; `firmware_rev` from sysfs | 70 | low | S0 |
| A5 watchdog | **change** (F9) | the branch has `hardware_ok` + `KERNEL_BAD` + `media_alive`; remaining: guarded `statvfs` in the sampler, the stale-sample rule in the loop, `fault`/`stopped_externally` never retried, `CSTS=0xffffffff` in the regex | 30 | low | S2 |
| A6 signals, `record_stop` in `finally` | **keep** | still absent on the branch (finally at 1953 restores settings only) | 25 | low | S0 |
| A7 sampler 1 Hz, no `vcgencmd` per sample, refuse the local stand-in | **keep** | branch interval still 0.5 s (670) | 30 | low | S2 |
| A8 kernel_tune disk name / class | **keep, conditional** | only with C2; the bug stands (`rstrip` gives `nvme0n1p`) | 15 | low | S7 |
| A9 take id with a date, CSV header migration | **keep** | branch unchanged | 15 | low | S0 |
| A10 `split` in `Cfg`, knob calls, merge off | **change** | the branch's `knob_stage` already sends `set_frames_per_folder value=` / `set_clip_merge enabled=` (names unconfirmed); add `verify()` read-back of `frames_per_folder`, `.parts` per take; drop the env duplication (one mechanism, F6) | 25 | low | S4 |
| A11 status + decision log | **keep** | add the survival and claims tables (A21) as its data source | 120 | medium | S2 |
| A12 wear ledger, cap, smart-log | **change** | the branch has `--budget-gb` + `projected_gb` + `budget_exceeded`; add per-card totals, `dev_w_sectors` delta, the helper `smartlog` read at start/end | 25 | low | S2 |
| A13 audio columns, `audio_fault` | **keep** | assign the outcome inside `run_take` before the walk's decision (F3) | 60 | low | S2 |
| A14 `APERTAR_AUDIO_BUFFER_MS` in the drop-in | **keep** | only when the lever is used; needs a restart | 10 | low | - |
| A15 loss classification on this binary | **keep**, merge with A5/A13 | pin the parser to the forced-drop check's lines; `first_drop_s` from the samples | 30 | low | S2 |
| A3' cold-delete budget | **merge into A3** | - | - | - | - |
| A4' part number, firmware | **merge into A4** | - | - | - | - |
| S1' 100 GB probe + hwmon log | **keep**; run with Core idle, not stopped (F11) | not a runner item | - | - | S1 |
| B1 3-min tier, `--tiers`, labels | **keep** | - | 20 | low | S2 |
| B2 log(T)-vs-fps fit | **drop** | v2 §7 forbids it (C1 F6) | - | - | - |
| B3 paired lever tests | **change** | pooled controls (every edge-fps baseline take), start/end controls per block, ABBA, direction rule, "not shown" non-terminal, drift flag | 80 | medium | S2 |
| B4 split pairs at 900/1800 | **change** | v2: S4 unsplit only; S5 unsplit first, split on the directory signature; S6 soak as the split variant; the signature computed from the samples (CPU slope vs ~99 ns all-in, buffer slope in the last minutes, `dev_w_ticks`/write vs fill, `nvme_c` vs latency, `dirty_kb`) | 70 | medium | S4 |
| B5 crop modes | **keep** + F8 | raw/active heights from `list_sensor_modes`; a refusal = `skipped_unavailable` | 40 | low | S2 |
| B6 `--plan-only` | **keep** | - | 20 | low | S0 |
| B7 offline tests | **change** | tests for the two-concordant walk, the per-card deletion policy on a fake tree, the classifier on recorded journal windows (the verify page's `ALSA capture` line as a fixture), the status writer; drop the fit tests | 120 | low | S0 |
| C1 restart-batch protocol | **keep, conditional** | the environ check becomes a per-take rule anyway (F7) | - | - | S7 |
| C2 storage group variant | **change** | add `workers 1`; confirm `workers`/`queue` re-read without a restart first (F10) | 15 | low | S7 |
| C3 MLV control | **keep** | the branch's stage M exists (`set_record_format mlv`) | - | - | S5 |
| C4 `make_results_xlsx.py` | **keep** | desk | - | - | - |
| D root helper | **change** (F6) | `arm` = YAML checks + `LIBCAMERA_RPI_CONFIG_FILE` only + daemon-reload + restart + environ read-back; `disarm`; `smartlog`; `fstrim`; `status`; `compact0`/`compact-restore`; `reboot`/`poweroff`; `drop-caches` is no longer needed (step 4 done); `idctrl` optional | 150 (sh) + sudoers 12 | low | S0 |
| D' `compact0`, `audio-usb` | **keep** | - | 20 | low | - |
| E1 campaign binary + verification | **change** | verification is on record; replace with "confirm the running binary carries `68516f1` and `01f170c` (GitHub `cinemate-port` head) and the `get_state` fields" | - | - | S0 |
| E2 RAM budget keys 0.9 / 256 | **change** | 0.6 / 512 = the defaults: no edit; never `--fix-budget` | - | - | S0 |
| E3 pre-roll off | **change** | `set_storage_preroll` over the socket, or leave it on (the gate waits) | 5 | low | S0 |
| E4 storage patches | **keep, conditional** | - | - | - | S7 |

Additions the list misses:

| # | Item | Size | Risk | Blocks |
| --- | --- | --- | --- | --- |
| A0 | Build base = branch `b7e602c` (merge into main or build there); re-anchor the list; strike `--fix-budget`; S1 tools come with it (F1) | merge | medium (conflicts in `fork-log.md`, READMEs) | S0 |
| A16 | Baseline `web=True`, `--web-remote` mandatory for stage N, `clients` sampled per second, client dropout = void, missing client at start = gate wait (F5) | 40 | low | S2 |
| A17 | Per-take read-back of Core's environ (`LIBCAMERA_RPI_CONFIG_FILE`, `APERTAR_AUDIO_BUFFER_MS`) and of `tuning_file`, `storage_preroll_auto`, `fps_speed_ramp`, `ladder_enabled`; mismatch = void / WAITING (F6, F7, F12) | 30 | low | S2 |
| A18 | Stale-sample guard: a sample older than 3 s or a `statvfs` error = `fault` + `record_stop` (F9) | 10 | low | S2 |
| A19 | YAML copy to `/run/apertar-media/pisp-pipeline.yaml` at runner start (pi), before the helper's `arm`; status line when the drop-in is absent (F6) | 15 | low | S0 |
| A20 | Stage N: the v2 night (warm-ups, start/end controls, two-concordant walk from `--start-fps`, ABBA pairs, the TDN-on take, `storage_preroll` capacity readings, tiers with `stop_on_drop=True`, S5/S6 rules, Part B per card, `decisions.log` reasons) (F4) | 300-400 | high | S2 |
| A21 | Survival and claims tables per cell into `status.md` / `status.json` (F13) | 60 | low | S2 |
| A22 | Resume sentinel + `@reboot` crontab line (pi), resume at most once and only when clean; refuse without the drop-in; `get_throttled` bits 16-19 (F7) | 50 | low | S4 |
| A23 | `hwmon('nvme')` re-resolved per take; the > 75 C end-of-take flag from `nvme_c_max` (F11, v2 §7) | 10 | low | S2 |
| A24 | S0 crop probe: `list_sensor_modes` + `set_resolution` read-back per crop and bit depth, heights into B5's table (F8) | desk + 10 | low | S2 |
| A25 | Ladder off at session start, restored in `finally` (`set_mode_ladder`) (F12) | 10 | low | S0 |
| A26 | Meter-take helper for SDR12's start fps (budget-derived overshoot 5-10 %, 30-60 s, integral identity, device cross-check; v2 §7); the branch's `metered_capacity` is 90 s at the top fps and needs the overshoot rule | 40 | medium | S2 |

Sum of the runner work on the branch base: about 1,100-1,250 lines (A: ~530, B: ~350, additions: ~560 minus overlaps), against the
list's ~900; the helper 150 lines of sh plus a 12-line sudoers file. The critical path is A0 -> A6/A9/A19/A25 -> smoke test (S0) ->
A3/A5/A13/A15/A16/A17/A18/A20/A21 (S2).

## 4. What v2 gets right and must not be lost

- The fixed state is the owner's real use with the deviations named (WebUI client connected, audio on, peaking + zebra, no debug log, no
  tracefs), and the instrumentation-cost hypothesis gets its one unlogged TDN-on take (R1 §4.2).
- The record's RAM budget (0.6 / 512) is kept and logged per take; `buffer_full` is reported in seconds of input absorbed.
- Stop-on-drop at every tier, two concordant takes per screening decision, warm-ups after restarts and mode switches, controls at block
  start and end with the drift flag, ABBA pairs with the direction rule, the claims table, no fitted prognosis (all C1 rules carried).
- Unsplit first at 30 min, the split member only on the directory signature or as the soak, the attribution signatures pre-registered,
  and the probe's measured c (now also the cold-unlink slope) in the arithmetic.
- The fill gate is physical, fill is a covariate, temperature is logged and never gated, deletes happen in the boot that wrote the clips
  with the cold-delete budget stated.
- `audio_fault` as its own outcome that never eliminates an arm alone, with the journal window, compaction and usb lines kept, and the
  Core fix placed before the campaign if an xrun ends a take.
- The void and stop-the-night rules name the right signals (`critical_warning`, kernel nvme/pcie/exFAT lines, Core `error`, `media_alive`,
  a second void, an under-voltage event) and leave the Pi on for Patrik.
- Nothing runs during a take but the 1 Hz sampler; status and decisions are written between takes, on the SD card, atomically.
- The wear ledger, the 10 TB cap with the shrink order (S3 first), "a 30-min take is never repeated to make sure unless void".
- Part B as a per-card check labelled n = 1, with the card's part number and serial recorded, and the S0 insistence on reading the binary,
  the card and the helpers before any take.

## Verification (skeptic)

Read 2026-11-08 ~13:30 with cat/sed/grep only, against the branch file (`git show origin/claude/practical-johnson-he481b:working/tools/longtakes.py`, 1,993 lines), main's `429019f` (1,464 lines), the KB at local HEAD `e2d2499`, and the plan as it stood at 13:26 (`plan-v2.md`) / 13:25 (`build-list.md` section H). Nothing ran on a camera or the network; only this section was written. "Adopted" = the current plan already carries the fix.

### The six specific checks

- (a) `git log -S` attributes `quiet_reasons`, `hardware_ok`, `KERNEL_BAD` (with `under-?voltage`, branch 338-339), `--budget-gb` + `projected_gb` (1420, 476), `LOCK = /run/apertar-media/longtakes.lock` (336; falls back to `/tmp`), stages m/s/L/M/k/S (1941-1951) and `knob_stage`/`long_runs` to **`b7e602c`**: confirmed. The sampler columns (`buffer_used`, `dev_w_*`, `dirty_kb`, `trim_*`, 325-326) and `core_cpu_slope`/`queue_budget_mib` (887) came in **`676a089`** (the commit R10 did read) and were extended by `b7e602c`: a small misattribution in fact 0.2, no consequence (none of it is on main). `--stages` default is still `'1d2rc'` (1407).
- (b) `--fix-budget` writes `buffer_ram_fraction 0.9`, `buffer_ram_floor_mb 256` into `/home/pi/apertar-hardware.conf` (1423, 1502-1505; restored in `finally` 1955-1960): confirmed. Core's defaults are 0.6 / 512 (`architecture/config.md:116-117`): confirmed.
- (c) `lessons/hardware-log.md:883` (entry 879-888): "Clip NAMES repeat across cards: the counter restarts when the card is **cleared** ... Match by capture time, never by name": confirmed; the KB says "cleared", C2 and v2 say "format" (a delete-all may restart the counter as well, which argues for the per-card key even more). `clip-split-verify.md` step 8: C0008 `paused (media delete)` at 1852/4502, delete `ok` in 0.1 s, trim 479 ms, `stopped (deleted)`: confirmed.
- (d) `long_runs` (branch 1590-1605): docstring "no stop at the first drop (Core's safety stop ends a failing take)", `take(..., stop_on_drop=False, ...)` at 1605; also meter (1580), soak (1649) and A/B (1782): confirmed.
- (e) `set_storage_preroll`: `architecture/config.md:125, 128` ("Read at each request; `set_storage_preroll` edits this key"; commands `storage_preroll`, `set_storage_preroll`): confirmed. `set_clip_merge`: fork-log row `ba0658d` only (config.md does not mention `clip_merge` or `frames_per_folder` at all; argument names unconfirmed, as C2 says): confirmed. Rows `00f2327` (`set_media_trim`) and `d44b177` (`set_buffer_mode`, the pre-roll feature) do not name either command; the citation is loose, the commands exist. `set_mode_ladder`: fork-log `0041ba0`.
- (f) The verify page's note is "This base (`f4a1393`) logs no `dropped_gap_estimate`; the drop checks used `recording_dropped_frames` and enqueued = written." The KB's code reading says the `ApertarCore capture stats: dropped_gap_estimate=... requeue_failures=...` line prints **only if** the gap estimate or the requeue failures are > 0 (`working/port-raw/p2-phaselock-core.md:74, 159`; `s2-storage-core.md:405`: "capture-stats only if gap or requeue > 0"), `ApertarCore drop[capture-gap]: +N frame(s) estimate dt_us= nominal_us= total_estimate=` is rate-limited (first gap, every 30th, any multi-frame gap) and `recording stats: enqueued= written= dropped_queue_full= ...` prints only when a counter is non-zero. Other kinds on record: `drop[queue-full] queue=12/12` (hardware-log:351), `drop[copy-slot]` (:140), `drop[requeue-failed]`. The 2026-11-01 build printed `dropped_gap_estimate=18` for 18 lost frames (hardware-log:937). Every verify take dropped 0 frames, so the absent line is expected and says nothing about the binary: **the KB does not support "this binary prints no `dropped_gap_estimate`"**; it supports "no drop line prints in a clean take". The S0 forced-drop check is still the right test, and `first_drop_s` from the samples is still right.

### Verdicts

| F | Verdict | Why (evidence opened) |
| --- | --- | --- |
| F1 | **HOLDS** | (a), (b) above; the build list's header and A-G anchors are main's (`@ 203204a`), E2 said 0.9 / 256, v2 S1 names `storage_facts.sh` and `exfat_write_probe.py`, both branch-only (`git diff --stat`: 4 files, 1,174 insertions). Adopted: v2 §9, H0, H base note. Nit: sampler columns = `676a089`. |
| F2 | **HOLDS** | hardware-log:883; main 1083 (`session.json` written once) + 1115 (`PRESERVE` from it), 943-944 (newest new `cDNG*` folder = the take's clip), 1017 `rmtree` (branch 1378, now also `MLV*`); `V/H6.md:16` (no socket delete; HTTP routes 8645 / 8727), `:25` (trim when >= 1 GiB freed); verify step 8; `playback/measurements.md:140` (delete 400 while recording); branch `storage-slowdown-plan.md:39, 137` (outside-delete trigger `10863-10869`, "very probably fired after every delete"). Adopted: v2 §6 fill gate, H5. |
| F3 | **OVERSTATED** | What holds: `first_drop_s`/`drop_kinds` come only from `drop[...]` lines (main 552-567; R10 q: 0 `drop_events` in the SSD run), the stop reads `recording_dropped_frames` at 2 Hz (branch 1228), and a `fault` falls through the walk to `fps -= 1` (branch 1707-1735; `estimate_cause` at 1371 runs after the outcome is fixed), so an audio fault does step the arm down. What does not: "journal lines that may not exist" rests on the verify note, which (f) shows is an observation on drop-free takes; the KB's code reading says the lines print on a drop. Adopted: H11 (samples first, `ALSA capture` first, parser pinned by the forced-drop check). |
| F4 | **HOLDS** | B2 and B4 were in the list; v2 §7 forbids the fit; branch `split_stage` = 1 x 30 vs 3 x 10 (1609-1613), `knob_stage` at factor 0.95 (1615-1627), (d) above, `--fps-start` one value, `--stages` default `1d2rc`. Adopted: H12. |
| F5 | **HOLDS** | main 125 (`distance()` counts `self.web`), 132-144 (baseline = `cs[0]`, web False), 173 (`RELEVANT['capture']`), 867-879 (client only when `c.web`; else a Pi-local `webui_client.py`; 30 s then `web_client_not_connected`); `webui_remote.py:18` hard-coded log dir, `:41` reconnect after 5 s; `webui_client.py` docstring (reconnects after EOF / 5 s silence). Adopted: v2 §7 WAIT rule, H8, H9. |
| F6 | **HOLDS** (line slips) | `e4-helper.sh` header 12-19: writes `LIBCAMERA_LOG_LEVELS`, `LIBCAMERA_LOG_FILE`, `LIBCAMERA_RPI_PISP_CONFIG_DUMP`, `LIBCAMERA_RPI_CONFIG_FILE`, "does NOT restart apertar-core" (line 19, not 22-ish); YAML `/home/pi/Tuning-Files/pipeline/pisp-depth4.yaml` (evening-4 findings:55); config.md:125; branch gate 385 (`storage_preroll_active`); A10 named both merge mechanisms; fork-log `ce0bd90` (`_env_off`), `01f170c`; `b1-arm.sh:173-186, 271-284`; `take3v3.sh:52` reads `/proc/$CORE/environ` (C2: :50); R2 §5.16's wait is `e3-unit.sh:19-20`. Adopted: v2 §5 (pre-roll ON, merge over the socket only, one drop-in line), H3, H4, D. Open: v2 §5 still says "armed once per evening"; the unit is the boot (v2 §7's WAITING rule covers the reboot). |
| F7 | **HOLDS** | branch `storage-slowdown-plan.md:208` (`@reboot ... [ -f AUTORESUME ]`), no sentinel in `longtakes.py` (grep); gate masks `& 0xF` only (branch 395); `media-tune-file.md:27` (override on tmpfs); `longtakes-campaign-plan.md:5-6` ("Voltage normalised", EXT5V 4.78 V); hardware-log:307 (EXT5V 5.02 V). Adopted: v2 §7, H7, H16. |
| F8 | **HOLDS** | main 92 (`{2160: 2200, 1080: 1100}[h]` for 16-bit), 1138-1140 (`setup_mismatch` stops); hardware-log:899-903 (`cd548ef`, 187 modes, 3840x2072 at 10/12 bit, duplicate-size warning); `c1-probe-compare.md:219` (`e5b74d3`: Clear HDR 12-bit -> `[10]` 3840x2160 only, 16-bit -> `[20]` 3840x2200 only); test-structure:26. Adopted: v2 §4, H17. |
| F9 | **HOLDS** (worst case named, likeliest case not) | branch 646 `os.statvfs(MEDIA)` unguarded in `sample()`, `run()` 666-672 has no try (any exception ends the thread), the loop 1222-1236 reads `sam.last()` with no age check and ends on `el >= max_seconds` as `pass_<tier>`; `record_stop` only at 1251, the `finally` (1953-1990) restores settings only; SIGTERM only sets `stop['now']` (1517). Since the main loop's own `statvfs` (1230) raises on a dead medium, the likelier result is a traceback with Core still recording, not a false pass; the false pass needs the sampler to die for another reason. Both are fixed by H1/H7 (+ H15's watcher). |
| F10 | **HOLDS** (conditional) | config.md:414-415 (`workers`, `queue`: "media change"), :409-411 (`dontneed`/`writeback` once per process, `sync_ms` each take), :17; test-structure:76 ("Core re-reads it when a take starts") vs :101 ("Storage tuning A/B changed nothing ... `workers` 2/6, `queue` 24/48"); main 806-808 (no `workers 1`); `media-tune-file.md:33-34` (`tune_override=yes|no` only). The two KB pages do conflict; the `media tune:` line read is the right arbiter. Adopted: H19. |
| F11 | **HOLDS** (low) | hardware-log:296-300 ("CFE HAT NVMe `/dev/nvme0n1p2`", 2026-10-26; an M.2 2230 card sits in a CFe-B carrier in that hat, so the shell is probable, the KB does not say it); main 24-35 `hwmon` once at import; `R6.md:130` (`ERFM` = E27T, `ELFMB` = E21T, unconfirmed); `probe-exfat-dir.md:169` (Core idle). Adopted: v2 §2 ("probably ... same hat slot and shell"), S1 "Core idle, not stopped", H8. |
| F12 | **HOLDS** | branch 389-390 (`NEEDS A HUMAN: the Mode Ladder is on`) -> `wait_for_quiet` False -> `gate_timeout` -> stop list 1530; `set_mode_ladder` (fork-log `0041ba0`), `take3v3.sh:60, 109`; main 433 `set_preview_tdn`; fork-log:158; `recipe.md:49, 74-75` (TDN off by tuning file). Adopted: v2 §5, H4, H10. |
| F13 | **HOLDS** (low) | branch 671-672 (CSV flushed per sample); smart-log needs the helper word; no survival/claims item existed. Adopted: H13. v2 §9 does not name the samples CSV in its "never during a take" list; the status-only read covers it. |

Summary: 11 HOLD (F6 with line-number slips of 2-3 lines, F9 with the likelier failure mode being a traceback, F11/F13 low), 1 OVERSTATED (F3: the "lines may not exist" premise), 0 REFUTED. C2 §0.3 (the ~99 ns all-in slope vs the probe's 63.3 ns) is confirmed on the branch (`49c6f46`: "CPU slope of a real take implies an all-in cost of about 99 ns per entry") and v2 §7 now reads "77-133 ns per directory entry".

### Section H against C2 §3

C2 §3 asked for, H lacks: **A1** (`--disk-mbps` from S1's 60-s write, refuse the 354 default on an NVMe; keep `storage_frontier`/A-B gate sane); **A2** (`--modes` mandatory, mode order from the argument); **A8** (kernel_tune disk name: `rstrip` gives `nvme0n1p`, class from `media_class`; conditional with H19); **A10**'s `split` field in `Cfg` and `.parts` recorded per take; **A14** (no path for the audio-buffer lever into the drop-in: H's D writes "the ONE env line", C2 F6 says "plus `APERTAR_AUDIO_BUFFER_MS` only when the lever is on", and v2 §5a's fallback `APERTAR_AUDIO_BUFFER_MS=1000` needs it); **B4**'s signature computation from the samples (CPU slope vs 77-133 ns, buffer slope in the last minutes, `dev_w_ticks`/write vs fill, `nvme_c` vs latency, `dirty_kb`: the S5 split trigger has no runner item); **B6** `--plan-only`; **C3** (MLV control; the branch's stage M); **A23**'s > 75 C end-of-take flag; **A22**'s "resume only when the runner's own last status was clean".
H states, C2 contradicts: the critical path "H14-H16 (S4/S5) -> H17 (Part B)" against H's own table (H14, H15, H17 block S2; Part B is H6's `--card`); D's `arm` as one env line (above). Everything else in H matches C2 §3 and the code read here (branch contents, 0.6 / 512 as Core's defaults, `--fix-budget` struck, sizes).
