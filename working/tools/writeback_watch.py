#!/usr/bin/env python3
"""Sample dirty/writeback page counts while a test runs: writeback_watch.py [seconds] [interval_s]

Read-only. Prints one line per sample: elapsed s, nr_dirty MB, nr_writeback MB, MemFree MB.
Run it in a second shell while `dd` or a take runs, then line the first gap from ipa_rate.py
up with the first non-zero nr_writeback."""
import sys, time

secs = float(sys.argv[1]) if len(sys.argv) > 1 else 15.0
step = float(sys.argv[2]) if len(sys.argv) > 2 else 0.1
page_kb = 4

def vm():
    out = {}
    for line in open('/proc/vmstat'):
        k, v = line.split()
        if k in ('nr_dirty', 'nr_writeback'):
            out[k] = int(v)
    for line in open('/proc/meminfo'):
        if line.startswith('MemFree:'):
            out['free_kb'] = int(line.split()[1])
    return out

t0 = time.time()
print('t_s dirty_MB writeback_MB free_MB')
while time.time() - t0 < secs:
    s = vm()
    print(f"{time.time() - t0:6.2f} {s['nr_dirty'] * page_kb / 1024:8.1f} {s['nr_writeback'] * page_kb / 1024:8.1f} {s['free_kb'] / 1024:8.0f}", flush=True)
    time.sleep(step)
