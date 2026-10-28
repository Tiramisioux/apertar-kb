#!/usr/bin/env python3
"""Split libcamera's per-frame PiSP cycle into its serial stages, read-only.

Input: a log written with LIBCAMERA_LOG_LEVELS=RPI:0,RPiStream:0 (journalctl -o cat, or LIBCAMERA_LOG_FILE).
Every line starts with libcamera's monotonic log time [H:MM:SS.nnnnnnnnn]; the "timestamp:" fields are kernel
CLOCK_MONOTONIC ns (CFE: start of frame; ISP Input complete: the BE done interrupt, pisp_be.c pispbe_isr_jobdone).

Per frame (keyed by the CFE buffer id, in time order):
  queue  = Signalling IPA ... - CFE dequeue log      (waiting for the pipeline to go Idle)
  S1     = Input re-queue to ISP - Signalling         (IPA thread + two hand-offs)
  S2     = BE done timestamp - Input re-queue         (libpisp Prepare + QBUFs + BE hardware; upper bound on hardware)
  S3     = ISP Input complete log - BE done timestamp (how long the done event waited for the thread)
  S4     = next frame's Signalling - ISP Input complete log (request completion incl. Core's callback)
  cycle  = next Input re-queue - this Input re-queue  (the pipeline period; 33.33 ms needed for 30 fps)
  sof    = CFE dequeue log - CFE timestamp            (SOF to dequeue on the thread)

Usage: python3 -I be_cycle.py <log> [more logs]
"""
import re
import statistics
import sys

TIME = re.compile(r'^\[(\d+):(\d+):(\d+)\.(\d+)\]')
EVENTS = {
    'cfe': re.compile(r'Stream CFE Image buffer dequeue, buffer id (\d+), timestamp: (\d+)'),
    'signal': re.compile(r'Signalling IPA processStats and prepareIsp: Bayer buffer id: (\d+)'),
    'start': re.compile(r'Input re-queue to ISP, buffer id (\d+)'),
    'done': re.compile(r'Stream ISP Input buffer complete, buffer id (\d+), timestamp: (\d+)'),
}


def parse(path):
    frames, open_by_id, lines, first, last = [], {}, 0, None, None
    with open(path, errors='replace') as f:
        for line in f:
            m = TIME.match(line)
            if not m:
                continue
            frac = m.group(4)
            t = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3)) + int(frac) / 10 ** len(frac)
            lines += 1
            first = t if first is None else first
            last = t
            for kind, rx in EVENTS.items():
                e = rx.search(line)
                if not e:
                    continue
                bid = e.group(1)
                if kind == 'cfe':
                    fr = {'id': bid, 'cfe': t, 'cfe_ts': int(e.group(2)) / 1e9}
                    frames.append(fr)
                    open_by_id[bid] = fr
                else:
                    fr = open_by_id.get(bid)
                    if fr is None or kind in fr:
                        continue
                    fr[kind] = t
                    if kind == 'done':
                        fr['done_ts'] = int(e.group(2)) / 1e9
                        open_by_id.pop(bid, None)
                break
    return frames, lines, first, last


def stats(name, values, unit='ms'):
    v = sorted(values)
    if not v:
        print(f'  {name:7s} no samples')
        return
    p = lambda q: v[min(len(v) - 1, int(q * (len(v) - 1) + 0.5))]
    print(f'  {name:7s} n={len(v):4d}  median {statistics.median(v):7.2f}  p10 {p(.1):7.2f}  p90 {p(.9):7.2f}  max {v[-1]:7.2f} {unit}')


def main():
    for path in sys.argv[1:]:
        frames, lines, first, last = parse(path)
        done = [f for f in frames if all(k in f for k in ('signal', 'start', 'done'))]
        done.sort(key=lambda f: f['start'])
        span = (last - first) if lines else 0.0
        print(f'{path}: {lines} log lines over {span:.1f} s, {len(frames)} CFE frames, {len(done)} complete cycles')
        if span > 0 and len(frames) / span < 25:
            print('  WARNING: fewer than 25 CFE dequeues per second in the log: lines may have been dropped '
                  '(journald rate limit?); use LIBCAMERA_LOG_FILE=/dev/shm/... for new windows')
        ms = lambda x: x * 1e3
        q = [ms(f['signal'] - f['cfe']) for f in done]
        s1 = [ms(f['start'] - f['signal']) for f in done]
        s2 = [ms(f['done_ts'] - f['start']) for f in done]
        s3 = [ms(f['done'] - f['done_ts']) for f in done]
        s4 = [ms(b['signal'] - a['done']) for a, b in zip(done, done[1:]) if b['signal'] >= a['done']]
        cyc = [ms(b['start'] - a['start']) for a, b in zip(done, done[1:])]
        sof = [ms(f['cfe'] - f['cfe_ts']) for f in frames]
        if s2 and min(s2) < 0 or s3 and min(s3) < -1:
            print('  WARNING: negative S2/S3: the log clock and the kernel timestamps are not on the same base; S2/S3 invalid')
        for name, vals in (('queue', q), ('S1', s1), ('S2', s2), ('S3', s3), ('S4', s4), ('cycle', cyc), ('sof', sof)):
            stats(name, vals)
        if cyc:
            print(f'  pipeline rate {1000 / statistics.median(cyc):.2f} fps (median cycle); 30 fps needs a median cycle <= 33.33 ms')


if __name__ == '__main__':
    main()
