#!/usr/bin/env python3
"""Frame delivery from the IPA's per-frame warning: ipa_rate.py <since>  (journal time)"""
import re, subprocess, sys

args = ['journalctl', '-u', 'apertar-core', '--since', sys.argv[1], '--no-pager'] + (['--until', sys.argv[2]] if len(sys.argv) > 2 else [])
out = subprocess.run(args,
                     capture_output=True, text=True).stdout
ts = []
for line in out.splitlines():
    if 'No HDR algorithm' in line:
        m = re.search(r'\[(\d+):(\d+):(\d+\.\d+)\]', line)
        if m:
            h, mi, s = m.groups()
            ts.append(int(h) * 3600 + int(mi) * 60 + float(s))
if len(ts) < 2:
    sys.exit('not enough lines')
dts = [b - a for a, b in zip(ts, ts[1:])]
span = ts[-1] - ts[0]
late = [d for d in dts if d > 0.060]
print(f'lines={len(ts)} span={span:.2f}s rate={(len(ts) - 1) / span:.2f}/s '
      f'intervals>60ms={len(late)} max={max(dts) * 1000:.0f}ms')
buckets = {}
for d in dts:
    b = min(int(d * 1000 // 10) * 10, 150)
    buckets[b] = buckets.get(b, 0) + 1
print(' '.join(f'{k}ms:{v}' for k, v in sorted(buckets.items())))
gaps = [round(ts[i + 1] - ts[0], 2) for i, d in enumerate(dts) if d > 0.060]
if gaps:
    print('gaps at s:', ' '.join(f'{g:.1f}' for g in gaps[:30]))
