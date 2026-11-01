#!/usr/bin/env python3
"""takes_from_journal.py RAW > table.md: one row per recording from Core's journal lines.

Make RAW on the Pi (both boots of the evening; -1 = the previous boot):
  for b in -1 0; do journalctl -u apertar-core -b $b --no-pager -o short-iso | grep -E \
    "recording clip:|camera configured:|capture stats:|recording stats:|storage preroll: reason|buffer: safety stop|lossless timing:"; \
  done > takes-raw.txt

Columns: the mode is the last `camera configured` line before the clip (raw size, HDR16 = SRGGB16 storage_bits=16,
SDR12 COMP1 = RGGB_PISP_COMP1, SDR12 unpacked = SRGGB16 storage_bits=12). 'Lost at capture' = dropped_gap_estimate;
Core prints the capture stats line only when it is non-zero, so a missing line counts as 0. 'fps' = (written + lost) /
(stop line - clip line), so it includes the stop latency. Pre-rolls are the clips followed by a `storage preroll: reason`
line (deleted after the measurement). The journal does not say which UI or Core settings a take ran with: see
night-2026-11-01.md for the windows.
"""
import re
import sys
from datetime import datetime


def ts(line):
    return datetime.fromisoformat(line[:25])


def mode_name(mode):
    if not mode:
        return '?'
    raw, _stream, fmt, bits, _pack = mode
    if fmt == 'RGGB_PISP_COMP1':
        kind = 'SDR12 COMP1'
    elif bits == '16':
        kind = 'HDR16'
    else:
        kind = f'SDR{bits} unpacked'
    return f'{raw} {kind}'


def main(path):
    mode = None
    takes = []
    cur = None
    for line in open(path).read().splitlines():
        if 'camera configured:' in line:
            m = re.search(r'raw=(\S+) .*stream=(\S+) format=(\S+) .*storage_bits=(\d+)(?: packing=(\S+))?', line)
            if m:
                mode = m.groups()
        elif 'recording clip:' in line:
            m = re.search(r'clip: /media/RAW/(\S+) format=(\S+) compression=(\S+)', line)
            cur = {'start': ts(line), 'clip': m.group(1), 'comp': m.group(3), 'mode': mode, 'gap': 0, 'enq': None,
                   'qfull': None, 'end': None, 'preroll': False, 'safety': False, 'cap': None}
            takes.append(cur)
        elif cur is None:
            continue
        elif 'capture stats:' in line:
            cur['gap'] = int(re.search(r'dropped_gap_estimate=(\d+)', line).group(1))
        elif 'recording stats:' in line:
            cur['enq'] = int(re.search(r'enqueued=(\d+)', line).group(1))
            q = re.search(r'dropped_queue_full=(\d+)', line)
            cur['qfull'] = int(q.group(1)) if q else None
            cur['end'] = ts(line)
        elif 'storage preroll: reason' in line:
            cur['preroll'] = True
        elif 'safety stop' in line:
            cur['safety'] = True
        elif 'lossless timing:' in line:
            c = re.search(r'estimated_capacity_fps=([0-9.]+)', line)
            cur['cap'] = c.group(1) if c else None

    print('| # | Start | Clip | Mode | Compression | Duration s | Written | Lost at capture | Lost % | fps | Notes |')
    print('| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |')
    for i, t in enumerate(takes, 1):
        start = t['start'].strftime('%H:%M:%S')
        if not t['end']:
            print(f"| {i} | {start} | `{t['clip']}` | {mode_name(t['mode'])} | {t['comp']} |  |  | {t['gap']} |  |  | no stop line |")
            continue
        dur = (t['end'] - t['start']).total_seconds()
        enq, gap = t['enq'], t['gap']
        pct = f'{100 * gap / (enq + gap):.2f}' if enq else ''
        fps = f'{(enq + gap) / dur:.1f}' if enq and dur > 0 else ''
        notes = []
        if t['preroll']:
            notes.append('pre-roll (deleted)')
        if t['safety']:
            notes.append('safety stop')
        if t['qfull']:
            notes.append(f"queue-full {t['qfull']}")
        if t['cap']:
            notes.append(f"lossless cap {t['cap']} fps")
        print(f"| {i} | {start} | `{t['clip']}` | {mode_name(t['mode'])} | {t['comp']} | {dur:.0f} | {enq} | {gap} | {pct} | {fps} | {', '.join(notes)} |")


if __name__ == '__main__':
    main(sys.argv[1])
