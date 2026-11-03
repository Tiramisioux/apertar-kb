#!/usr/bin/env python3
"""be_overlap.py RAWDIR: what lengthens the ISP back end (BE) job in a take, from libcamera's RPi debug log and the
1 Hz take log (desk analysis of evening 2, drop-frames/tests-2026-11/tier0-2026-11-03.md). Read-only, stdlib only.

RAWDIR holds raw-2026-11-03.tgz unpacked: <lib>-P<n>.log (LIBCAMERA_LOG_LEVELS=RPI:0,RPiStream:0 via LIBCAMERA_LOG_FILE),
take-e2-<take>-P<n>.log (take_logger.py) and e2-<take>.out (take3v3.sh console output).

Per frame (keyed by CFE buffer id, CFE SOF timestamp for the swap):
  swap   = CFE Config dequeue log - CFE Image dequeue log (same SOF timestamp): the Image dequeue handler's time, which in
           Clear HDR 16 holds the in-place 16-bit byte swap (~0.05 ms in SDR12, where there is none)
  queue  = Signalling - CFE Image dequeue (swap + RawStats + wait for the pipeline to go Idle)
  S1     = Input re-queue to ISP - Signalling
  S2     = BE done timestamp (kernel, pisp_be job-done) - Input re-queue log
  S3     = ISP Input complete log - BE done timestamp
  S4     = next Signalling - ISP Input complete log (only when the next frame was waiting)
  slack  = Input re-queue(N) - ISP Input complete(N-1): Core's and the UI's work on frame N-1 starts at complete(N-1)
Sections: 1 stage medians per take; 2 S2 by overlap with another frame's swap x slack; 3 the same with the exposure fixed
at the job's start; 4 the idle-regime phase (when the next frame's swap lands in a job); 5 per-second Spearman of S2
with the 1 Hz counters; 6 CPU time per delivered frame.
The 1 Hz log is in epoch seconds and libcamera in CLOCK_MONOTONIC: each take is aligned on the "clocks at
record_start: epoch= mono=" line take3v3.sh prints (from 2026-11-04); without it (evening 2), the offset is fitted once
per boot by matching per-second losses (CFE SOF gaps) with Core's recording_dropped_frames increments over the takes
that lost frames, else seeded from the label line's uptime (a few seconds off).
Usage: python3 -I be_overlap.py RAWDIR [--prefix e2] [--take NAME[:LIB] ...] [--utc-offset 1]
  RAWDIR holds <prefix>-<NAME>.out, take-<prefix>-<NAME>-P<n>.log and <LIB>-P<n>.log (LIB defaults to NAME).
  Without --take: every <prefix>-<NAME>.out in RAWDIR (for --prefix e2, evening 2's four units with their LIB names).
"""
import math
import os
import re
import statistics
import sys
from bisect import bisect_left

EVENING2 = [('g2', 'g2'), ('pv0b', 'pv0'), ('pv12', 'pv12'), ('frm', 'frm')]  # (take label, libcamera log prefix)


def parse_args(argv):
    if len(argv) < 2 or argv[1].startswith('-'):
        sys.exit(__doc__)
    raw, prefix, takes, utc = argv[1], 'e2', [], 1.0
    i = 2
    while i < len(argv):
        if argv[i] == '--prefix':
            prefix = argv[i + 1]
        elif argv[i] == '--take':
            name, _, lib = argv[i + 1].partition(':')
            takes.append((name, lib or name))
        elif argv[i] == '--utc-offset':
            utc = float(argv[i + 1])
        else:
            sys.exit(f'unknown argument {argv[i]}\n' + __doc__)
        i += 2
    if not takes:
        if prefix == 'e2':
            takes = EVENING2
        else:
            takes = sorted((f[len(prefix) + 1:-4], f[len(prefix) + 1:-4]) for f in os.listdir(raw)
                           if f.startswith(prefix + '-') and f.endswith('.out'))
    if not takes:
        sys.exit(f'no {prefix}-*.out in {raw}')
    return raw, prefix, takes, utc


RAW, PREFIX, TAKES, UTC_OFFSET = parse_args(sys.argv)
TIME = re.compile(r'^\[(\d+):(\d+):(\d+)\.(\d+)\]')
IMG = re.compile(r'Stream CFE Image buffer dequeue, buffer id (\d+), timestamp: (\d+)')
CFG = re.compile(r'Stream CFE Config buffer dequeue, buffer id \d+, timestamp: (\d+)')
SIG = re.compile(r'Signalling IPA processStats and prepareIsp: Bayer buffer id: (\d+)')
STA = re.compile(r'Input re-queue to ISP, buffer id (\d+)')
DON = re.compile(r'Stream ISP Input buffer complete, buffer id (\d+), timestamp: (\d+)')
RST = re.compile(r'RawStats \S+ ([\d.]+) ms')


def med(v):
    return statistics.median(v) if v else float('nan')


def q(v, x):
    v = sorted(v)
    return v[min(len(v) - 1, int(x * (len(v) - 1) + 0.5))] if v else float('nan')


def parse_lib(path):
    by_ts, open_by_id, frames, rawstats = {}, {}, [], []
    for line in open(path, errors='replace'):
        m = TIME.match(line)
        if not m:
            continue
        fr_ = m.group(4)
        t = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3)) + int(fr_) / 10 ** len(fr_)
        if e := IMG.search(line):
            f = {'img': t, 'ts': int(e.group(2)) / 1e9}
            by_ts[e.group(2)] = f
            open_by_id[e.group(1)] = f
            frames.append(f)
        elif e := CFG.search(line):
            f = by_ts.get(e.group(1))
            if f is not None and 'cfg' not in f:
                f['cfg'] = t
        elif e := SIG.search(line):
            f = open_by_id.get(e.group(1))
            if f is not None and 'sig' not in f:
                f['sig'] = t
        elif e := STA.search(line):
            f = open_by_id.get(e.group(1))
            if f is not None and 'start' not in f:
                f['start'] = t
        elif e := DON.search(line):
            f = open_by_id.pop(e.group(1), None)
            if f is not None and 'start' in f:
                f['done'] = t
                f['done_ts'] = int(e.group(2)) / 1e9
        elif e := RST.search(line):
            rawstats.append((t, float(e.group(1))))
    frames.sort(key=lambda f: f['ts'])
    # the frame period from the take itself (40 ms at 25 fps, 33.3 at 30, 30.3 at 33): the median SOF interval
    period = statistics.median([b['ts'] - a['ts'] for a, b in zip(frames, frames[1:])]) if len(frames) > 2 else 0.040
    for a, b in zip(frames, frames[1:]):
        b['lost'] = max(0, round((b['ts'] - a['ts']) / period) - 1)
    if frames:
        frames[0]['lost'] = 0
    return frames, rawstats


def parse_take(path):
    rows = []
    for line in open(path):
        if not line.startswith('t='):
            continue
        parts = line.rstrip('\n').split(' | ')
        head = parts[0].split()
        r = {'t': float(head[0][2:])}
        for kv in head[2:]:
            k, _, v = kv.partition('=')
            r[k] = int(v)
        for p in parts[1:]:
            w = p.split()
            if not w:
                continue
            if w[0] in ('mem', 'nvme'):
                for kv in w[1:]:
                    k, _, v = kv.partition('=')
                    if v.isdigit():
                        r[f'{w[0]}_{k}'] = int(v)
            elif w[0] == 'boost':
                r['boost'] = int(w[1].split('=')[1])
            elif w[0] == 'psi':
                tot = [int(x.split('=')[1]) for x in w if x.startswith('total=')]
                if len(tot) == 2:
                    r['psi_some'], r['psi_full'] = tot
            elif w[0].startswith('dropped='):
                v = w[0].split('=')[1]
                r['dropped'] = int(v) if v.isdigit() else None
            elif w[0] == 'thr':
                r['thr'] = {x.split(':')[0]: (x.split(':')[1], int(x.split(':')[2]), int(x.split(':')[3]))
                            for x in w[1:] if x.count(':') == 4}
        rows.append(r)
    return rows


def read_out(take):
    info, cur = {}, None
    for line in open(os.path.join(RAW, f'{PREFIX}-{take}.out')):
        if m := re.match(r'label=\S+-(P\d+) core=(\d+) ui=(\d+) camtid=\S+ pagesize=\d+ uptime_s=(\d+)', line):
            cur = m.group(1)
            info[cur] = {'uptime': int(m.group(4)), 'secs': 0, 'enqueued': None, 'lost': 0}
        elif cur and line.startswith('  camtid at start:'):
            info[cur]['camtid'] = line.split(':')[1].strip()
        elif cur and line.startswith('start '):
            info[cur]['start'] = line.split()[1]
        elif cur and (m := re.match(r'\s+clocks at record_start: epoch=([\d.]+) mono=([\d.]+)', line)):
            info[cur]['clock_off'] = float(m.group(1)) - float(m.group(2))
        elif cur and (m := re.match(r'mode: .*\bfps=([\d.]+)', line)):
            info[cur]['fps_set'] = float(m.group(1))
        elif cur and (m := re.match(r'\s+(\d+)s \d\d:\d\d:\d\d: dropped=', line)):
            info[cur]['secs'] = max(info[cur]['secs'], int(m.group(1)))
        elif cur and line.startswith('recording clip:'):
            m3 = re.search(r'dropped_gap_estimate=(\d+)', line)
            info[cur]['lost'] = int(m3.group(1)) if m3 else 0
            m4 = re.search(r'enqueued=(\d+)', line)
            info[cur]['enqueued'] = int(m4.group(1)) if m4 else None
    return info


def spearman(x, y):
    pairs = [(a, b) for a, b in zip(x, y) if a is not None and b is not None and not math.isnan(a) and not math.isnan(b)]
    if len(pairs) < 8:
        return float('nan')

    def rank(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r, i = [0.0] * len(v), 0
        while i < len(v):
            j = i
            while j + 1 < len(v) and v[order[j + 1]] == v[order[i]]:
                j += 1
            for k in range(i, j + 1):
                r[order[k]] = (i + j) / 2 + 1
            i = j + 1
        return r
    rx, ry = rank([p[0] for p in pairs]), rank([p[1] for p in pairs])
    mx, my = statistics.mean(rx), statistics.mean(ry)
    sxy = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    sxx, syy = sum((a - mx) ** 2 for a in rx), sum((b - my) ** 2 for b in ry)
    return sxy / math.sqrt(sxx * syy) if sxx and syy else float('nan')


def fit_offset(takes):
    """epoch - monotonic, from the takes with >= 5 lost frames; seeded by label uptime and the start line."""
    fits, seeds = [], []
    for t in takes:
        tk, inf = t['tk'], t['info']
        hh, mm, ss = map(int, inf['start'].split(':'))
        t0 = tk[0]['t']
        sod = (t0 + 3600 * UTC_OFFSET) % 86400  # local time of day (CET by default)
        seed = t0 - (sod - (hh * 3600 + mm * 60 + ss)) - (inf['uptime'] + 23.5)  # label line ~23 s before start
        seeds.append(seed)
        inc = [(tk[i]['t'], tk[i]['dropped'] - tk[i - 1]['dropped']) for i in range(1, len(tk))
               if tk[i].get('dropped') is not None and tk[i - 1].get('dropped') is not None]
        losses = [(f['ts'], f['lost']) for f in t['frames'] if f.get('lost')]
        if sum(v for _, v in inc) < 5 or not losses:
            continue
        best = max(((sum(min(v, sum(n for ts, n in losses if te - 1.6 - (seed + d / 10) <= ts < te - (seed + d / 10)))
                         for te, v in inc if v > 0), seed + d / 10) for d in range(-80, 81)))
        fits.append(best[1])
    return (med(fits), fits) if fits else (med(seeds), [])


def main():
    takes = []
    for take, lib in TAKES:
        info = read_out(take)
        for p in sorted(info, key=lambda x: int(x[1:])):
            lpath, tpath = os.path.join(RAW, f'{lib}-{p}.log'), os.path.join(RAW, f'take-{PREFIX}-{take}-{p}.log')
            if not (os.path.exists(lpath) and os.path.exists(tpath)):
                print(f'skipping {take}-{p}: missing {lpath if not os.path.exists(lpath) else tpath}')
                continue
            frames, rawstats = parse_lib(lpath)
            inf = info[p]
            inf['secs'] = inf['secs'] or 180
            nominal = inf.get('fps_set', 25.0)
            inf['delivered'] = inf['enqueued'] if inf['enqueued'] is not None else nominal * inf['secs'] - inf['lost']
            takes.append({'name': f'{take}-{p}', 'frames': frames, 'rawstats': rawstats, 'tk': parse_take(tpath), 'info': inf})
    if not takes:
        sys.exit('no take with both logs')
    fitted, fits = fit_offset([t for t in takes if 'clock_off' not in t['info']]) if any('clock_off' not in t['info'] for t in takes) else (None, [])
    for t in takes:
        if 'clock_off' in t['info']:
            t['off'], how = t['info']['clock_off'], 'clock pair at record_start'
        else:
            t['off'], how = fitted, ('fitted on losses' if fits else 'seeded from uptime (a few s off)')
        print(f'clock offset {t["name"]}: epoch - monotonic = {t["off"]:.2f} s ({how})')
    if fits:
        print(f'  loss fits around the common value: {", ".join(f"{x - fitted:+.1f}" for x in fits)} s')
    for t in takes:
        t0 = t['tk'][0]['t'] - t['off']
        t['lo'], t['hi'] = t0 + 5, t0 + t['info']['secs'] - 2  # recording seconds 5 .. end - 2
        t['jobs'] = sorted([f for f in t['frames'] if 'done_ts' in f and 'sig' in f and t['lo'] <= f['start'] < t['hi']],
                           key=lambda f: f['start'])
        t['swaps'] = sorted((f['img'], f['cfg']) for f in t['frames'] if 'cfg' in f)

    print('\n1. stage medians, recording seconds 5 .. end - 2 (ms)')
    print(f'  {"take":9s} {"lost":>4s} {"swap":>5s} {"stats":>5s} {"queue":>6s} {"S1":>4s} {"S2":>5s} {"S2p90":>5s} {"S3":>5s} {"S4":>4s} {"cycle":>5s}')
    for t in takes:
        J = t['jobs']
        sw = [(b - a) * 1e3 for a, b in t['swaps'] if t['lo'] <= a < t['hi']]
        rs = [v for ts, v in t['rawstats'] if t['lo'] <= ts < t['hi']]
        s2 = [(f['done_ts'] - f['start']) * 1e3 for f in J]
        s4 = [(b['sig'] - a['done']) * 1e3 for a, b in zip(J, J[1:]) if b['sig'] >= a['done']]
        print(f'  {t["name"]:9s} {t["info"]["lost"]:4d} {med(sw):5.1f} {med(rs):5.1f} {med([(f["sig"] - f["img"]) * 1e3 for f in J]):6.1f} '
              f'{med([(f["start"] - f["sig"]) * 1e3 for f in J]):4.1f} {med(s2):5.1f} {q(s2, .9):5.1f} '
              f'{med([(f["done"] - f["done_ts"]) * 1e3 for f in J]):5.2f} {med(s4):4.1f} '
              f'{med([(b["start"] - a["start"]) * 1e3 for a, b in zip(J, J[1:])]):5.1f}')

    SW = [(0, 0.5), (0.5, 3), (3, 6), (6, 1e9)]
    SL = [(0, 2), (2, 16), (16, 1e9)]
    lab = lambda a, b, u: f'{a:g}-{b:g} {u}' if b < 1e9 else f'>{a:g} {u}'
    pool = {}
    print('\n2. median S2 (ms) [n]: rows = ms of the job overlapped by another frame\'s swap, columns = slack')
    print(f'  {"take":9s} {"swap overlap":12s}' + ''.join(f'{"slack " + lab(a, b, "ms"):>18s}' for a, b in SL))
    for t in takes:
        swi = [a for a, _ in t['swaps']]
        cells = {}
        for prev, f in zip(t['jobs'], t['jobs'][1:]):
            s, d = f['start'], f['done_ts']
            ov = sum(max(0.0, min(b, d) - max(a, s)) for a, b in t['swaps'][max(0, bisect_left(swi, s - 0.05)):bisect_left(swi, d)]) * 1e3
            slack = (s - prev['done']) * 1e3
            key = (next(i for i, (a, b) in enumerate(SW) if a <= ov < b), next(j for j, (a, b) in enumerate(SL) if a <= slack < b))
            cells.setdefault(key, []).append((d - s) * 1e3)
            pool.setdefault(key, []).append((d - s) * 1e3)
        for i, (a, b) in enumerate(SW):
            print(f'  {t["name"] if i == 0 else "":9s} {lab(a, b, "ms"):12s}' + ''.join(
                (f'{med(cells[(i, j)]):6.1f} [{len(cells[(i, j)]):5d}]' if (i, j) in cells else '-').rjust(18) for j in range(len(SL))))
    for i, (a, b) in enumerate(SW):
        print(f'  {"pooled" if i == 0 else "":9s} {lab(a, b, "ms"):12s}' + ''.join(
            (f'{med(pool[(i, j)]):6.1f} [{len(pool[(i, j)]):5d}]' if (i, j) in pool else '-').rjust(18) for j in range(len(SL))))

    print('\n3. exposure fixed at the job\'s start: exposed = a swap is running at the start or begins within 2 ms;')
    print('   unexposed = none running and the next begins >= 15 ms after the start. Median S2 (p25-p75) [n]')
    pool3 = {}
    for t in takes:
        swi = [a for a, _ in t['swaps']]
        line = f'  {t["name"]:9s}'
        for name3, (slo, shi) in (('queued (slack < 2)', (0, 2)), ('idle (slack >= 16)', (16, 1e9))):
            ex, un = [], []
            for prev, f in zip(t['jobs'], t['jobs'][1:]):
                s = f['start']
                if not slo <= (s - prev['done']) * 1e3 < shi:
                    continue
                k = bisect_left(swi, s - 0.03)
                running = any(a <= s < b for a, b in t['swaps'][max(0, k - 2):k + 1])
                nxt = next((a for a, _ in t['swaps'][k:k + 3] if a >= s), None)
                v = (f['done_ts'] - s) * 1e3
                if running or (nxt is not None and nxt - s <= 0.002):
                    ex.append(v)
                elif nxt is not None and nxt - s >= 0.015:
                    un.append(v)
            pool3.setdefault(name3, ([], []))[0].extend(ex)
            pool3[name3][1].extend(un)
            line += f'  {name3}: ex {med(ex):5.1f} [{len(ex):4d}] un {med(un):5.1f} [{len(un):4d}]'
        print(line)
    for name3, (ex, un) in pool3.items():
        print(f'  pooled {name3}: exposed {med(ex):.1f} ({q(ex, .25):.1f}-{q(ex, .75):.1f}) [{len(ex)}], '
              f'unexposed {med(un):.1f} ({q(un, .25):.1f}-{q(un, .75):.1f}) [{len(un)}], difference {med(ex) - med(un):+.1f} ms')

    print('\n4. idle-regime phase: in jobs that found the pipeline idle (slack >= 16 ms), dequeue -> job start and job start ->')
    print('   the next frame\'s dequeue (where its swap begins); share of all jobs at least that long; share of queued jobs')
    for t in takes:
        imgs = sorted(f['img'] for f in t['frames'])
        a2s, s2n, queued = [], [], 0
        for prev, f in zip(t['jobs'], t['jobs'][1:]):
            slack = (f['start'] - prev['done']) * 1e3
            queued += slack < 2
            if slack >= 16:
                a2s.append((f['start'] - f['img']) * 1e3)
                k = bisect_left(imgs, f['start'])
                if k < len(imgs):
                    s2n.append((imgs[k] - f['start']) * 1e3)
        thr = med(s2n)
        s2 = [(f['done_ts'] - f['start']) * 1e3 for f in t['jobs']]
        print(f'  {t["name"]:9s} idle jobs {len(a2s):5d}  dequeue->start {med(a2s):6.1f}  start->next dequeue {thr:5.1f}  '
              f'jobs >= that {sum(x >= thr for x in s2) / len(s2):4.2f}  queued {queued / len(s2):4.2f}  lost {t["info"]["lost"]}')

    print('\n5. Spearman rho, per-second median S2 against the 1 Hz counters (recording seconds 3 .. end - 1)')
    keys = ['pgsteal_kswapd', 'pgmigrate_success', 'compact_isolated', 'kswapd_low_wmark_hit_quickly', 'nvme_writes',
            'psi_some', 'mem_MemFree', 'mem_Dirty', 'mem_Writeback', 'boost', 'cam_run', 'rec_run', 'lost']
    rate = {'pgsteal_kswapd', 'pgmigrate_success', 'compact_isolated', 'kswapd_low_wmark_hit_quickly', 'nvme_writes', 'psi_some'}
    table, pooled = {k: [] for k in keys}, {k: ([], []) for k in keys}
    for t in takes:
        tk, J = t['tk'], t['jobs']
        starts = [f['start'] for f in J]
        last = tk[-1].get('thr', {})
        cam = t['info'].get('camtid')
        xs, ys = [], {k: [] for k in keys}
        for i in range(3, min(len(tk), t['info']['secs'] - 1)):
            a, b = tk[i - 1], tk[i]
            fr = J[bisect_left(starts, a['t'] - t['off']):bisect_left(starts, b['t'] - t['off'])]
            if not fr:
                continue
            dt = b['t'] - a['t']
            xs.append(med([(f['done_ts'] - f['start']) * 1e3 for f in fr]))
            ta, tb = a.get('thr', {}), b.get('thr', {})
            for k in keys:
                if k in rate:
                    ys[k].append((b[k] - a[k]) / dt if k in a and k in b else None)
                elif k == 'cam_run':
                    ys[k].append((tb[cam][1] - ta[cam][1]) / dt / 1e6 if cam in ta and cam in tb else None)
                elif k == 'rec_run':
                    ys[k].append(sum(tb[x][1] - ta[x][1] for x in tb if x in ta and x not in last and tb[x][0] == 'apertar-core') / dt / 1e6)
                elif k == 'lost':
                    ys[k].append(sum(f.get('lost', 0) for f in fr))
                else:
                    ys[k].append(b.get(k))
        for k in keys:
            table[k].append(spearman(xs, ys[k]))
            pooled[k][0].extend(xs)
            pooled[k][1].extend(ys[k])
    print(f'  {"counter":30s}' + ''.join(f'{t["name"]:>9s}' for t in takes) + f'{"pooled":>9s}')
    for k in keys:
        print(f'  {k:30s}' + ''.join(f'{r:9.2f}' if not math.isnan(r) else f'{"-":>9s}' for r in table[k]) + f'{spearman(*pooled[k]):9.2f}')

    print('\n6. CPU time per delivered frame (ms): CameraManager (libcamera\'s thread) and Core\'s recording-time threads')
    print('   (the threads that exit at record stop: probably 1 copy thread, 4 writers, the sync thread and two small ones)')
    for t in takes:
        tk = t['tk']
        cam, last = t['info'].get('camtid'), tk[-1].get('thr', {})
        end = min(t['info']['secs'], len(tk) - 1)
        a, b = tk[4]['thr'], tk[end]['thr']
        dt = tk[end]['t'] - tk[4]['t']
        fps = t['info']['delivered'] / t['info']['secs']
        camr = (b[cam][1] - a[cam][1]) / dt / 1e6
        rec = sorted(((b[x][1] - a[x][1]) / dt / 1e6 for x in b if x in a and x not in last and b[x][0] == 'apertar-core'), reverse=True)
        print(f'  {t["name"]:9s} lost {t["info"]["lost"]:4d}  fps {fps:4.1f}  CameraManager {camr / fps:5.1f}  recording threads '
              f'{sum(rec) / fps:5.1f} (largest {rec[0] / fps:4.1f}, next four {sum(rec[1:5]) / fps:5.1f})  cores used {(camr + sum(rec)) / 1000:4.2f}')


if __name__ == '__main__':
    main()
