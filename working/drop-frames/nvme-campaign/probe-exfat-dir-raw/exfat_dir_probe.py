#!/usr/bin/env python3
"""exfat_dir_probe.py: zero-wear probe of exFAT directory create and unlink cost against file count.
Creates N empty files in ONE new folder under ROOT, timing each open(O_CREAT|O_EXCL)+close; then unlinks them in creation order,
timing each unlink. Empty files allocate no cluster: the only bytes written are the directory's own entries (5 per 33-char name).
Per-file latencies go to a CSV in OUT (tmpfs); a per-1000 summary and a linear fit are printed. No sudo. Deletes only what it made.
  python3 -I exfat_dir_probe.py --n 60000                      # full run: create, fsync the folder, unlink, rmdir
  python3 -I exfat_dir_probe.py --n 10000 --keep               # create and keep (for the cold-cache delete run)
  python3 -I exfat_dir_probe.py --delete-only --dir /media/RAW/probe_exfat_dir_HHMMSS   # time the unlinks of a kept folder
  --short-names uses 16-char names (4 entries per file) instead of 33 (5 entries), to see the entry-count effect.
"""
import argparse, os, statistics, sys, time

def summarize(label, lat, per=1000):
    rows = []
    for s in range(0, len(lat), per):
        chunk = lat[s:s + per]
        if not chunk:
            continue
        chunk_sorted = sorted(chunk)
        rows.append((s + len(chunk), statistics.median(chunk) / 1e6, chunk_sorted[int(0.9 * (len(chunk) - 1))] / 1e6, max(chunk) / 1e6))
    print(f"{label}: files  median_ms  p90_ms  max_ms   (per block of {per})")
    for n, med, p90, mx in rows:
        print(f"{label}: {n:7d}  {med:9.3f}  {p90:6.3f}  {mx:7.3f}")
    # least-squares fit of the block medians against the block's end index: slope = ns per file
    if len(rows) >= 3:
        xs = [r[0] for r in rows]; ys = [r[1] * 1e6 for r in rows]
        mx_ = sum(xs) / len(xs); my_ = sum(ys) / len(ys)
        slope = sum((x - mx_) * (y - my_) for x, y in zip(xs, ys)) / sum((x - mx_) ** 2 for x in xs)
        icpt = my_ - slope * mx_
        print(f"{label}: fit median_ns = {icpt:.0f} + {slope:.2f} * files   (slope / entries-per-file = c per entry)")
        return slope, icpt
    return None, None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--n', type=int, default=60000)
    ap.add_argument('--root', default='/media/RAW')
    ap.add_argument('--out', default='/run/apertar-media' if os.path.isdir('/run/apertar-media') else '/tmp')
    ap.add_argument('--short-names', action='store_true')
    ap.add_argument('--keep', action='store_true')
    ap.add_argument('--delete-only', action='store_true')
    ap.add_argument('--dir', default=None)
    a = ap.parse_args()
    if not os.path.ismount(a.root):
        sys.exit(f"{a.root} is not a mount point; refusing")
    entries = 4 if a.short_names else 5
    name = (lambda i: f"C1_{i:09d}.dng") if a.short_names else (lambda i: f"cDNG_26-11-08_C0001_{i:09d}.dng")
    stamp = time.strftime('%H%M%S')
    d = a.dir or os.path.join(a.root, f"probe_exfat_dir_{stamp}")
    if not os.path.basename(d).startswith('probe_exfat_dir_'):
        sys.exit("refusing: the folder name must start with probe_exfat_dir_")
    csv = os.path.join(a.out, f"exfat_probe_{stamp}.csv")
    st0 = os.statvfs(a.root); used0 = (st0.f_blocks - st0.f_bfree) * st0.f_frsize
    print(f"folder {d}  entries/file {entries}  used_bytes_before {used0}  csv {csv}")
    create_lat = []
    if not a.delete_only:
        os.mkdir(d)
        t_start = time.perf_counter_ns()
        for i in range(a.n):
            p = os.path.join(d, name(i))
            t0 = time.perf_counter_ns()
            fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC, 0o644)
            os.close(fd)
            create_lat.append(time.perf_counter_ns() - t0)
            if (i + 1) % 5000 == 0:
                print(f"created {i + 1}  last-5000 median {statistics.median(create_lat[-5000:]) / 1e6:.3f} ms  elapsed {(time.perf_counter_ns() - t_start) / 1e9:.1f} s", flush=True)
        t0 = time.perf_counter_ns(); dfd = os.open(d, os.O_RDONLY); os.fsync(dfd); os.close(dfd)
        print(f"folder fsync {(time.perf_counter_ns() - t0) / 1e6:.1f} ms; create total {(time.perf_counter_ns() - t_start) / 1e9:.1f} s")
        s = os.stat(os.path.join(d, name(0))); print(f"check: st_size {s.st_size} st_blocks {s.st_blocks} (both must be 0)")
        summarize('create', create_lat)
    st1 = os.statvfs(a.root); used1 = (st1.f_blocks - st1.f_bfree) * st1.f_frsize
    print(f"used_bytes_after_create {used1}  delta {used1 - used0} (expect ~{a.n * entries * 32} B of directory, rounded up to 128 KiB clusters)")
    unlink_lat = []
    if not a.keep:
        names = sorted(os.listdir(d))
        t_start = time.perf_counter_ns()
        for i, fn in enumerate(names):
            t0 = time.perf_counter_ns(); os.unlink(os.path.join(d, fn)); unlink_lat.append(time.perf_counter_ns() - t0)
            if (i + 1) % 5000 == 0:
                print(f"unlinked {i + 1}  last-5000 median {statistics.median(unlink_lat[-5000:]) / 1e6:.3f} ms  elapsed {(time.perf_counter_ns() - t_start) / 1e9:.1f} s", flush=True)
        os.rmdir(d); os.sync()
        print(f"unlink total {(time.perf_counter_ns() - t_start) / 1e9:.1f} s; folder removed")
        summarize('unlink', unlink_lat)
    with open(csv, 'w') as f:
        f.write('index,create_ns,unlink_ns\n')
        for i in range(max(len(create_lat), len(unlink_lat))):
            f.write(f"{i},{create_lat[i] if i < len(create_lat) else ''},{unlink_lat[i] if i < len(unlink_lat) else ''}\n")
    st2 = os.statvfs(a.root); print(f"used_bytes_end {(st2.f_blocks - st2.f_bfree) * st2.f_frsize}  csv written {csv}")

if __name__ == '__main__':
    main()
