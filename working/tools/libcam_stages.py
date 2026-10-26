#!/usr/bin/env python3
"""Per-frame stage times from libcamera's RPi debug log: libcam_stages.py <journal-cat file>

Needs Core started with LIBCAMERA_LOG_LEVELS=RPI:0,RPiStream:0 (systemd drop-in, Patrik's sudo).
Follows each Bayer buffer id through: CFE image dequeue -> IPA signalled (swap + software stats done)
-> ISP (back end) input queued -> ISP input complete. Prints medians/p90 per stage, the CFE arrival
interval, and every log line that mentions a drop.
"""
import re, statistics, sys

TIME = re.compile(r'^\[(\d+):(\d+):(\d+\.\d+)\]')
PATTERNS = {
    'cfe': re.compile(r'Stream CFE Image buffer dequeue, buffer id (\d+)'),
    'signal': re.compile(r'Signalling IPA processStats and prepareIsp: Bayer buffer id: (\d+)'),
    'be_start': re.compile(r'Input re-queue to ISP, buffer id (\d+)'),
    'be_done': re.compile(r'Stream ISP Input buffer complete, buffer id (\d+)'),
}
RAWSTATS = re.compile(r'RawStats \S+ ([\d.]+) ms')

frames, open_frames, rawstats, drops = [], {}, [], []
for line in open(sys.argv[1], errors='replace'):
    m = TIME.match(line)
    if not m:
        continue
    t = (int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3])) * 1000.0
    if 'drop' in line.lower():
        drops.append(line.strip()[:200])
    if r := RAWSTATS.search(line):
        rawstats.append(float(r[1]))
        continue
    for name, pat in PATTERNS.items():
        p = pat.search(line)
        if not p:
            continue
        bid = p[1]
        if name == 'cfe':
            open_frames[bid] = {'cfe': t}
        elif bid in open_frames and name not in open_frames[bid]:
            open_frames[bid][name] = t
            if name == 'be_done':
                frames.append(open_frames.pop(bid))
        break

def summary(label, values):
    if not values:
        print(f'  {label:<34} n=0')
        return
    values = sorted(values)
    p90 = values[int(0.9 * (len(values) - 1))]
    print(f'  {label:<34} n={len(values):<4} median={statistics.median(values):6.1f} ms  p90={p90:6.1f}  max={values[-1]:6.1f}')

full = [f for f in frames if {'signal', 'be_start', 'be_done'} <= f.keys()]
arrivals = sorted(f['cfe'] for f in frames)
print(f'frames traced: {len(full)}; CFE arrivals: {len(arrivals)}')
summary('CFE arrival interval', [b - a for a, b in zip(arrivals, arrivals[1:])])
summary('raw stats (libcamera\'s own figure)', rawstats)
summary('CFE dequeue -> IPA signalled', [f['signal'] - f['cfe'] for f in full])
summary('IPA signalled -> back end start', [f['be_start'] - f['signal'] for f in full])
summary('back end start -> done', [f['be_done'] - f['be_start'] for f in full])
summary('CFE dequeue -> back end done', [f['be_done'] - f['cfe'] for f in full])
starts = sorted(f['be_start'] for f in full)
summary('back end start interval', [b - a for a, b in zip(starts, starts[1:])])
print(f'drop lines: {len(drops)}')
for d in drops[:8]:
    print('  ' + d)
