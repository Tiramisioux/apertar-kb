# DNG chain comparison (cinemate/cinepi-raw vs Apertar drop-frames): research in progress

Started 2026-11-01 in a cloud session (Claude Code) at the operator's request: compare the two DNG write chains, find
improvements for Apertar on exFAT / SSD (writing and mounting), explain the residual drops at 4K Clear HDR 16-bit 25 fps
(also with Log) and 4K 50 fps SDR, say whether the drop-frames changes made recording better, and whether the storage
pre-roll has an effect. Sources: Apertar-Core `drop-frames` 92d0970, Apertar-UI `drop-frames` e061be8, cinemate `main`
4990afc (full history), cinepi-raw `main` 63a08d5, cinemate-handbook c99ff77, this KB at 1899e8d, Linux v6.12 source.

Method: nine reader reports (R1..R9, assignments in `assignments/`, rules in `BRIEF.md`), then three syntheses from
different lenses, a merge, adversarial verification of every hypothesis (code, evidence, mechanism), a completeness critic.
The answer page will be `working/dng-chain-answer.md`.

## State (updated as reports land)

| Report | Topic | State |
| --- | --- | --- |
| R1 | cinepi-raw DNG write chain and history | done |
| R2 | cinemate storage, mounting, kernel tuning, scheduling, pre-roll, docs, history | done |
| R3 | Apertar-Core write chain on drop-frames and history | running |
| R4 | Mounting: Apertar-UI automounter vs cinemate's, exFAT specifics | done |
| R5 | Evidence pass over the kb and the handbook | done |
| R6 | Domain: Linux exFAT internals, NVMe HMB, trim, bandwidth, writeback, libcamera | running |
| R7 | Apertar-Core capture side: completion thread, requeue, capture gaps, previews, pre-roll | running |
| R8 | Apertar-Core encoder path and data-rate model per case | done |
| R9 | What each stack asks libcamera for; the ISP back-end serial cycle; link utilisation | running |

## Findings already firm enough to act on (each has its refs in the report named)

1. The 4K 50 fps SDR take (T34 M3, 2026-10-28) wrote 525 MB/s with the write queue never above 3/12 and lost ~12 % of
   frames as steady single-frame capture gaps: the loss is upstream of Core's writers (libcamera's serial per-frame
   cycle), so no writer-side change (Log, ram buffer, trim, sync policy, mount options) can touch it (R5, R8).
2. Clear HDR 16-bit + Log at 311 MB/s is well inside the drive envelope; Clear HDR 16-bit linear (415 MB/s) ran 10 min
   clean on a trimmed drive (A0, A1). The residual drops in this case are capture-side and short-take (R5, R8).
3. The kb's A1-vs-A2 conclusion ("the per-frame writeback hint keeps the CFE from stalling") does not hold as a mechanism:
   `CdngEncoder.cpp:1780` calls `posix_fadvise(POSIX_FADV_DONTNEED)` after every DNG, and in Linux 6.12 that call itself
   starts asynchronous writeback (`mm/fadvise.c`: `__filemap_fdatawrite_range(WB_SYNC_NONE)`), then `lru_add_drain_all()`
   on every CPU when the dirty pages cannot be invalidated. A2 differed from A1 by one redundant syscall; its 10 % loss is one
   unexplained run (orchestrator + R5).
4. cinemate has no counted take of either operator case. Its only quantified clean 4K 16-bit 25 fps record is eight ~10 s
   takes WITH Log 12 (medium unstated); its only multi-minute 16-bit soak stalled (NTFS/FUSE); cinepi-raw itself dropped
   frames at 4K 16-bit until a preview fix in Sept 2026; nothing at 4K 50 fps exists (R1, R2, R5).
5. cinepi-raw requests 16-bit containers even for SDR (2 B/px on the link, twice Core's COMP1 bytes); Core's writer makes a
   second full copy of each 16-bit frame (row memcpy into a scratch, 491,520-byte write() chunks, ~37 syscalls/frame) where
   cinepi-raw packs once and writes once (R1, R8).
6. Both stacks format exFAT with mkfs.exfat's default 128 KiB clusters (cinemate tried 1 MiB and reverted for macOS); neither
   trims or mounts with discard except Core's new fstrim helper; the Linux exfat driver issues one discard per freed cluster under
   `-o discard` (R2, orchestrator).
7. exFAT writers on Apertar are 4 (MediaProfile {4,12,0} since 0358fcf), not 2 (R8).
8. The WebUI's MJPEG downsample runs on libcamera's completion thread when a browser is attached (ApertarCoreApp.cpp ~9355) (R5).

## How to resume if this session ends

Read `BRIEF.md`, the finished reports, then run the missing readers from `assignments/`, three syntheses, a merge, verification
and the critic as described above; write `working/dng-chain-answer.md` in the kb's answer-page format (see
`working/storage-answer.md`, `working/research-30fps-answer.md`).

### Added with R4 (mounting)
9. The live `/media/RAW` mount comes from the Apertar-UI CFE automounter (`mount(2)` with `uid=1000,gid=1000,umask=0002` + `MS_NOATIME`);
   `noatime` is on the mount. Three other Apertar mount paths (touch-UI Mount button, the Python re-insert watchers in Core and UI) lack
   `noatime`. Mount options are not a plausible cause of the residual drops (R4).
10. Touch-UI clip deletes bypass Core (`cliplistmodel.cpp` removes files directly), so Core's trim-after-delete never fires for them:
    the 0.9 TB stall can come back in a record/delete session driven from the touch UI (R4, lead L1).
11. A `discard` mount is not a substitute for the fstrim helper: the 6.12 exfat driver issues one synchronous discard per freed 128 KB
    cluster under `bitmap_lock` (~1.9 million for a 15000-frame clip) (R4).
