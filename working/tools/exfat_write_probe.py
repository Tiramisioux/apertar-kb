#!/usr/bin/env python3
"""exfat_write_probe.py: Core's DNG write pattern without the camera, with the levers as switches.

Writes files of --size-mb into ONE new folder under --root (default /media/RAW) the way Core's writers do (several
threads, 480 KiB write() chunks per file, a sync thread that every second fsyncs the files finished since the last tick
and then the folder), and times every file. Switches turn the candidate levers on and off so each one is measured on
its own, in minutes, with no sensor or ISP in the loop:

  --workers N          concurrent writers (Core: 4)             --chunk-kb K      write() size per call (Core: 480; 0 = one write per file, cinepi-raw)
  --fsync tick|none    Core's once-a-second fsync pass, or none  --sync-ms M       the pass interval (Core: 1000)
  --prealloc           ftruncate the file to its final size right after open (one cluster allocation per file)
  --direct             O_DIRECT (page-aligned buffer, length padded to 4 KiB, ftruncate to the exact size at the end)
  --subdir K           a new sub-folder every K files (the clip-split idea)
  --fps F              pace the files like a take at F fps (0 = as fast as the drive takes them)
  --budget-mb B        with --fps: stop as "buffer full" when the writers are B MB behind the schedule (Core's RAM buffer)
  --seconds S / --files N   length of the run

Output: every 1000 files (or every 10 s) a line with files/s, MB/s, the per-file wall time p50/p90/max, the schedule lag
(frames and seconds behind: the implied buffer), the device's write latency from /sys/block/<disk>/stat (ms per write)
and Dirty/Writeback from /proc/meminfo; a summary at the end; every file's timing in a CSV under --out.

WEAR: this writes real data (files x size). Keep --size-mb and --files to what the question needs; the empty-file directory
probe (exfat_dir_probe.py) is the zero-wear tool for the directory question. The folder is deleted at the end unless --keep.
Refuses to run unless --root is a mount point (or --force). Deletes only what it made. No sudo.

  python3 -I exfat_write_probe.py --size-mb 1.3 --fps 38 --seconds 300 --budget-mb 600            # emulate a 2K lossless take
  python3 -I exfat_write_probe.py --size-mb 12.4 --files 300 --workers 1                           # one writer: contiguous files?
  python3 -I exfat_write_probe.py --size-mb 12.4 --files 300 --prealloc                            # preallocated: FAT chains gone?
  python3 -I exfat_write_probe.py --size-mb 12.4 --files 300 --fsync none                          # no per-file fsync/FLUSH
  python3 -I exfat_write_probe.py --size-mb 12.4 --files 300 --chunk-kb 0 --prealloc --direct      # cinepi-raw style, direct
"""
import argparse, collections, mmap, os, queue, shutil, statistics, sys, threading, time

PAGE = 4096


def root_disk(path):
    """/dev/sda1 -> sda, /dev/nvme0n1p2 -> nvme0n1 (for /sys/block/<disk>/stat); '' if unknown."""
    try:
        st = os.stat(path)
        dev = '%d:%d' % (os.major(st.st_dev), os.minor(st.st_dev))
        for d in os.listdir('/sys/class/block'):
            try:
                if open('/sys/class/block/%s/dev' % d).read().strip() == dev:
                    p = os.path.realpath('/sys/class/block/%s' % d)
                    if os.path.exists(p + '/partition'):
                        return os.path.basename(os.path.realpath(p + '/..'))
                    return d
            except OSError:
                pass
    except OSError:
        pass
    return ''


def dev_stat(disk):
    """(writes completed, sectors written, write ticks ms, in flight, io ticks ms) or None."""
    try:
        f = open('/sys/block/%s/stat' % disk).read().split()
        return int(f[4]), int(f[6]), int(f[7]), int(f[8]), int(f[9])
    except (OSError, IndexError, ValueError):
        return None


def meminfo(keys=('Dirty', 'Writeback')):
    out = {}
    try:
        for l in open('/proc/meminfo'):
            k = l.split(':')[0]
            if k in keys:
                out[k] = int(l.split()[1])
    except OSError:
        pass
    return out


class Probe:
    def __init__(self, a):
        self.a = a
        self.size = int(a.size_mb * 1e6)
        self.padded = (self.size + PAGE - 1) // PAGE * PAGE
        # one shared data buffer, page-aligned (mmap), filled with a non-repeating pattern so a controller cannot dedupe it
        self.buf = mmap.mmap(-1, self.padded)
        pat = os.urandom(1 << 20)
        for off in range(0, self.padded, 1 << 20):
            self.buf[off:off + min(1 << 20, self.padded - off)] = pat[:min(1 << 20, self.padded - off)]
        self.view = memoryview(self.buf)
        self.q = queue.Queue()
        self.done_lock = threading.Lock()
        self.finished = []          # (index, t_open, t_close, path) in completion order
        self.to_sync = []
        self.stop = threading.Event()
        self.buffer_full = False
        self.direct_fallback = False
        self.errors = 0

    def path(self, i):
        d = self.a.dir
        if self.a.subdir:
            d = os.path.join(d, 'part_%03d' % (i // self.a.subdir))
        return os.path.join(d, '%s_%09d.dng' % (os.path.basename(self.a.dir), i))

    def ensure_dir(self, i):
        if self.a.subdir and i % self.a.subdir == 0:
            os.makedirs(os.path.dirname(self.path(i)), exist_ok=True)

    def write_one(self, i):
        p = self.path(i)
        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_CLOEXEC
        direct = self.a.direct and not self.direct_fallback
        if direct:
            flags |= os.O_DIRECT
        t0 = time.perf_counter_ns()
        fd = os.open(p, flags, 0o644)
        try:
            if self.a.prealloc:
                os.ftruncate(fd, self.padded if direct else self.size)
            try:
                os.posix_fadvise(fd, 0, 0, os.POSIX_FADV_SEQUENTIAL)
            except (AttributeError, OSError):
                pass
            total = self.padded if direct else self.size
            chunk = self.a.chunk_kb * 1024 if self.a.chunk_kb else total
            if direct:
                chunk = max(PAGE, chunk // PAGE * PAGE)
            off = 0
            while off < total:
                n = min(chunk, total - off)
                try:
                    w = os.write(fd, self.view[off:off + n])
                except OSError as e:
                    if direct and e.errno == 22:       # EINVAL: this filesystem/alignment refuses O_DIRECT here
                        self.direct_fallback = True
                        os.close(fd)
                        os.unlink(p)
                        return self.write_one(i)
                    raise
                off += w
            if direct and self.padded != self.size:
                os.ftruncate(fd, self.size)
            if self.a.writeback and not direct:
                try:
                    os.sync_file_range(fd, 0, 0, os.SYNC_FILE_RANGE_WRITE)
                except (AttributeError, OSError):
                    pass
        finally:
            os.close(fd)
        t1 = time.perf_counter_ns()
        with self.done_lock:
            self.finished.append((i, t0, t1))
            if self.a.fsync == 'tick':
                self.to_sync.append(p)

    def worker(self):
        while not self.stop.is_set():
            try:
                i = self.q.get(timeout=0.2)
            except queue.Empty:
                continue
            if i is None:
                return
            try:
                self.write_one(i)
            except OSError as e:
                self.errors += 1
                print('write error on file %d: %s' % (i, e), file=sys.stderr)

    def syncer(self):
        """Core's syncLoop: every --sync-ms fsync each file finished since the last tick (then drop its pages), then the folder."""
        interval = self.a.sync_ms / 1000.0
        while not self.stop.wait(interval):
            with self.done_lock:
                files, self.to_sync = self.to_sync, []
            dirs = set()
            for p in files:
                try:
                    fd = os.open(p, os.O_RDONLY | os.O_CLOEXEC)
                    os.fsync(fd)
                    try:
                        os.posix_fadvise(fd, 0, 0, os.POSIX_FADV_DONTNEED)
                    except (AttributeError, OSError):
                        pass
                    os.close(fd)
                    dirs.add(os.path.dirname(p))
                except OSError:
                    pass
            for d in dirs:
                try:
                    fd = os.open(d, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
                    os.fsync(fd)
                    os.close(fd)
                except OSError:
                    pass

    def run(self):
        a = self.a
        os.makedirs(a.dir)
        disk = root_disk(a.root)
        threads = [threading.Thread(target=self.worker, daemon=True) for _ in range(a.workers)]
        for t in threads:
            t.start()
        sync_t = None
        if a.fsync == 'tick':
            sync_t = threading.Thread(target=self.syncer, daemon=True)
            sync_t.start()
        st0 = os.statvfs(a.root)
        free0 = st0.f_bavail * st0.f_frsize
        t_start = time.perf_counter()
        prev_stat = dev_stat(disk) if disk else None
        prev_t = t_start
        report_at = 10.0 if a.fps else None
        next_report_files = 1000
        enqueued = 0
        last_line = 0
        budget_bytes = int(a.budget_mb * 1e6)
        rows = []    # (t, files_done, mbps, p50, p90, max, lag_frames, lag_s, dev_lat_ms, dirty_kb, writeback_kb)
        print('folder %s  size %.2f MB  workers %d  chunk %s  fsync %s  prealloc %s  direct %s  subdir %s  fps %s  disk %s' % (
            a.dir, self.size / 1e6, a.workers, ('%d KiB' % a.chunk_kb) if a.chunk_kb else 'whole file', a.fsync, a.prealloc,
            a.direct, a.subdir or '-', a.fps or 'max', disk or '?'), flush=True)
        try:
            while True:
                now = time.perf_counter()
                el = now - t_start
                if a.seconds and el >= a.seconds:
                    break
                if a.files and enqueued >= a.files and self.q.empty() and len(self.finished) >= a.files:
                    break
                # feed the queue: paced at fps, or keep 2 x workers in flight
                if a.fps:
                    due = int(el * a.fps)
                    while enqueued < due and (not a.files or enqueued < a.files):
                        self.ensure_dir(enqueued)
                        self.q.put(enqueued)
                        enqueued += 1
                    lag_frames = enqueued - len(self.finished)
                    if budget_bytes and lag_frames * self.size >= 0.9 * budget_bytes:
                        self.buffer_full = True
                        print('BUFFER FULL at %.1f s: %d frames (%.0f MB) behind the schedule, 90 %% of the %d MB budget' % (
                            el, lag_frames, lag_frames * self.size / 1e6, a.budget_mb), flush=True)
                        break
                else:
                    while enqueued - len(self.finished) < 2 * a.workers and (not a.files or enqueued < a.files):
                        self.ensure_dir(enqueued)
                        self.q.put(enqueued)
                        enqueued += 1
                time.sleep(0.005)
                done = len(self.finished)
                if (report_at and el >= report_at) or (not report_at and done >= next_report_files):
                    with self.done_lock:
                        recent = self.finished[last_line:]
                    last_line = len(self.finished)
                    lat = sorted((t1 - t0) / 1e6 for _, t0, t1 in recent) or [0.0]
                    st = os.statvfs(a.root)
                    written_mb = (free0 - st.f_bavail * st.f_frsize) / 1e6
                    dt_ = now - prev_t
                    cur = dev_stat(disk) if disk else None
                    dev_lat = ''
                    if cur and prev_stat and cur[0] > prev_stat[0]:
                        dev_lat = '%.1f' % ((cur[2] - prev_stat[2]) / (cur[0] - prev_stat[0]))
                    prev_stat = cur
                    mi = meminfo()
                    lag = enqueued - done
                    rate = len(recent) / dt_ if dt_ else 0
                    print('%6.1f s  files %6d  %5.1f files/s  %6.1f MB/s  per-file p50 %6.1f p90 %6.1f max %7.1f ms  lag %5d frames = %5.1f s  dev write %s ms  dirty %6s KB wb %6s KB%s' % (
                        el, done, rate, rate * self.size / 1e6, lat[len(lat) // 2], lat[int(0.9 * (len(lat) - 1))], lat[-1],
                        lag, lag / a.fps if a.fps else 0, dev_lat or '-', mi.get('Dirty', '?'), mi.get('Writeback', '?'),
                        '  (O_DIRECT refused: buffered)' if self.direct_fallback else ''), flush=True)
                    rows.append((round(el, 1), done, round(rate * self.size / 1e6, 1), lat[len(lat) // 2], lat[int(0.9 * (len(lat) - 1))], lat[-1],
                                 lag, dev_lat, mi.get('Dirty', ''), mi.get('Writeback', '')))
                    prev_t = now
                    if report_at:
                        report_at += 10.0
                    next_report_files = done + 1000
        except KeyboardInterrupt:
            print('interrupted', flush=True)
        # drain and stop
        if not self.buffer_full:
            while len(self.finished) < enqueued and not self.errors:
                time.sleep(0.05)
        self.stop.set()
        for _ in threads:
            self.q.put(None)
        for t in threads:
            t.join(5)
        if sync_t:
            sync_t.join(5)
        el = time.perf_counter() - t_start
        done = len(self.finished)
        lat = sorted((t1 - t0) / 1e6 for _, t0, t1 in self.finished) or [0.0]
        print('SUMMARY files %d in %.1f s = %.1f files/s, %.1f MB/s; per-file p50 %.1f p90 %.1f p99 %.1f max %.1f ms; errors %d%s%s' % (
            done, el, done / el if el else 0, done * self.size / 1e6 / el if el else 0, lat[len(lat) // 2], lat[int(0.9 * (len(lat) - 1))],
            lat[int(0.99 * (len(lat) - 1))], lat[-1], self.errors, '; BUFFER FULL' if self.buffer_full else '',
            '; O_DIRECT was refused, ran buffered' if self.direct_fallback else ''), flush=True)
        os.makedirs(a.out, exist_ok=True)
        csvp = os.path.join(a.out, os.path.basename(a.dir) + '.csv')
        with open(csvp, 'w') as f:
            f.write('index,t_open_ns,t_close_ns,ms\n')
            for i, t0, t1 in sorted(self.finished):
                f.write('%d,%d,%d,%.3f\n' % (i, t0, t1, (t1 - t0) / 1e6))
            f.write('# windows: t_s,files,mbps,p50_ms,p90_ms,max_ms,lag_frames,dev_write_ms,dirty_kb,writeback_kb\n')
            for r in rows:
                f.write('# ' + ','.join(str(x) for x in r) + '\n')
        print('per-file timings:', csvp)
        if not a.keep:
            shutil.rmtree(a.dir, ignore_errors=True)
            print('folder removed (the drive keeps the written clusters until a trim: Core trims only after its own deletes)')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--root', default='/media/RAW')
    ap.add_argument('--out', default='/run/apertar-media' if os.path.isdir('/run/apertar-media') else '/tmp')
    ap.add_argument('--size-mb', type=float, default=1.3)
    ap.add_argument('--files', type=int, default=0)
    ap.add_argument('--seconds', type=float, default=0)
    ap.add_argument('--fps', type=float, default=0)
    ap.add_argument('--budget-mb', type=float, default=0)
    ap.add_argument('--workers', type=int, default=4)
    ap.add_argument('--chunk-kb', type=int, default=480)
    ap.add_argument('--fsync', choices=('tick', 'none'), default='tick')
    ap.add_argument('--sync-ms', type=int, default=1000)
    ap.add_argument('--no-writeback', dest='writeback', action='store_false', help="skip Core's per-file sync_file_range hint")
    ap.add_argument('--prealloc', action='store_true')
    ap.add_argument('--direct', action='store_true')
    ap.add_argument('--subdir', type=int, default=0)
    ap.add_argument('--keep', action='store_true')
    ap.add_argument('--force', action='store_true', help='allow a --root that is not a mount point (tests)')
    a = ap.parse_args()
    if not a.files and not a.seconds:
        sys.exit('give --files N or --seconds S')
    if not os.path.ismount(a.root) and not a.force:
        sys.exit('%s is not a mount point; refusing (use --force for a test directory)' % a.root)
    a.dir = os.path.join(a.root, 'probe_exfat_write_' + time.strftime('%H%M%S'))
    if os.path.exists(a.dir):
        sys.exit('%s exists; refusing' % a.dir)
    Probe(a).run()


if __name__ == '__main__':
    main()
