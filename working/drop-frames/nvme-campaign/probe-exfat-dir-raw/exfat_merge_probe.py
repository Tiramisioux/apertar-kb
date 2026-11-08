#!/usr/bin/env python3
"""exfat_merge_probe.py: zero-wear probe of the cost of merging one exFAT folder of empty frame files into another.
Renames every file of --src into --dst in creation order, timing each os.rename. File i of --src (name ..._{i:09d}.dng) becomes
..._{offset+i:09d}.dng in --dst, as a flatten of split parts does (frame numbering continues), so no name collides; refuses if a
target exists. Per-1000 medians and a linear fit as exfat_dir_probe.py; CSV to OUT (tmpfs). No sudo. Touches only probe_exfat_dir_*.
  python3 -I exfat_merge_probe.py --dst /media/RAW/probe_exfat_dir_A --src /media/RAW/probe_exfat_dir_B --offset 10000
  add --cleanup to unlink everything and rmdir both folders afterwards.
"""
import argparse, os, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from exfat_dir_probe import summarize

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dst', required=True)
    ap.add_argument('--src', required=True)
    ap.add_argument('--offset', type=int, required=True)
    ap.add_argument('--out', default='/run/apertar-media' if os.path.isdir('/run/apertar-media') else '/tmp')
    ap.add_argument('--cleanup', action='store_true')
    a = ap.parse_args()
    for d in (a.dst, a.src):
        if not os.path.basename(d.rstrip('/')).startswith('probe_exfat_dir_') or not os.path.isdir(d):
            sys.exit(f"refusing: {d} is not an existing probe_exfat_dir_* folder")
    pat = re.compile(r'^(.*_)(\d{9})\.dng$')
    src_names = sorted(os.listdir(a.src))
    print(f"dst {a.dst} ({len(os.listdir(a.dst))} files)  src {a.src} ({len(src_names)} files)  offset {a.offset}")
    lat = []
    t_start = time.perf_counter_ns()
    for i, fn in enumerate(src_names):
        m = pat.match(fn)
        if not m:
            sys.exit(f"refusing: unexpected name {fn}")
        target = os.path.join(a.dst, f"{m.group(1)}{a.offset + int(m.group(2)):09d}.dng")
        if os.path.lexists(target):
            sys.exit(f"refusing: {target} exists")
        t0 = time.perf_counter_ns(); os.rename(os.path.join(a.src, fn), target); lat.append(time.perf_counter_ns() - t0)
        if (i + 1) % 2000 == 0:
            print(f"renamed {i + 1}  elapsed {(time.perf_counter_ns() - t_start) / 1e9:.1f} s", flush=True)
    t0 = time.perf_counter_ns()
    for d in (a.dst, a.src):
        dfd = os.open(d, os.O_RDONLY); os.fsync(dfd); os.close(dfd)
    print(f"fsync both folders {(time.perf_counter_ns() - t0) / 1e6:.1f} ms; rename total {(time.perf_counter_ns() - t_start) / 1e9:.1f} s; dst now {len(os.listdir(a.dst))} files, src {len(os.listdir(a.src))}")
    summarize('rename', lat)
    stamp = time.strftime('%H%M%S')
    csv = os.path.join(a.out, f"exfat_merge_{stamp}.csv")
    with open(csv, 'w') as f:
        f.write('index,rename_ns\n')
        for i, v in enumerate(lat):
            f.write(f"{i},{v}\n")
    print(f"csv written {csv}")
    if a.cleanup:
        t_start = time.perf_counter_ns()
        for fn in sorted(os.listdir(a.dst)):
            os.unlink(os.path.join(a.dst, fn))
        for fn in os.listdir(a.src):
            os.unlink(os.path.join(a.src, fn))
        os.rmdir(a.dst); os.rmdir(a.src); os.sync()
        print(f"cleanup: both folders removed in {(time.perf_counter_ns() - t_start) / 1e9:.1f} s")

if __name__ == '__main__':
    main()
