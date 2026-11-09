# R10: what `working/tools/longtakes.py` already does, against the NVMe plan (read 2026-11-08, KB at origin/main 203204a)

Sources read: `working/drop-frames/nvme-4k-recipe-plan.md`, `longtakes-test-structure.md`, `longtakes-campaign-plan.md`,
`working/tools/longtakes.py` (1,464 lines, all), `webui_remote.py`, `webui_client.py` (header), `make_results_xlsx.py` (header,
sheet list), the SSD run `working/drop-frames/tests-2026-11/longtakes-ssd-2026-11-07/` (session.json, results.md, results.csv,
runner.log, longtakes.db schema and counts, one journal file, samples CSVs), and the unmerged branch
`origin/claude/practical-johnson-he481b` (one commit `676a089`: runner telemetry, `longtakes_fill.py`, `storage_facts.sh`,
`exfat_write_probe.py`). Line numbers are those of `working/tools/longtakes.py` at `203204a` unless another file is named.
Nothing was run against a camera; no KB file was modified.

The owner's 2026-11-08 requirements (a)-(r) in section 6 are taken from the task brief; they are not written down in the KB
(grep for ledger / status file / 500 GB finds only the inspection plan of 2026-11-02 and the NVMe plan's section 3).

---

## 1. CLI and session layout

**Entry point:** `main()` (1029-1452), stdlib only, Python 3, runs ON the Pi (`python3 -I longtakes.py --out ~/longtakes/<session>`,
copy kept in `~/longtakes/bin/` per the campaign plan). Talks to Core over the Unix socket `SOCK = '/tmp/apertar-core.sock'`
(17; `core()` 45-67 sends one JSON line and returns the first `{"ok"...}` line, 20 s timeout) and to the WebUI over
`http://127.0.0.1:8000/api/state` for the audio settings only (`ui_audio` 511-518).

**Arguments** (`argparse` 1031-1052):

| arg | default | effect |
| --- | --- | --- |
| `--out DIR` | required | run directory; `~` expanded (1054); re-running with the same DIR resumes |
| `--dry-run` | off | prints per mode MB/frame, MB/s at 25 fps, storage cap fps, RUN / `excluded: storage too slow`, the stage upper bounds and the A/B variant list; returns before touching Core (1066-1075) |
| `--max-seconds N` | 0 | caps every walk take (smoke test); the outcome label becomes `pass_capped_<N>s` unless N is in `TIER_NAMES` (906-909) |
| `--only N` | 0 | stop after N unfinished configs have been walked (1158-1160; counted per `walk_config`, not per take) |
| `--web-remote` | off | WebUI-on takes use the Mac client via the `web_flag` file instead of a local stand-in (869-879) |
| `--clear-all` | off | `clear_media` also deletes clip folders present when the session started (463, 474) |
| `--modes a,b` | all storage-possible modes | `MODE_FILTER`; when given, `mode_possible` is NOT checked (128-129) |
| `--fps-start F` | 0 | overrides the first fps of every walk (1169) |
| `--disk-mbps X` | `DISK_MBPS` = 354.0 (83) | the drive's sustained MB/s: decides mode inclusion, the walk's start fps and the A/B gate |
| `--stages` | `'1d2rc'` | 1 baseline per mode, d one-factor configs, 2 storage A/B, r combinations, c the 10/20/30 min ladder, F Log follow-up (1414-1431; F is not in the default) |
| `--ab-seconds` / `--ab-reps` / `--ab-variants` | 120 / 3 / all | A/B take length, repeats, variant subset (1043, 1051-1052, 1055-1056) |
| `--start-at-mode-max` | off | walks start at the mode's own `fps_take_max`, not at `mode_cap_fps` (1167) |
| `--tier1-seconds` | 300 | round 0 (walk) take length, `SCREEN['s']` (85, 1058) |
| `--tier10-seconds` / `--tier2-seconds` / `--tier3-seconds` | 600 / 1200 / 0 | ladder lengths; 0 = 30 min or drive full (1046-1048) |
| `--tier-top` | `'3,2,1'` | survivors per mode in the 10, 20, 30 min rounds (1049, 1378) |
| `--no-prune` | off | test every config, ignore `prune_reason`, the frontier and the smart step (1050, 1151, 1173, 1207) |

There is no `--only`-by-name, no stage for a 60 s probe, no `--budget`, no `--status` option.

**Session start** (1076-1126): `get_state` must answer or the script exits (1076-1078); `findmnt`/`lsblk` give the device behind
`/media/RAW` (`MEDIA`, 18) and its parent disk (1079-1082); `session.json` is written once (1083-1104) with Pi model, kernel, Core
commit (`git -C ~/ApertarCore log -1`), drive model/size/transport, mount options, `disk_mbps_sustained`, `modes_run` and
`modes_excluded_storage_too_slow`, tuning file, UI service state, throttle flags, kernel-tune read-back, Core's original settings
(fps, bit depth, compression, Log, TDN, phase lock, speed ramp, Clear HDR, resolution), Pi revision, eth0 MAC, `preexisting_clips`;
`audio_original` is added from the WebUI (1120-1123). `backfill()` (718-750) loads any CSV rows missing from the DB, the session
dict goes into the DB `session` table (1107-1114), `PRESERVE` is filled from `preexisting_clips` (1115), `set_fps_speed_ramp False`
(1119), SIGTERM sets `stop['now']` (1125).

**Files written, all under `--out`** (nothing is written to `/media/RAW` by the runner itself):

| file | written by | when |
| --- | --- | --- |
| `runner.log` | `log()` 402-406 (also printed to stdout; the SSD run kept `stdout.txt` as a redirect) | every event; between takes except for warnings inside `run_take` |
| `results.csv` | `append_row` 761-768, header `FIELDS` 753-758 written only when the file is new | one row per take, plus `pruned` / `exhausted` rows |
| `results.md` | `write_md` 776-800, regenerated from the whole CSV | after every `append_row` |
| `session.json` | 1083-1104, 1121-1123 | once at start |
| `longtakes.db` | `db_ingest` 637-693 in a thread (`start_ingest` 699-708) | after each take, "while the next take is set up"; `join_ingest` before the next `record_start` (880) |
| `samples/<take_id>.csv` | `Sampler` 309-399 | DURING the take, one line per sample, flushed each time (395) |
| `journal/<take_id>.log` | 961-964 | right after the take (`journalctl -u apertar-core --since <take start>`) |
| `webui/<take_id>.log` | the local stand-in `webui_client.py` (876-878) | during WebUI-on takes without `--web-remote` |
| `web_flag` | `web_flag()` 497-499, appends `1` / `0` | at the start and end of a WebUI-on take with `--web-remote` |

Take id = `<cfg_id>_fps<int>_<HHMMSS>` (848), no date; cfg_id = `<mode>_<unc|lossless>_log%d_tdn%d_lock%d_trim%d_web%d` (119-122).

**Resume:** `walk_config` returns at once if the config already has a `pass*`, `skipped_unavailable`, `exhausted` or `pruned` row
(1145-1149); otherwise the walk continues at `min(fps already tried) - 1` (1170-1172). `bracket()` passes the prior rows of the same
variant label to `bracket_search` (1282-1283). The A/B stage counts finished reps per variant (`collections_count` 1455-1460, 1265).
The SSD `runner.log` shows four restarts in the first ten minutes, each resuming correctly.

**What runs on the Mac:** `webui_remote.py` (41 lines): one ssh session doing `tail -n1 -F <rundir>/web_flag` on the Pi and starting /
stopping `webui_client.py` (the browser-page stand-in: GET `/api/state` once a second plus the MJPEG preview, read-only) against
`apertar.local:8000`; it logs to a hard-coded Mac path (`~/Documents/Apertar/apertar-kb/working/drop-frames/tests-2026-11/webui-mac`,
line 18). `make_results_xlsx.py` (openpyxl; sheets `Max fps`, `Minutes`, `Takes`, `Notes`, lines 6, 121, 189, 229, 248) reads
`longtakes.db` on the Mac. On the branch, `longtakes_fill.py` (Mac or Pi, read-only analysis of a run dir). Without `--web-remote` the
WebUI stand-in runs on the Pi itself (875-879), which is not the lever the NVMe plan describes.

**Shutdown** (`finally` 1432-1452): tuning override cleared and kernel tuning restored (`set_variant 'base'`), Clear HDR, resolution,
TDN, phase lock, trim (forced on), compression, bit depth, speed ramp, fps restored from `original_settings`; audio format restored if
it had been switched; Log is left "as last set" (1452). `record_stop` is NOT in the `finally` (see section 7).

---

## 2. The take loop, step by step

### 2.1 Applying a config: `apply_cfg(c, fps)` (419-438) and `verify()` (441-452)

Order and sleeps: `get_state`; `set_clear_hdr enabled=` if it differs (+4 s); `set_resolution width= height=` if it differs (+4 s);
a bit-depth round trip `set_raw_bit_depth value=<other>` (+5 s) then `value=<wanted>` (+6 s), "so every take starts from a fresh
camera config" (420, 427-429; other = 16->12, 12->16 if HDR else 10, 10->12); `settle()` (409-416: wait up to 40 s for
`state == 'ready'` and not recording); then without waiting between them `set_cdng_compression value=`, `set_cdng_log value='on'|'off'`,
`set_preview_tdn enabled=`, `set_fps_phase_lock enabled=`, `set_media_trim enabled=`, `set_fps value=<float>`; +4 s; `settle()`.
Minimum ~15 s plus settle per take, ~23 s when HDR or resolution change. `walk_config` additionally calls `apply_cfg(c, 25)` once per
config before the walk to learn `fps_take_max` / `fps_max` (`MODE_MAX`, 1162-1164).

`verify()` compares `get_state` with the request: `raw_bit_depth`, `cdng_compression`, `cdng_log_applied` (Core's own verdict, not
the switch), `preview_tdn`, `fps_phase_lock`, `fps` (within 0.01), `resolution` string, `clear_hdr`. Any mismatch -> outcome
`skipped_unavailable` when the only mismatch is `log_applied` and Log was wanted (then `log_probe()` 521-539 makes a 4 s take and keeps
Core's `CineMate Log` journal lines as the reason, deleting the probe clip), else `setup_mismatch`, which stops the campaign
("needs a human", 1138-1140). `media_state != 'mounted'` -> `media_not_mounted`, also a stop (861-863, 1138).

**Tuning override and kernel tune** (storage A/B only, `set_variant` 827-844): `~/ApertarCore/scripts/apertar-tune clear` then
`set k=v ...` for `workers`, `queue`, `sync_ms` (`TUNE_CLI` 810; Core re-reads the override at `record_start`); `kernel_tune` by calling
the root helper directly, `sudo -n /usr/local/libexec/apertar-media-tune apply|restore <disk> <class> exfat` (839-840) with
`KT['class']` defaulting to `'usb-storage'` until a take's journal line supplies `media_class` (840, 1135-1136). Read-back:
`kernel_readback()` (818-824) reads `/proc/sys/vm/dirty_bytes`, `dirty_background_bytes`, `dirty_writeback_centisecs`,
`/sys/block/<disk>/queue/{scheduler,nr_requests,rq_affinity}` into the `tune_readback` column. The disk name is derived by
`os.path.basename(KT['dev']).rstrip('0123456789')` (819, 838): `sda1 -> sda` works, `nvme0n1p1 -> nvme0n1p` does not (section 7).

**WebUI client** (867-879): with `--web-remote`, `web_flag` gets a `1` and the runner waits up to 30 s for a non-loopback
connection on port 8000 (`ss -tnH state established '( sport = :8000 )'`, `web_peers` 486-494; `wait_peers` 502-508); if none,
the take runs anyway with `mismatch = web_client_not_connected`. Without the flag a local `webui_client.py` is started on the Pi.

### 2.2 Starting: `run_take()` (847-1026)

Start temperatures (`start_pi_c`, `start_nvme_c` from `/sys/class/thermal/thermal_zone0/temp` and the `nvme` hwmon, 864-865; the
hwmon lookup `hwmon('nvme')` 24-35 runs once at import). `before = clip_dirs()` (866). `join_ingest()` so the DB thread is idle
(880). The `Sampler` thread starts (881-885), then `record_start` (886); if Core answers `not supported by this device` the audio
format is switched to `auto` (`set_audio_capture_options format=auto`) and `record_start` is retried (887-890), restored at the end.

### 2.3 The sampler (`Sampler` 309-399)

Docstring says 1 Hz; the loop waits 0.5 s (396), and the SSD CSVs show 0.5 s spacing (t_s 0.3, 0.8, 1.3 ...), so ~2 samples/s.
Each `sample()` (367-387): CPU % from `/proc/stat`, `MemAvailable`, `statvfs(MEDIA)` -> `fill_pct`, `free_gb`, `vcgencmd get_throttled`
(a subprocess per sample), **`get_state` over the socket** (the whole state dict kept as `_st` for the stop logic), Core's CPU
(`core_cpu()` 333-360: per-thread utime+stime from `/proc/<pid>/task/*/stat`, summed in % of one core, plus the single busiest thread as
`name:%`; the pid is found by scanning `/proc/*/cmdline` for `apertar-core --socket`, 322-331), Pi temperature, NVMe temperature.
Columns written (316-317): `t_s, pi_c, nvme_c, cpu_pct, load1, mem_avail_mb, fill_pct, free_gb, throttled, dropped, state,
core_cpu_pct, core_top_thread`. `dropped` = `recording_dropped_frames` from `get_state`; `state` = `rec` or Core's state string.
Not sampled: Core's write-buffer level, drop counters by kind, the disk's own stat counters, dirty/writeback pages, per-thread CPU
for every thread (the branch adds all but the last; see section 7 end).

### 2.4 Stop conditions (loop 896-922, polled every 0.5 s on the latest sample)

In priority order:
1. `stop_on_drop and last['dropped'] > 0` -> outcome **`drop`** (902-903). (Not called `first_drop`; off in the A/B stage, 1273.)
2. `statvfs` free < `CAPACITY_GUARD` = 6 GiB (20, 904-905) -> **`pass_drive_full`** (a pass).
3. elapsed >= `max_seconds or 1800` -> **`pass_30min`**, or `pass_<tier>` for 300/600/1200/1800 (`TIER_NAMES` 86), else
   `pass_capped_<N>s` (906-909).
4. Core no longer recording after >3 s (910-920): if `buffer_safety_stop` was true in any of the last 12 samples -> **`buffer_full`**;
   elif free < 1.5 GB -> `drive_full`; else **`stopped_externally`**.
5. `recording_error` or `recording_fault` in the state -> **`fault`** (921-922).
`stop['now']` (SIGTERM) is NOT checked inside this loop: a take always runs to one of these ends.

After the loop: `record_stop` (925), the stand-in client is terminated / `web_flag 0` + wait for the peer to go (926-929), up to
180 s until `not recording and not media_writes_pending` (931-937), +3 s, sampler stopped (938).

### 2.5 After a take (939-1025)

`drive_full` = outcome is `pass_drive_full`/`drive_full` or free < 1.5 GB (940-942). The clip = the newest new `cDNG*` folder
(943-944); DNGs are counted **recursively** (`os.walk`, `_(\d{9})\.dng$`), so a split clip's `part_NNN/` folders count the same;
sidecars in the clip root (the WAV) are listed with sizes into `audio`, `missing` = highest frame number + 1 - count (947-960).
The Core journal since the take's set-up is saved (961-964) and parsed (`parse_journal` 552-567): `drop[<kind>]: +N` lines -> `kinds`
and `first` (= time of the first drop line minus `record_start` time), `apertar-media-trim ... COMMAND` lines -> `trim_events`,
the stats line keys `STAT_KEYS` (548-549: `enqueued, dropped_queue_full, dropped_gap_estimate, peak_queue, queue_bytes_peak,
queue_budget, write_failures, fault`). `buffer_peak_pct = queue_bytes_peak / queue_budget` (968-972); a `stopped_externally` with
>= 88 % is re-classified **`buffer_full`** (973-975). `buffer_setting`, `buffer_safety_stop`, `buffer_flush_discarded` come from a
final `get_state` (976-979); `media_class` from the `recording clip:` journal line (980-983; `dontneed=` and `writeback=` on the same
line are not extracted). `dropped = max(state counter, sample at the stop, missing)` (984). `gb_written = files x mean size of the
first 20 DNGs found` (985-989). `core_cpu_avg/max` and the most frequent top thread over the take (990-994). A/B takes become
`ab_clean` / `ab_dropped` (995-996). `cause_estimate` by `estimate_cause()` (570-594), heuristic text only.
**Clip deletion:** the take's own clip is deleted right here, unconditionally (`shutil.rmtree`, 1017-1018), then +8 s if trim is on
and >1 GB was written (1020-1021); the since-trim byte counter `written['gb']` is reset when a trim was seen or trim is on, else
accumulated (1019; it feeds only the "untrimmed-drive stall" cause text, 584-585). The row and the payload (samples, journal lines,
`t_rec_wall`) return to `take()` (1130-1141), which appends the CSV row, regenerates `results.md`, starts the DB ingest thread, and
stops the campaign on `record_start_failed` / `setup_mismatch` / `media_not_mounted`.

**Before every take**, in every stage, `clear_media(out)` (470-480) deletes every `/media/RAW/cDNG*` directory not in `PRESERVE`
(+8 s), and the walk refuses to start a take with < 20 GiB free (1192-1194). So today clips are deleted twice: right after their take
and again (whatever is left) before the next.

**Restart handling:** `stopped_externally` with zero drops is "not a result": the walk repeats the fps up to 2 times per config
(`ext_stops`, 1198-1204), the A/B take up to 3 attempts (1272-1277), `bracket.attempt` twice (1292-1294); then the campaign stops.
`fault` is treated as an ordinary failure (fps - 1 next, 1226).

---

## 3. The search logic

**Config space** (`all_configs` 132-143): per included mode, 2 x 2 x 2 x 2 x 2 x 2 = 64 configs of (compression none/lossless_jpeg,
Log, TDN, phase lock, trim on/off, WebUI). Order: stage 1 = each mode's baseline (`unc log0 tdn0 lock0 trim1 web0`), stage d = the 6
one-factor configs per mode, stage r = the remaining 57, sorted by `distance()` (number of factors away from the baseline, 124-125)
then id. The SSD run: 7 modes x 64 = 448 configs.

**Mode gate** (`MODES` 78-81; `mode_size_mb` 89-93 = w x raw_h x bits / 8 with 16-bit raw heights 2200/1100; `mode_possible` 96-97:
size x 25 fps <= `DISK_MBPS x 0.98`; `mode_cap_fps` 107-109 = int(`DISK_MBPS x 0.98` / size)). With the default 354 MB/s:
4kSDR12 cap 27, 4kSDR10 33, 4kHDR12 27, 4kHDR16 **20 -> excluded**, 2K modes 82-133. The walk starts at
`min(fps_take_max, mode_cap_fps)` unless `--start-at-mode-max` (1167). `--modes` bypasses `mode_possible` but not `mode_cap_fps`.

**Round 0 walk** (`walk_config` 1143-1231): take of `SCREEN['s']` (300 s) at the start fps; on failure fps - 1 (1226) down to
`FPS_FLOOR = 25` (19); stop at the first `pass*` (1206) or `skipped_unavailable` (1205); write `exhausted` when 25 fails (1227-1231).
**Smart step** after `buffer_full` (`smart_next_fps` 278-293, used 1207-1225): drive-written fps = `fps x (enqueued - peak_queue) /
enqueued`, x 1.35 if the take was < 4 s else x 1.15, clamped to [25, fps - 1]; if the estimate is < 20 fps (0.8 x floor) the config is
`pruned` "ruled out in theory"; needs enqueued >= 60 and >= 1.5 s. No step logic exists for capture-gap failures (1 fps at a time).

**Pruning** (`prune_reason` 222-241, skipped with `--no-prune`): a non-baseline config is pruned when (a) the mode's baseline was clean
at the top fps (`limiter_of` 176-194 returns an empty set: "nothing to improve"); (b) a single factor is not in `RELEVANT` for the
limiter (172-173: storage -> comp, log, trim; capture -> tdn, lock, web, log; the limiter is read from the failures just above the
clean fps: `buffer_full`/`queue-full` -> storage, `capture-gap` -> capture); (c) a combination contains a factor that did not beat the
baseline alone (`beneficial_factors` 211-219, `compare_scores` 197-208: a pass beats a fail; both passed -> higher fps; both failed ->
>= 2x time to failure = better, <= 0.5x = worse, else neutral). **Data-rate frontier** (`storage_frontier` 296-306, used 1173-1187):
the lowest MB/s at which an uncompressed, Log-off take of the same frame size (+-3 %) ended `buffer_full`; the walk starts below it,
and a config whose 25 fps rate is at/above it is `pruned`. **No-difference** (tier rounds, 1400-1408): among the configs tied at the
best fps of the previous round, one whose factor set is a strict superset of a kept config's is dropped with a log line.

**Stage 2, storage A/B** (`ab_stage` 1233-1279): only for modes whose baseline was storage-limited (1241-1245) and only at
>= 70 % of `DISK_MBPS` (1259-1262); targets = the mode's best config (`config_score` 146-156) plus the plain baseline; fps = one above
the config's best pass (or 25); `AB_VARIANTS` (806-808) `base, workers2, workers6, queue24, queue48, sync500, sync2000, kerneltune`,
interleaved, `--ab-reps` x each, `--ab-seconds` long, `stop_on_drop=False`, outcome `ab_clean`/`ab_dropped`/`buffer_full`.

**Stage c, the ladder** (`tier_stage` 1372-1411): rounds `tier10`, `tier20`, `tier30` (600, 1200, 0 = 30 min s); per mode the configs
at the best fps of the previous round (round 0 passes for tier10), tie broken toward fewer switches, at most `--tier-top` per round
(3, 2, 1); each runs `bracket()` (1281-1300) -> `bracket_search(f0, prior, attempt)` (244-275): start at f0, after a failure go down 3,
6, 12 ... fps until a pass, then bisect between the highest pass and the lowest failure down to 1 fps (no "leave 2 fps alone" rule
for long rounds); prior rows of the same label are reused; floor 25. Durations: 5 (round 0) / 10 / 20 / 30 min; no 60 s round in the
code (`--tier1-seconds 60` would shorten round 0 but keep the 10/20/30 ladder and label the pass `pass_capped_60s`).

**Stage F, Log follow-up** (`follow_log_stage` 1302-1370): 4K modes first; parents = configs that ever hit `buffer_full`/`queue-full`
plus the 30-min winner; each gets a Log twin walked (forced, from 1.4 x the parent's 5-min fps) and, if it gained or is the winner's
twin, the `logt10/logt20/logt30` bracket rounds; a mode with no parent tries lossless, lossless+Log, Log.

**Outcome labels in use:** `pass_5min`, `pass_10min`, `pass_20min`, `pass_30min`, `pass_drive_full`, `pass_capped_<N>s`, `drop`,
`buffer_full`, `drive_full`, `stopped_externally`, `fault`, `record_start_failed`, `setup_mismatch`, `media_not_mounted`,
`skipped_unavailable`, `pruned`, `exhausted`, `ab_clean`, `ab_dropped`. `config_score` ignores `exhausted`, `stopped_externally`,
`skipped_unavailable`, `pruned` and all variant rows (148-149). SSD run: 189 takes in the DB (`buffer_full` 118, `pass_*` 40,
`ab_clean` 24, `skipped_unavailable` 7); 629 CSV rows (440 `pruned`/`exhausted`); no `drop` outcome ever occurred.

---

## 4. Data: schema, per-second columns, results columns

**`longtakes.db`** (`DB_SCHEMA` 599-623, confirmed identical in the SSD file):
- `session(k, v)` - session.json as JSON strings (20 rows).
- `takes(take_id PK, cfg_id, mode, bits, comp, log, tdn, lock, trim, web, fps, outcome, seconds, dropped, first_drop_s, drop_kinds,
  cause_estimate, pi_c, nvme_c, pi_c_max, nvme_c_max, cpu_pct, load1, mem_avail_mb, fill_pct, throttled, files, missing, audio,
  gb_written, trim_events, drive_full, drive_full_at_s, start_pi_c, start_nvme_c, clip, started, mismatch, variant, media_class,
  buffer_setting, buffer_safety_stop, buffer_flush_discarded, tune_readback, core_cpu_avg, core_cpu_max, core_top_thread)` - 47 cols.
- `samples(take_id, t_s, pi_c, nvme_c, cpu_pct, load1, mem_avail_mb, fill_pct, free_gb, throttled, dropped, state, core_cpu_pct,
  core_top_thread)` + index; 141,163 rows for 189 takes; `core_cpu_pct` present for 28 takes (46,206 rows; busiest threads seen:
  `CameraManager`, `apertar-core`), because the CPU columns were added mid-run.
- `drop_events(take_id, t_unix, t_rel_s, kind, frames, dt_us, nominal_us)` from `drop[kind]: +N ... dt_us= nominal_us=` lines
  (680-684); **0 rows** in the SSD run (no capture drops happened).
- `stats(take_id, k, v)` the stats-line keys; `journal(take_id, t_unix, line)` raw lines; view `config_summary`.
- `db_ingest` is idempotent per take (DELETE then INSERT, 649-650) and adds missing columns with ALTER TABLE (645-648).

**`samples/<take_id>.csv`:** the 13 columns above; the SSD run's early files have 11 (no `core_cpu_*`). `nvme_c` empty on the SSD.

**`results.csv`** (`FIELDS` 753-758, 49 names): the `takes` columns plus `stats` (JSON of the stats line) and `buffer_peak_pct`. In the
SSD file the header has 46 names and 35 later rows have 49 values (the header is written once, 766; `FIELDS` grew mid-run), so
`csv.DictReader` files those rows' `core_cpu_*` under `None`; the DB got them from the in-memory row, not from the CSV.

**`results.md`** (`write_md` 776-800): header line (Pi, Core commit, `sess.get('nvme')` - a key that does not exist, hence
"drive: None"), one table row per CSV row: `mode, comp, log, tdn, lock, trim, web, fps, outcome, s, dropped, first drop s, kinds,
Pi C, NVMe C (peak), cpu %, RAM avail MB, fill %, drive full at s, cause (estimate)`; then "Best clean fps per config (first pass
while stepping down)" with `config, fps, outcome, minutes` (one row per config, last pass wins). No per-mode duration-vs-fps table,
no Core CPU, no bytes written, no variant/tier label in the table.

---

## 5. Monitoring today

Between takes a person can `tail -f <out>/runner.log` (one line per take: `cfg fps -> outcome after Ns dropped= kinds= pi= nvme=`,
plus `==`/`--` lines for stage decisions, smart steps, prunes), read `results.md` (regenerated after each take) or query
`longtakes.db` (ingest finishes within the next take's set-up; a 120 s join cap, 714). `session.json` is static. There is **no
status file** (no "current take / fps / elapsed / next planned"), no progress line during a take, and `runner.log` is silent during a
take except for warnings. The only thing written during a take is `samples/<take_id>.csv` (every 0.5 s, flushed) - readable over ssh
with `tail`, and it does show elapsed time, free GB, dropped and Core CPU. `web_flag` tells the Mac side when a client is wanted.
Control: SIGTERM ends the campaign after the current take (up to 30 min later); Ctrl-C interrupts the take loop without
`record_stop` (section 7). The `--dry-run` listing is the only plan preview.

---

## 6. Gap table

Legend: BUILT / PARTLY / MISSING; anchors are `function (lines)` in `longtakes.py` at `203204a`; "branch" = `676a089` on
`origin/claude/practical-johnson-he481b` (unmerged).

### 6a. `nvme-4k-recipe-plan.md` section 9

| # | Item | Status | What exists / what is missing |
| --- | --- | --- | --- |
| 9.1 | Three modes, no storage exclusion, NVMe temperature | PARTLY | `--modes 4kHDR16,4kHDR12,4kSDR12` bypasses `mode_possible` (`included_modes` 128-129); `4kHDR16` is in `MODES` (81); NVMe temp via `hwmon('nvme')` (24-35), per sample (382) and at take start (865). Missing: with `DISK_MBPS` left at 354 the walk start `min(fmax, mode_cap_fps)` (1167) is 20 fps for HDR16 -> the `while fps >= 25` loop never runs and an `exhausted` row is written at once (1190, 1227-1231); 4K 12-bit starts at 27. Needs `--disk-mbps ~733` or `--start-at-mode-max`; the A/B gate (1259-1262) and the dry-run labels use the same constant. |
| 9.2 | 60 s probe round + log(T)-vs-fps fit | MISSING (fit) / PARTLY (probe) | `--tier1-seconds 60` shortens round 0 (1045, 1058, 1195) but there is no separate probe round before the 5-min bracket, and a 60 s pass is labelled `pass_capped_60s` (906-909; `TIER_NAMES` 86 has no 60). No fit anywhere: capture-gap failures step 1 fps (1226); only `smart_next_fps` (278-293) for `buffer_full`. Already built, as the plan says: Log probe with Core's reason (`log_probe` 521-539, 856-858), Core CPU per sample (sum + busiest thread, 333-360) and per take (990-994). |
| 9.3 | Write-budget guard | MISSING | `gb_written` per take (985-989, files x mean of 20 sampled DNG sizes) and `written['gb']` since the last trim (1019, 1126) exist; no cumulative total, no projection before a take, no cap, no report. |
| 9.4 | Control takes + spread-based no-difference | MISSING | No control takes anywhere; "no difference" = `compare_scores` 2x/0.5x rule on single scores (197-208) and the equal-fps superset rule in `tier_stage` (1400-1408). |
| 9.5 | Group testing of storage knobs + greedy stacking | MISSING | `AB_VARIANTS` one knob per variant (806-808); the `r` stage is every combination of individually-helpful factors (`prune_reason` 238-240), not greedy forward selection. |
| 9.6 | Restart-batch protocol (env file, `NEED_RESTART`, `/proc/<pid>/environ` check) | MISSING | Nothing writes an env file or pauses for a restart; `find_core()` (322-331) locates the pid only for CPU sampling; `dontneed=`/`writeback=` on the `recording clip:` line are not read (980-983). Group B/C levers (FE depth, dontneed, writeback, priority, direct I/O, UI off, mount flags, PCIe gen) have no representation in `Cfg` (112-125). |
| 9.7 | NVMe watchdog | MISSING | Present: `media_state != 'mounted'` -> `media_not_mounted` -> stop (861-863, 1138-1140); `fault` outcome from `recording_error`/`recording_fault` (921-922). Missing: kernel-log scan for `nvme`/`pcie`/`exFAT`, `media_alive`, and "never retry": a `fault` is followed by the next fps (1226); `stopped_externally` is retried twice (1198-1204). A `statvfs(MEDIA)` failure mid-take raises inside the sampler thread (376) and the main loop (904) - a crash, not a stop. |
| 9.8 | Duration-vs-fps report in `results.md` and the KB | PARTLY | `results.md` has the per-take table and "Best clean fps per config" (776-800); `make_results_xlsx.py` `Minutes` sheet (longest clean take per fps heat map, line 189) is the closest thing, Mac-side, from the DB. No per-mode duration-vs-fps table, no cause column per fps, no KB page written by the runner. |
| 9.9 | Offline tests (fit, budget guard, neutrality) | MISSING | No test file in the repo references `bracket_search` or `smart_next_fps` (grep: only `longtakes.py`); the docs' "tested offline" has nothing committed. |

### 6b. Owner requirements of 2026-11-08

| # | Requirement | Status | Anchor and detail |
| --- | --- | --- | --- |
| a | Card-size adaptation (read the drive size, per-mode max take length, 500 GB vs 1 TB) | PARTLY | Drive model/size recorded (`lsblk -dno MODEL,SIZE,TRAN`, 1088) and free space sampled (`sample` 376-377); a clean take stops at < 6 GiB as `pass_drive_full` (`CAPACITY_GUARD` 20, 904-905) with `drive_full_at_s` (940-942). Missing: no computation of the longest take a mode/fps fits on this drive, no planning use of the size (the 30-min round simply runs until the guard). |
| b | No 75 % fill rule, only a physical-fit gate | PARTLY | No fill-percentage gate exists: the gates are 6 GiB during (904), 1.5 GB for `drive_full` (916, 940), 20 GiB before a take (1192). "75 %" survives only as a cause-estimate annotation (582). Missing: a true fit gate (project bytes = fps x seconds x MB/frame before `record_start` and compare with free space); today a take that will not fit is started and ends as a pass at 6 GiB. |
| c | No cool-down | BUILT | No temperature waits; the only sleeps are Core's trim settle (8 s, 480 and 1021) and the config sleeps (424-437); start temperatures logged (864-865). |
| d | Stop on first drop + buffer-full as results | BUILT | `drop` on `recording_dropped_frames > 0` (902-903, label `drop`); `buffer_full` from `buffer_safety_stop` in the last 12 samples (910-915) or `queue_bytes_peak/queue_budget >= 0.88` (968-975); both feed `limiter_of` (176-194), the smart step (1207) and stage F (1330). Off in the A/B stage (1273). |
| e | Delete clips only when the next take needs the space | MISSING | Today: the take's own clip is deleted right after it (`shutil.rmtree`, 1017-1018); `clear_media` before every take in every stage (1191, 1270, 1277, 1288) deletes all `cDNG*` folders except `PRESERVE` (470-480); `log_probe` deletes its probe clip (537-538). No "fits -> keep" decision. |
| f | Status file for ssh monitoring, written only between takes | MISSING | No status file; `results.md`/`results.csv` after each take (761-768), `runner.log` on events (402-406), `samples/*.csv` DURING the take (395). Nothing summarises "current take, started, planned length, next step, bytes so far". |
| g | Wear ledger (bytes per take and cumulative; nvme smart-log via a helper) | PARTLY | Per take `gb_written` (985-989) in CSV/DB; since-trim counter only (1019). Missing: cumulative per session/per drive, a cap, any smart-log reading (the plan says the runner has no root; branch `storage_facts.sh` only prints the `sudo nvme smart-log` command for the owner). The SSD run's rows sum to 5,908 GB. |
| h | `frames_per_folder` / `clip_merge` control per take, recursive DNG counting | PARTLY | Recursive count BUILT (947-960, 987; commit `429019f`; branch identical). Missing: no `set_frames_per_folder` / `set_clip_merge` call, no `APERTAR_CLIP_MERGE=0`, no `Cfg` field, no `verify()` of `frames_per_folder` / `clip_merge_*` state; the knobs exist only on the Pi's `clip-split` branch (`fork-log.md` 175-185: `d7dd337`, `8874374`). With `clip_merge` default on, the merge worker flattens a split clip "while idle" - i.e. during the runner's post-take delete and the next set-up. |
| i | Split A/B (paired one-folder vs split at the long stages) | MISSING | No paired design anywhere; `tier_stage` brackets one config at a time (1372-1411). `probe-exfat-dir.md` 138-146 makes it mandatory for the 15/30-min stages. |
| j | FE config depth / dontneed / writeback restart batches | MISSING | See 9.6. |
| k | NVMe watchdog | MISSING | See 9.7. |
| l | Write-budget guard | MISSING | See 9.3. |
| m | Control takes + spread-based no-difference | MISSING | See 9.4. |
| n | log(T)-vs-fps fit | MISSING | See 9.2. |
| o | 4K crop modes (3840x2072 etc.) in `MODES` | MISSING | `MODES` (78-81) has only 3840x2160 and 1920x1080; `mode_size_mb` (92) maps 16-bit raw heights with a dict `{2160: 2200, 1080: 1100}` that raises `KeyError` for any other height at 16 bit (the dry run would crash on a `4kHDR16` crop entry). `apply_cfg` can set any resolution (`set_resolution width height`, 425-426) and `verify` checks the string (450). KB: the Pi's driver probed 3840x2072 and 1920x1036 at 10/12 bit (`lessons/hardware-log.md:901`); the apertar driver's 1.85:1 crop is 3840x2076 (`working/compare-raw/c1-probe-compare.md:219`), so the exact height to list depends on the installed driver. |
| p | WebUI client as a lever | BUILT | `web` factor (`Cfg` 113-125, `RELEVANT['capture']` 173); `--web-remote` + `web_flag` + `wait_peers` via `ss` on :8000 (486-508, 869-874); Mac side `webui_remote.py`; local stand-in otherwise (875-879). |
| q | Time to first drop recorded | BUILT | `first_drop_s` = first `drop[...]` journal line minus `record_start` time (552-561, 1000); `seconds` = time to stop (923); `drop_events.t_rel_s` (612-613, 680-684). Caveat: relies on Core's `drop[kind]: +N ... dt_us= nominal_us=` journal format and the 0.5 s sampler; never exercised in the SSD run (0 `drop_events`, 0 `first_drop_s`). |
| r | Core CPU per thread per second | PARTLY | Per sample: the sum over all threads in % of one core and the ONE busiest thread as `name:%` (333-360, columns 316-317); per take `core_cpu_avg`, `core_cpu_max`, modal top thread (990-994). Not every thread; the branch adds buffer level, disk stat, dirty/writeback, trim state and a CPU slope, still not per thread. |

### 6c. What the unmerged branch `676a089` adds (runner telemetry, 136 changed lines in `longtakes.py`)

- Sampler columns (`SAMPLE_COLS`, branch 316-318): `buffer_used`, `buffer_capacity` (Core's write-buffer level from `get_state` or a
  0.5 s-timeout `GET /api/buffer`, `buffer_level` 332-343), `dev_w_ios`, `dev_w_sectors`, `dev_w_ticks`, `dev_inflight` from
  `/sys/block/<disk>/stat` (`dev_stat` 323-329; `DEV['disk']` set from the parent disk in `main`, 1170), `dirty_kb`, `writeback_kb`
  from `/proc/meminfo`, `trim_running`, `trim_last_unix` from the state.
- Take columns: `queue_budget_mib`, `budget_seconds` (RAM budget in seconds of input), `recorder_stop_s` (`recorder stop time:` line),
  `stall_msg` (`no frame written` / `stopped responding` in the journal), `idle_gap_s` since the previous take ended (`LAST_END`),
  `core_cpu_slope` (linear fit of Core CPU over the take after 20 s; the "directory-walk signature"), `trim_before` (Core's last trim
  result and whether it finished since the previous take). DB `takes` grows to 54 columns, `samples` to 24; `FIELDS` +7.
- Same recursive DNG count as main (so `429019f` and the branch overlap there).
- `longtakes_fill.py` (236 lines, analysis): drain MB/s from the free-space series, implied queue vs budget, regimes of `buffer_full`
  takes, stop time, Core CPU per window, per-directory-entry cost from the CPU slope.
- `storage_facts.sh` (36 lines, read-only, no sudo): mount, cluster size, block device, discard_max_bytes, scheduler, driver chain
  (uas vs usb-storage), NVMe model/firmware/state/temperature, `nvme`/`pcie` cmdline args, HMB dmesg lines, writeback knobs, power,
  Core's trim state via `core.py get_state`, newest clip's DNG count; prints the root commands (`fstrim`, `smartctl`, `nvme smart-log`,
  `nvme id-ctrl`) for the owner.
- `exfat_write_probe.py` (340 lines): camera-free emulation of Core's DNG write pattern (workers, 480 KiB chunks, once-a-second fsync,
  prealloc, O_DIRECT, sub-folder every K files, fps pacing with a budget -> "buffer full"), per-file timing CSV; writes real data
  (wear), deletes what it made, refuses to run outside a mount point.
- Also on the branch: `storage-slowdown-plan.md` (212 lines) and `tests-2026-11/reanalysis-longtakes-ssd-2026-11-08.md`. The branch is
  one commit (`676a089`) on base `8a42f7b`, five commits behind main: it does not delete `nvme-campaign/probe-exfat-dir*` (those were
  added to main after the branch point; a plain diff shows them as deletions), but its `longtakes.py` and main's `429019f` both rewrote
  the DNG-count block of `run_take`, so a merge conflicts there and in `fork-log.md` / the READMEs.
None of the branch changes touch the search logic, deletion policy, status, budget or watchdog gaps above.

---

## 7. Risks in the code for an unattended NVMe run

1. **`DISK_MBPS = 354` is the SSD's number** (83). Left alone: `4kHDR16` is excluded by `mode_possible`, or, with `--modes`, walked from
   20 fps -> immediate silent `exhausted` (1167, 1190, 1227-1231); `4kHDR12`/`4kSDR12` start at 27 fps; the A/B gate skips modes
   under 70 % of 354 (1259-1262); `storage_frontier` margins (1175) and the dry-run text follow it. Pass `--disk-mbps` from a measured
   NVMe write test (733-759 MB/s per the plan) or `--start-at-mode-max`.
2. **Mode list.** Without `--modes`, every mode `mode_possible` admits runs (with an NVMe-sized `DISK_MBPS` that is all 8, 512 configs
   incl. the 2K modes); `4kHDR16` has no exclusion logic other than the MB/s arithmetic (96-97). `--modes 4kHDR16,4kSDR12,4kHDR12`
   is mandatory, and the plan's mode order (HDR16, SDR12, HDR12) is not what `MODES` gives (`all_configs` keeps `MODES` order:
   4kSDR12, ..., 4kHDR12, 4kHDR16).
3. **kernel_tune on NVMe is broken**: `basename(dev).rstrip('0123456789')` gives `nvme0n1p` for `/dev/nvme0n1p1` (819, 838) ->
   `/sys/block/nvme0n1p/...` read-backs are `?` and `apertar-media-tune apply nvme0n1p <class> exfat` targets a non-existent disk.
   `KT['class']` defaults to `usb-storage` until a take has reported `media_class` (840, 1135-1136): a `--stages 2` run on a fresh
   out dir would tune the NVMe as USB storage. The helper is called with `sudo -n` (needs the sudoers rule Core has).
4. **Clip deletion can hit the owner's clips.** `clip_dirs()` = every `/media/RAW/cDNG*` directory (455-459). `PRESERVE` is the set
   present at the FIRST start of that out dir (`session.json` `preexisting_clips`, 1101, 1115): any clip the owner records later (between
   resumes, during a pause) is deleted by the next `clear_media` (1191 etc.); `--clear-all` deletes everything; `log_probe` removes every
   new `cDNG*` folder after its 4 s take (537-538); `run_take` deletes the newest new folder (943-944, 1017) - a clip the owner starts
   during the runner's post-take window would be "the newest". Requirement (e) replaces this policy anyway; the fix should also refresh
   `PRESERVE` at every (re)start and never delete folders the runner did not create (match on names recorded in `results.csv`).
5. **No watchdog, and faults are retried.** `fault` -> next fps (921-922, 1226); `stopped_externally` -> up to two repeats (1198-1204);
   if the NVMe drops off the bus, `os.statvfs(MEDIA)` raises in the sampler thread (376; the thread dies silently, `sam.last()` goes
   stale) and in the main loop (904) -> traceback; the `finally` restores settings but does not `record_stop`. `media_state` is checked
   only before a take (861). Kernel log never read.
6. **Ctrl-C / SIGINT mid-take leaves Core recording**: `record_stop` (925) is after the loop; `KeyboardInterrupt` jumps to the
   `finally` (1432) which never stops the recording. SIGTERM (1125) is only honoured between takes (loop 896-922 ignores it), so a stop
   request can take 30 min.
7. **Sampler load during takes:** every 0.5 s a `get_state` socket round trip, a `vcgencmd` subprocess, `/proc/<pid>/task/*` scans
   (309-399); the branch adds an HTTP `GET /api/buffer` per sample when `get_state` lacks the buffer fields. The docstring and the plan say
   "1 Hz" / "nothing runs during a recording" (598) - the DB part is true, the sampler is not light. Also the Pi-local WebUI stand-in
   (875-879) adds preview-encoding load to the Pi when `--web-remote` is not used: a different lever from "a real client on the Mac".
8. **CSV header drift on resume:** `FIELDS` grew (core_cpu_*) without a header migration (766): SSD `results.csv` has a 46-field header
   over 35 rows of 49 fields; the branch adds 7 more. Resuming an old out dir with a newer runner loses the new columns in
   `load_rows`/`backfill` (DB gets them only from the live row). Start a fresh out dir per runner version or migrate the header.
9. **`mode_size_mb` KeyError** for any 16-bit mode whose height is not 2160/1080 (92): adding a 3840x2072/2076 HDR16 crop to `MODES`
   crashes `--dry-run` and `all_configs`. Raw height for Clear HDR 16-bit crops is a driver fact (the 2160 mode uses 2200 rows).
10. **`setup_mismatch` stops the campaign** on any read-back difference (856-860, 1138-1140), including `fps` off by > 0.01 (449) and a
    refused crop resolution - correct for an unattended run, but it means a human must be reachable; there is no notification path.
11. **Take id without a date** (848): two takes of one config and fps at the same HH:MM:SS on different days collide on the DB primary
    key (`db_ingest` deletes the earlier take's rows, 649-650). Unlikely over one campaign, not impossible over days.
12. **Trim handling:** `set_media_trim` is a per-config factor; the `finally` forces trim ON (1442) regardless of the original setting;
    `written['gb']` (1019) is reset whenever trim is on and >1 GB was written, so the "since trim" counter is only meaningful for trim-off
    configs.
13. **Core settings left changed at the end:** Log "stays as last set" (1452); `fps_speed_ramp` restored from the session (1445);
    audio format restored only if the runner changed it (1449-1451). Fine, but worth telling the owner.
14. **Hard-coded paths/hosts:** `SOCK`, `MEDIA`, `TUNE_CLI = ~/ApertarCore/scripts/apertar-tune` (810), `/usr/local/libexec/apertar-media-tune`
    (839), `~/ApertarCore` for the Core commit (1086), port 8000 (488, 514, 877), `KT['dev'] = '/dev/sda1'` (809, overridden by `findmnt`),
    Mac side `apertar.local` / ssh alias `apertar` / a Mac log directory (`webui_remote.py` 13-18). No serial numbers are hard-coded;
    the drive is identified from the mount only.
15. **The 2K modes and the 8-mode `make_results_xlsx.py`:** the workbook's `MODES` (17-19) omits `4kHDR16` and hard-codes two
    "not run" explanation rows for the SSD (144-150): it will need the three NVMe modes and those rows removed.
