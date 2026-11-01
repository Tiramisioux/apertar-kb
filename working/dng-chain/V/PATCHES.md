# Review of the seven commits on claude/adoring-euler-n8zi0j-work (base 92d0970)

Worktree: /home/user/Apertar-Core-work. Order (oldest first): e55557d, 4abbef0, 04bac89, e0fa852, c57c284, 0ed07ea, fb557e9.
Line numbers below are against HEAD (fb557e9) unless a commit is named. Nothing was modified.

## Host checks (run by the reviewer)

| Check | Result |
| --- | --- |
| `TZ=UTC sh tools/dng_payload_write_test.sh` | PASS. Six layouts byte-identical across direct / forced-copy / `APERTAR_DNG_WRITE_ROWS=512`. strace: direct path 42 `write` + 4 `writev` for the 6 files (1 write per contiguous 16-bit/8-bit frame; padded 2160-row frame = 3 writev of 1024/1024/112 rows, 70-row frame = 1 writev); copy path 117 `write`. Log: research/V/payload-test.log |
| `cc-check.sh` (CameraController.cpp, libcamera block on) | errors now 25, baseline 25, "no new errors". Log: research/V/cc-check.log |
| `g++ -std=c++20 -fsyntax-only -Iinclude -Isrc src/ApertarCoreApp.cpp` | exit 0, no output |
| `bash -n scripts/start-apertar-core.sh` + dry run (exec replaced by echo) | default: `exec <bin> --socket .. --media ..` (identical to before). `APERTAR_RT=1`: prefix `chrt -f 70 ionice -c2 -n0 taskset -c 1-3`. `APERTAR_RT_CPUS=` (empty): no taskset. `APERTAR_RT_CPUS=2 APERTAR_RT_PRIORITY=50`: `chrt -f 50 ionice -c2 -n0 taskset -c 2`. bash 5.2 on the host; the `${A[@]+"${A[@]}"}` idiom also passes under `set -u` on bash 4.3 semantics. |

## Summary table

| Commit | Title (short) | Verdict | One line |
| --- | --- | --- | --- |
| e55557d | cdng: direct write of 16/8-bit payloads | ok | writevAll and iovec adjust correct; byte-identical; compiles for aarch64 GCC 12 |
| 4abbef0 | rec: allocate outside mutex_, warm pool, keep through take | ok | no double lock, no mutex_/copyMutex_ nesting, overflow guarded, ram mode bounded by budget |
| 04bac89 | media: free-space trim (+ carries the noatime hunk) | fix needed (history only) | code correct; the commit holds the noatime/umask hunk that e0fa852's message describes, and lacks the pre-roll hunk its own message claims |
| e0fa852 | media: noatime (actually: pre-roll trim hunk) | fix needed (history only) | code correct; the diff is the pre-roll `trimMedia("delete")` change, not the mount options |
| c57c284 | scripts: APERTAR_RT=1 | ok | bash paths verified; default exec unchanged; opt-in |
| 0ed07ea | cdng, rec: APERTAR_DNG_DONTNEED; stats field | fix needed (trivial) | the old standalone `dropped_copy_slot=` line (CameraController.cpp:4298-4299) now duplicates the new field |
| fb557e9 | web: APERTAR_WEB_PREVIEW_RECORDING_FPS | fix needed (trivial) | `strtod` accepts `nan` and denormals: NaN or 1e306 reaches `static_cast<int64_t>` (UB); default path unchanged |

No correctness bug was found in the C++ or the bash. Behaviour at default knob values changes only where intended: the direct write path (e55557d), the pool policy (4abbef0), the trim coverage (04bac89, e0fa852), the mount option strings (04bac89), plus one new field on the stats line (0ed07ea) and one atomic load per preview frame (fb557e9).

---

## e55557d — cdng: write unpacked 16-bit and 8-bit payloads straight from the frame, in one write()

Verdict: **ok**

Files: src/cdng/CdngEncoder.cpp (+108), tools/dng_payload_write_test.cpp (new), tools/dng_payload_write_test.sh (new).

What was read: `rowCopyIsIdentity` (CdngEncoder.cpp:1082-1092), `writevAll` (:1094-1120), `writeRowsDirect` (:1123-1142), `writeDngRowBytes` (:1143-1184), `writeRawPayload` (:1983-2041), `unpackedBytesPerSampleForFrame` (:155-160), `writeAll` (:517-538), the three `prepare*Layout` functions (:1927-1981), `takePayloadScratch` (:1318-1323), `RawFrameView` (include/apertar/core/Types.hpp:256-271), the test tool and script.

Findings (confirmed unless marked):

1. Identity test matches the old row pass exactly. `writeDngRowBytes` memcpy's `layout.rowBytes` for `Bits16` not Csi2Packed/PispCompressed1 (:1164-1165) and for `Bits8` with `unpackedBytesPerSampleForFrame == 1` (:1166-1169). `rowCopyIsIdentity` (:1082-1092) returns true for exactly those two cases. The layout for both is `Unpacked` with `rowBytes = width*2` (`prepareUnpackedLayout` :1976-1978) or `packedRowBytes(width, Bits8) = width`. The 12-bit Log case (view bitDepth rewritten to `targetBits` = 12 in copyLoop, CameraController.cpp:4883) still goes through `packDng12Row`, so the README's "CineMate Log frames keep the scratch path" is right.
2. `writevAll` (:1094-1120) partial-write handling is correct: EINTR retried; 0 → EIO; consumed iovecs skipped with `remaining >= iov->iov_len`; the partially written iovec gets `iov_base += remaining; iov_len -= remaining`. `remaining` cannot exceed the sum of the iovecs, and `iov_len` is never 0 (rowBytes > 0, checked at :1985). The caller refills `iov[]` for every chunk (:1131-1134), so in-place modification is safe.
3. `writeRowsDirect` (:1123-1142): contiguous case writes `rowBytes * height` bytes from `frame.data` — the same bytes the old path copied row by row when `stride == rowBytes`. Padded case: one iovec per row, `min(IOV_MAX, 1024)` rows per call; the loop `y += rows` covers every row (2160 = 1024+1024+112, matched by strace).
4. Scratch chunk cap raised from 4 MiB to 64 MiB (:1997). At the default 64 rows the chunk is `rowBytes*64` (491,520 B at 4K 16-bit, 368,640 B at 4K 12-bit packed), far below 4 MiB, so the default is unchanged; the cap only matters with `APERTAR_DNG_WRITE_ROWS` up to 4096 (max 31 MB scratch per writer at 4K 16-bit — intended for the A/B).
5. ENV parsing: `configuredPayloadWriteRows` (:84-99) uses `strtoul` with errno/end checks and a 1..4096 range → falls back to 64 on anything odd. `payloadCopyForced` (:103-111) treats any value except `0|false|off` as on (differs from `boolEnvValue`, which also knows `no`); harmless for an A/B knob.
6. aarch64 / GCC 12: `IOV_MAX` comes from `<limits.h>` (included :27) under `_GNU_SOURCE`, which g++ defines on Linux — same on the Pi's toolchain; `<sys/uio.h>` (:29) declares `writev`/`struct iovec`; `std::min<long>(IOV_MAX, 1024)` is well-typed. No libcamera code touched. Compiles on the host with the same flags.
7. Not a regression but worth knowing: neither path checks `frame.size` against `stride*height`; both read `frame.data + y*stride` for `rowBytes`. Same exposure as before.
8. Pre-existing, not from this commit: `takePayloadScratch` (:1318-1323) does `clear()` then `resize(size)` per frame, which zero-fills the scratch (491 KB) every DNG on the scratch path. The direct path no longer touches the scratch at all.
9. The test tool is not referenced by CMakeLists.txt (grep empty): host-only, builds with `-lyaml`; the Pi build is unaffected.

Behaviour at defaults: 16-bit (Clear HDR) and 1-byte 8-bit payloads are written in one `write()` (or ≤3 `writev()` with a padded stride) from the pooled copy; one full memcpy per frame removed. Everything else unchanged.

---

## 4abbef0 — rec: allocate raw copies outside the queue mutex, warm the pool at take start, keep it through the take

Verdict: **ok**

File: src/camera/CameraController.cpp (+90/-20) inside `DngRecordingQueue`.

What was read: `startAtFolder` (CameraController.cpp:4056-4211), `stop` (:4232-4330), `hasCapacityForFrame` (:4584-4617), `enqueue` (:4729-4790), `acquireRawBuffer` (:4637-4663), `rawPoolWarmEnabled`/`warmRawPool`/`trimRawPoolToIdle`/`clearRawPool` (:4668-4727), `copyLoop` (:4846-4905), `releaseHeldRequest`/`stopCopyWorkers` (:4907-4940), both worker recycle sites (:5075, :5174), `failRecording` (:5181-5200), `recycleRawBuffer` (:5204-5225), `planQueueBuffer` (:5253-5302), `idleRawPoolSize`/`preferredRawPoolSize` (:5305-5317), the member block (:5340-5395), `boolEnvValue` (:1266-1286), the caller `startRecording` (:7270-7405: `setFrameBytesHint` :7400, `startAtFolder` :7405), `clearRawPool` caller (:8273, on reconfigure), the completion handler `requestComplete` (:8661-8700, takes `sessionSettingsMutex_` shared only) and `recordRawFrame`'s `rawSize` (:8974-8983, `copy.size = rawSize` :9039).

Findings:

1. Lock discipline. `acquireRawBuffer` (:4637-4663): the pool lookup is in a `{ lock_guard }` block; the miss allocates after the block → the 16.6 MB zero-fill no longer runs under `mutex_`. `warmRawPool` (:4676-4705): two separate lock scopes, allocation between them. `trimRawPoolToIdle` (:4708-4716) one lock. No function takes `mutex_` twice; `startAtFolder` calls `warmRawPool` with no lock held (:4153); `stop` calls `trimRawPoolToIdle` after the writers are joined and the copy threads stopped (:4293), with no lock held.
2. `mutex_` vs `copyMutex_`: `copyLoop` releases `copyMutex_` before `acquireRawBuffer`, `recycleRawBuffer` and `enqueue` (:4852-4860 scope ends before :4863); `enqueueCopy` (completion thread) takes `copyMutex_` after `hasCapacityForFrame` has released `mutex_` (:9032 then :9034+). `stop`: `stopCopyWorkers` (copyMutex_) and the `stopping_` block (mutex_) are sequential. No nesting in either order → no deadlock.
3. size_t overflow: `preferredRawPoolSize` returns `SIZE_MAX` in ram mode (:5314-5315); `recycleRawBuffer` guards `maxRetainedBuffers <= 4096u` before `expectedSize * maxRetainedBuffers` (:5213), so `maxRetainedBytes = 0` and the byte cap is skipped. In frames mode the count is ≤ 64+8+2 = 74 → no overflow.
4. Memory in ram mode: the pool is bounded by `queuedBytes_ + pooledRawBytes_ + capacity > queueBudgetBytes_` (:5219), i.e. queue + pool ≤ the budget computed from MemAvailable at take start (:5290-5298). Total copies in existence ≤ budget + workers + copy threads, the same peak as before; the difference is that the peak is now held until `stop()` instead of being returned as the queue drains. Within plan; no unbounded growth.
5. Memory in frames mode: pool cap while active = `maxQueuedFrames_ + workerCount_ + 2` (:5315). exFAT profile (2 writers, 12 frames): 16 × 16.6 MB = 265 MB held through the take at 4K 16-bit; idle pool afterwards `min(12, max(2+2,4)) = 4` → 66 MB (ext4, 4 writers: 6 → 100 MB). With `APERTAR_CDNG_QUEUE_FRAMES=64` and 8 workers the cap is 74 × 16.6 = 1.2 GB, but the queue alone could already hold 64.
6. The dropped-buffer free in `recycleRawBuffer` (`return;` at :5220) happens **after** the `lock_guard` is destroyed: `buffer` is a by-value parameter, destroyed after the body's locals. So the munmap of a rejected 16.6 MB vector is also outside `mutex_`. `trimRawPoolToIdle`/`clearRawPool` free under the lock, but only at stop/reconfigure.
7. The pool is never trimmed while a writer needs a vector: `trimRawPoolToIdle` only pops pooled (idle) vectors; vectors in `queue_`, in a worker's `FrameJob` or in the copy worker are not in `rawPool_`. Detached writers after a dead-medium stop (`joinAll == false`, :4280-4287) recycle later into an idle-capped pool — bounded.
8. Warm buffers are usable: `frameBytesHint_ = activeRawFrameBytes(stride, height)` (:7400) and `copy.size = rawSize = min(candidate - offset, activeFrameSize)` (:8980-8982) → `rawSize ≤ hint`, so every warm buffer has `capacity ≥ size`. If `rawSize < hint`, `expectedRawBufferSize_` becomes `rawSize` on the first acquire and a warm buffer is kept on recycle as long as `hint ≤ 1.5 × rawSize` (:5214, :5217) — true for the normal case `rawSize == hint`.
9. Where the warm runs: `startAtFolder` is called from `startRecording` on the command path under the controller lock (:7398 comment "this runs under the controller lock"). The completion thread does not take the controller `mutex_` (`requestComplete` :8661-8700 takes `sessionSettingsMutex_` shared; the only exclusive lock on that mutex is at :7246, outside `startRecording`), so the ~66-100 MB zero-fill (tens of ms on the Pi 5) delays the take start, not the frames. Threads that do take the controller mutex (`isRecording()` :12076, HTTP status) wait that long once per first-take-after-configure.
10. `active_` and the gauge flag are set true only after `warmRawPool`, the sync thread and the writers are up (:4187-4188), so `preferredRawPoolSize` reads the idle count during warm and the active count during the take; `stop()` sets `active_` false first (:4242), so the trim at :4293 uses the idle count. `preferredRawPoolSize` reads `ramMode_` (mutex_-guarded) only from `recycleRawBuffer`, which holds `mutex_`.
11. Minor: `trimRawPoolToIdle` pops from the back without regard to fit. Since `clearRawPool` runs on every reconfigure (:8273), pooled vectors have one size, so this cannot keep an undersized vector and drop a fitting one in practice.
12. `rawPoolWarmEnabled()` → `boolEnvValue("APERTAR_RAW_POOL_WARM", true)` (:1266-1286 accepts 1/true/yes/on, 0/false/no/off). `=0` restores exactly the old rule (idle count always; no warm).
13. Compiles: `<limits>` (:58) for `std::numeric_limits`, `<algorithm>` (:36) for `std::min_element`; `boolEnvValue` is defined before the class. cc-check: no new errors.

Behaviour at defaults (intended): first take after a (re)configure allocates the idle pool before the writers start; copies are retained through the take; the pool shrinks to the idle count at stop. A/B: `APERTAR_RAW_POOL_WARM=0`.

---

## 04bac89 — media: trim after a delete made outside Core, and after every pre-roll clip delete

Verdict: **fix needed** (history/commit message; the code is correct)

File: src/ApertarCoreApp.cpp (+10/-3). The diff holds two hunks: (a) the embedded Python watcher's `mount_partition` option strings (ApertarCoreApp.cpp:3884, :3886, :3888 — `uid=1000,gid=1000,umask=0002,noatime` for ntfs3 and exfat, `noatime` for ext4), (b) the free-space trim in `runMediaWatcher` (:10488-10495). It does **not** contain the pre-roll `trimMedia("delete")` change its message announces ("and after every pre-roll clip delete"); that hunk is in e0fa852. The noatime hunk here is what e0fa852's message describes.

Fix (history): swap the hunks or amend the two messages. Minimal: `git rebase -i 4abbef0` and reword 04bac89 to "media: trim after a delete made outside Core; noatime and umask on the re-insert mount" and e0fa852 to "media: trim after every pre-roll clip delete". Or `git rebase -i` with edit on both and move the hunks so each matches its message.

Code findings:

1. Trigger (:10492-10495): `havePrevious && current.mounted() && previous.mounted() && current.sameMedium(previous) && current.freeBytes > previous.freeBytes && delta >= 1 GiB && !camera_.isRecording() && !mediaDeleteActive_.load()`. `freeBytes` is `uint64_t` (src/util/MediaProbe.hpp:47); the `>` guard precedes the subtraction → no underflow. `previous = current` is assigned every cycle (:10558-10559), so a jump fires once.
2. During a format: the medium is unmounted while mkfs runs, so `current.mounted()` is false; on remount `previous.mounted()` is false for the first mounted poll; later polls see no jump → the free-space trim does not fire for a format (the existing "mount" trim covers it). Probable: relies on the format path unmounting, which the watcher's `storagePrerollFormatRunning_` handling (:10547-10549) implies.
3. During a pre-roll: the take lowers free space (no trigger); after its delete (0.7-1.4 GB) a jump ≥ 1 GiB can fire "free-space" in addition to the pre-roll's own `trimMedia("delete")` (:10900). Both set `mediaTrimPending_` (:11035-11036) and coalesce **unless** the first trim is already in its FITRIM (`mediaTrimPending_` is cleared before the run, :11076), in which case the worker runs a second trim right after. On exFAT every FITRIM re-discards all free space (no "already trimmed" tracking as ext4 has), measured 0.47 s for 927 GB → at worst about one extra half-second of discard traffic. Minor; see e0fa852.
4. The trim worker is idle-only: `mediaTrimMayRun` (:11050-11060) checks `isRecording`, sound, timelapse, pending writes, delete, `prerollActive`, standby, speed test. The idle check is made once before the ioctl (:11093-11105); a take started during the ≤0.5 s FITRIM overlaps it. Pre-existing for every trim reason, not new here.
5. `camera_.isRecording()` takes the controller mutex (CameraController.cpp:12076-12080), but the `&&` chain evaluates it only when a ≥1 GiB jump was observed on the same mounted medium, i.e. rarely; the watcher's "holds no lock anyone waits for" property (:10443-10444) still holds (it takes, not holds). If the command path is inside a long stop drain at that moment the watcher waits for it — once.
6. Limitation (not a bug): deletes made one by one from the touch UI, each < 1 GiB (4K lossless clips are ~0.7 GB), never cross the per-poll threshold; a running total since the last trim would. Same semantics as Core's own `trimMediaAfterDelete` (:11042-11049) which measures per batch.
7. noatime/umask hunk: the strings equal Core's own mount path (:3958, :3960 `uid=1000,gid=1000,umask=0002,noatime`). `ntfs3` and `exfat` accept `umask` and `noatime`; `ext4 -o noatime` is standard. Only the option strings changed in the Python text.

Behaviour at defaults (intended): a ≥1 GiB free-space rise between two polls on an idle, mounted medium requests a trim (reason "free-space"); re-insert mounts get noatime/umask.

---

## e0fa852 — media: noatime and umask on the re-insert mount of a CFexpress card

Verdict: **fix needed** (history/commit message; the code is correct)

File: src/ApertarCoreApp.cpp (+3/-2). The diff is the pre-roll completion in `runStoragePrerollOnce` (ApertarCoreApp.cpp:10896-10900): `if (result.bytes >= (1ULL << 30)) trimMedia("delete");` → unconditional `trimMedia("delete");`. It contains no mount option change. The message belongs to the hunk in 04bac89 (see above). Fix: reword/swap as described under 04bac89.

Code findings:

1. `result` is still used (`result.bytes` in `logLine`, :10886-10893), so no unused-variable warning from dropping the `if`.
2. The pre-roll runs on its own thread; its take runs under `commandMutex_` only for the start (:10842-10863); the completion (:10883-10900) holds no lock; `trimMedia` only sets a flag under `mediaTrimMutex_` and notifies (:11022-11038). Safe.
3. Behaviour change at default: before, a 2 s pre-roll at 4K 16-bit 25 fps deletes 50 × 16.6 MB ≈ 830 MB < 1 GiB → no trim; at 4K 12-bit 60 fps ≈ 1.4 GB → trim. Now every pre-roll ends with a FITRIM request. At mount the sequence is: trim("mount") → pre-roll waits for it (`waitForMediaTrim`, :10858) → 2 s take → delete → trim("delete") (→ possibly a coalesced "free-space"). On exFAT each FITRIM discards all free space again (probable: fs/exfat/balloc.c `exfat_trim_fs` walks the bitmap with no trimmed-group tracking), so a freshly trimmed 1 TB drive takes about two to three full discards per mount, ~0.5 s each per the measured number in the comment. The last one lands right before the operator's first take, on the idle worker; if the take starts within that half second it overlaps the ioctl (same window as every other trim).
4. Suggested refinement (optional, for the A/B rather than a bug): skip the post-pre-roll trim when `mediaTrimLastUnix_` is within, say, 60 s and the last result was ok, or keep the 1 GiB threshold but seed it with the pre-roll's measured bytes — whichever the pre-roll measurements favour. The commit's own "Not run on the Pi" applies.

---

## c57c284 — scripts: APERTAR_RT=1 runs Core under SCHED_FIFO on cores 1-3 like cinepi-raw; README knob table

Verdict: **ok**

Files: scripts/start-apertar-core.sh (+24/-1), config/apertar-core-capture-priority.conf (+3), README.md (+15/-1).

Findings (bash, under `set -euo pipefail`, verified by dry run — see the host-check table):

1. `PREFIX=()` + `exec ${PREFIX[@]+"${PREFIX[@]}"} "$CORE_BIN" ...` (script:43): the parameter-expansion idiom expands to nothing when the array is empty and to the quoted elements otherwise; safe under `set -u` on bash ≥ 4.3 and on 5.x (Pi OS Bookworm ships 5.2). Default path produces exactly the old `exec "$CORE_BIN" --socket ... --media ...`.
2. `RT_CPUS="${APERTAR_RT_CPUS-1-3}"` (script:28): the `${VAR-word}` form — unset → `1-3`, set-but-empty → empty, which `[[ -n "$RT_CPUS" ]]` (script:34) turns into "no taskset" as the comment and README say. Verified both cases. `set -u` does not trip on `${VAR-word}`.
3. `if command -v chrt ... && chrt -f "$RT_PRIORITY" /bin/true 2>/dev/null` (script:29): both commands are the `if` condition, so `set -e` does not exit on refusal; the else branch logs and falls through to the plain exec. `/bin/true` exists on Pi OS (merged /usr). A non-numeric `APERTAR_RT_PRIORITY` makes `chrt` fail → same fallback.
4. `echo ... "${PREFIX[*]}"` (script:37) runs only when the array is non-empty. No pipes, so `pipefail` is moot.
5. Drop-in: `LimitRTPRIO=80` added next to `LimitNICE=-5`. Unused unless `APERTAR_RT=1`; nothing installs the drop-in (as the message says), so a default install is unchanged.
6. Semantics to keep in mind for the A/B (not a defect): `chrt -f 70` applies to **every** thread Core spawns (libcamera's, the copy worker, the DNG writers, the sync thread, the HTTP server, the embedded Python watcher, encoders), inherited through `ionice`/`taskset`; cinepi-raw is launched the same way but has far fewer threads. Pinning all of them to cores 1-3 leaves core 0 for everything else; with lossless (CPU-bound) workers at FIFO 70 the kernel's own threads and the UI on cores 1-3 can starve. That is the intended parity test, off by default.
7. README table (README.md:281-294): rows match the code defaults (`APERTAR_DNG_WRITE_ROWS` 64, `APERTAR_RAW_POOL_WARM` on, `APERTAR_RT` off, cores 1 to 3, priority 70). The trim sentence (README.md:271) now describes both new trim triggers.

---

## 0ed07ea — cdng, rec: APERTAR_DNG_DONTNEED chooses when a DNG's pages leave the page cache; dropped_copy_slot in the stats line

Verdict: **fix needed** (trivial)

Files: src/cdng/CdngEncoder.hpp (+7), src/cdng/CdngEncoder.cpp (+23/-1), src/camera/CameraController.cpp (+12), README.md (+1).

Findings:

1. Fix: the old standalone line is still there. `stop()` prints `"ApertarCore recording stats: dropped_copy_slot=" << dropped` when `dropped > 0` (CameraController.cpp:4298-4299) **and** the new field `dropped_copy_slot=` in the main stats line (:4319). A take with copy-slot drops now logs the number twice. Remove :4298-4299:
   ```cpp
   -        if (const uint64_t dropped = droppedNoRequestSlot_.load(std::memory_order_relaxed); dropped > 0)
   -            std::cerr << "ApertarCore recording stats: dropped_copy_slot=" << dropped << "\n";
   ```
   (Keep the field in the main line; that is what the message wants. Any kb script grepping the old line should switch to the field.)
2. Knob coverage: `dngPageCacheDrop()` gates the call in `CdngEncoder::writeDngFile` (CdngEncoder.cpp:1900-1901) and adds the sync-thread call (CameraController.cpp:4553-4556). `LossyDngEncoder.cpp:101` still calls `POSIX_FADV_DONTNEED` unconditionally, so the README row "When a written DNG's pages leave the page cache" is true for cDNG (uncompressed and lossless) only. Either route Lossy DNG through `dngPageCacheDrop()` or say "cDNG" in the README row. Not relevant to the operator's cases (uncompressed cDNG), so a doc nit.
3. Parsing (CdngEncoder.cpp:84-98): empty/`writer`/`1` → Writer; `sync` → Sync; `off`/`0`/`false` → Off; anything else logs once and uses Writer. `true`/`on` are not accepted (they warn and fall back to Writer, the same thing). Fine.
4. Placement of `dngPageCacheDrop()`: defined between `} // namespace` and `namespace {` (:82-100) → in `namespace apertar`, matching the header declaration (CdngEncoder.hpp:17-18). `<iostream>` added for the warning (:20). Compiles (payload test built this file; cc-check unchanged).
5. Sync mode mechanics (CameraController.cpp:4549-4557): fd is `O_RDONLY`; `posix_fadvise` does not need write access. After `fsync` the pages are clean and not under writeback, so the invalidate succeeds without the `lru_add_drain_all` fallback for pages already on the LRU; pages still sitting in a per-CPU folio batch can still trigger one drain per call (probable, kernel behaviour; the bpftrace count the message proposes settles it). For MLV the sync tick pushes `mlvPathString_` every second (:4545-4546), so in sync mode the growing MLV's clean pages are dropped once a second — harmless.
6. Warning when sync mode is chosen without the sync thread (:4168-4174): `static bool warned` → logged once per process. Default `writer` unchanged.
7. Default behaviour: unchanged except the new stats field.

---

## fb557e9 — web: APERTAR_WEB_PREVIEW_RECORDING_FPS caps or pauses the web preview while a raw take runs

Verdict: **fix needed** (trivial; default path unaffected)

Files: src/ApertarCoreApp.cpp (+24/-2), src/camera/CameraController.cpp (+5), src/camera/CameraController.hpp (+2), README.md (+1).

Findings:

1. Fix: `webPreviewRecordingFps()` (ApertarCoreApp.cpp:86-99) rejects `parsed < 0.0 || parsed > kWebPreviewMaxFps`, which lets **NaN** through (`strtod("nan")` → both comparisons false) and accepts denormal positives. In `captureWebPreviewFrame` (:9376-9380) `maxFps = NaN` passes `maxFps <= 0.0` and `static_cast<int64_t>(1'000'000.0 / maxFps)` is UB (NaN → int64); `=1e-300` gives 1e306 → int64 overflow, also UB (aarch64 saturates to INT64_MAX in practice, x86 gives INT64_MIN → the preview would run at full rate). Fix at :94:
   ```cpp
   -        if (end == text || *end != '\0' || parsed < 0.0 || parsed > kWebPreviewMaxFps)
   +        if (end == text || *end != '\0' || !std::isfinite(parsed) || parsed < 0.0 || parsed > kWebPreviewMaxFps)
                return kWebPreviewMaxFps;
   +        if (parsed > 0.0 && parsed < 0.5)
   +            return 0.0;   // slower than one frame every two seconds: treat as paused
   ```
   (`<cmath>` for `std::isfinite`.) Only values nobody would type; the README documents `N` and `0`.
2. Thread safety of `rawTakeActive()` on the completion thread (CameraController.cpp:11981-11984): returns `frameBufferGauge().active.load(acquire)`; the gauge is a function-local static (thread-safe init, :4014-4018) and `active` is `std::atomic<bool>` (:4010). No lock, no controller state. The flag is set true at the end of `startAtFolder` (:4188) and false at the start of `stop()` (:4243) and in `failRecording` (:5191), so "a raw take runs" is exactly the window in which `hasCapacityForFrame` accepts frames. It is also true during the storage pre-roll's take (same queue), which caps the preview then too — desirable.
3. Gating position (:9376-9380): before `mjpegMutex_` and before `lastWebPreviewCaptureAt_` is updated, so with `=0` nothing is touched and the preview resumes on the first frame after the take; with `=N` the existing interval check does the limiting. With `=0` the browser's MJPEG stream simply stalls for the take (no error path); matches "pauses".
4. Default: `kWebPreviewMaxFps` (30) when the variable is unset/empty → identical interval to before; the only added cost is one atomic load per preview frame.
5. Cosmetic: the new function was inserted between the comment that documents `frameBufferStatus` ("Called about 5 times a second ... read under try_lock", CameraController.cpp:11978-11980) and `frameBufferStatus` itself (:11986), so the comment now reads as if it described `rawTakeActive`. Move the comment below the new function.
6. `webPreviewRecordingFps` is a function-local `static const` → `getenv` runs once, on whichever thread first shows the preview (the completion thread). Fine.
7. Compiles: ApertarCoreApp.cpp syntax-checks; CameraController.cpp cc-check unchanged. `rawTakeActive` touches no libcamera type.

---

## Cross-cutting

- Behaviour at defaults, complete list: direct write path for unpacked 16-bit/8-bit payloads (e55557d); pool warmed at take start and retained through the take (4abbef0); trim on a ≥1 GiB free-space rise and after every pre-roll (04bac89/e0fa852); noatime/umask on the watcher's re-insert mount (04bac89); `dropped_copy_slot=` field on the stats line (0ed07ea); one atomic load per web-preview frame (fb557e9). Nothing else changes without a knob.
- aarch64 / GCC 12 / libcamera: no new libcamera API use; headers used (`<sys/uio.h>`, `<limits.h>` for IOV_MAX under `_GNU_SOURCE`, `<limits>`, `<algorithm>`, `<iostream>`) are present; cc-check against the libcamera headers shows the same 25 fork-versus-upstream errors as the baseline. Nothing found that would compile on x86 but not on the Pi.
- Things the Pi must still answer (the commits say so themselves): perf page-faults on the copy thread (4abbef0), the A0 vs `APERTAR_DNG_DONTNEED=sync` vs `off` 10-minute runs (0ed07ea), the WebUI-open two-take test (fb557e9), the trim journal line after a touch-UI delete (04bac89), and whether the extra post-pre-roll FITRIM is neutral for the first take (e0fa852).
