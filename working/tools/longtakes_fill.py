#!/usr/bin/env python3
"""longtakes_fill.py: read a long-take run (results.csv + longtakes.db) for what happened INSIDE each take.

The runner records one row per take and a 1 Hz sample series (temperatures, CPU, RAM, free space). This tool turns the
free-space series into the writers' progress and reconstructs the write buffer's fill over the take:

  drain MB/s   = bytes the writers took from the buffer per second (exFAT allocates clusters at write() time, so the
                 free-space drop follows the writers, not the drive);
  implied queue = frames delivered (fps x t) minus frames written, as a share of the RAM budget (the stats line's
                 queue_budget). Negative values are the file-size estimate's error (~1-3 %): read the shape, not the sign.

It also sorts every buffer_full take into a regime, reads the stop time and the "nothing was written" message from the
journal, prints Core's CPU per window with the busiest thread, and derives the per-directory-entry cost c from the slope
of Core's CPU over a long take (assumes the slope is the exFAT create walk: 5 entries per frame file, see the plan).

  python3 -I longtakes_fill.py RUN_DIR                    # the four tables
  python3 -I longtakes_fill.py RUN_DIR --tail 150 --step 5   # plus the last 150 s of every failed take at 5 s steps
  python3 -I longtakes_fill.py RUN_DIR --csv windows.csv  # the per-window rows as CSV

Labels: everything here is derived from the runner's samples; nothing is measured anew.
"""
import argparse, collections, csv, datetime as dt, os, re, sqlite3, sys

GIB = 2 ** 30


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def load(run):
    rows = list(csv.DictReader(open(os.path.join(run, 'results.csv'))))
    con = sqlite3.connect(os.path.join(run, 'longtakes.db'))
    stats = {}
    for tid, k, v in con.execute('select take_id, k, v from stats'):
        stats.setdefault(tid, {})[k] = v
    journal = collections.defaultdict(list)
    for tid, t, line in con.execute("select take_id, t_unix, line from journal where line like '%ApertarCore%'"):
        journal[tid].append((t, line))
    return rows, con, stats, journal


def samples(con, tid):
    return con.execute('select t_s, free_gb, mem_avail_mb, pi_c, cpu_pct, core_cpu_pct, core_top_thread, state '
                       'from samples where take_id=? order by t_s', (tid,)).fetchall()


def file_mb(r):
    files = num(r.get('files')) or 0
    gb = num(r.get('gb_written')) or 0
    return gb * 1000 / files if files else 0.0


def idle_gaps(rows):
    """Seconds between the previous take's end (plus ~25 s of stop and clean-up) and each take's start."""
    P = lambda s: dt.datetime.strptime(s, '%Y-%m-%d %H:%M:%S')
    out, prev_end = {}, None
    for r in sorted([x for x in rows if x.get('started') and num(x.get('seconds')) is not None and x.get('take_id')],
                    key=lambda x: x['started']):
        st = P(r['started'])
        out[r['take_id']] = (st - prev_end).total_seconds() if prev_end else None
        prev_end = st + dt.timedelta(seconds=num(r['seconds']) + 25)
    return out


def stop_info(journal, tid):
    stop = stall = safety = None
    for t, line in journal.get(tid, []):
        m = re.search(r'recorder stop time: ([\d.]+)s', line)
        if m: stop = float(m.group(1))
        if 'no frame written' in line: stall = True
        if 'safety stop at' in line: safety = t
    return stop, bool(stall), safety


def regimes(rows, con, stats, journal, out):
    print('=== buffer_full takes: need vs drain, budget in seconds of input, stop time, regime ===')
    print('  slow  = the writers never kept up (buffer full within ~3 budgets of input)')
    print('  late  = drain equal to the need for minutes, then the buffer filled')
    print('  stall-msg = Core logged "nothing was written for 5 s" (always at the stop, in this run)')
    counts = collections.Counter()
    for r in sorted([x for x in rows if x.get('outcome') == 'buffer_full'], key=lambda x: x['started']):
        tid = r['take_id']; fps = num(r['fps']); fmb = file_mb(r); need = fps * fmb
        budget = num(stats.get(tid, {}).get('queue_budget')) or 0
        bsec = budget / (need * 1e6) if need else 0
        sam = samples(con, tid)
        secs = num(r['seconds']) or 0
        drain = (sam[0][1] - sam[-1][1]) * GIB / 1e6 / max(sam[-1][0] - sam[0][0], 1) if len(sam) > 1 else 0
        stop, stall, _ = stop_info(journal, tid)
        regime = 'slow' if secs < 3 * bsec + 20 and drain < 0.985 * need else ('stall-msg' if stall else 'late')
        counts[regime] += 1
        out.append({'take_id': tid, 'kind': 'regime', 'seconds': secs, 'need_mbps': round(need, 1), 'drain_mbps': round(drain, 1),
                    'budget_s': round(bsec, 1), 'stop_s': stop, 'regime': regime, 'files': r.get('files')})
        print('%-58s %6.0fs need %6.1f drain %6.1f MB/s budget %5.1f s stop %5s s files %6s  %s' % (
            tid[:58], secs, need, drain, bsec, ('%.1f' % stop) if stop else '-', r.get('files'), regime))
    print(dict(counts))
    print()


def fill_curves(rows, con, stats, journal, gaps, window, min_seconds, out):
    print('=== takes >= %d s: drain MB/s / implied queue %% of budget / Core CPU %% / Pi C per %d s window ===' % (min_seconds, window))
    for r in sorted([x for x in rows if (num(x.get('seconds')) or 0) >= min_seconds], key=lambda x: x['started']):
        tid = r['take_id']; fps = num(r['fps']); fmb = file_mb(r); need = fps * fmb
        st = stats.get(tid, {}); budget = num(st.get('queue_budget')) or 0
        sam = samples(con, tid)
        if not sam:
            continue
        t0, free0 = sam[0][0], sam[0][1]
        gap = gaps.get(tid)
        print('%-58s %-11s %5.0fs file %4.2f MB need %5.1f MB/s budget %4.0f MiB (%4.1f s) idle before %s min mem0 %s MB' % (
            tid[:58], r['outcome'], num(r['seconds']), fmb, need, budget / 2 ** 20, budget / (need * 1e6) if need else 0,
            ('%.0f' % (gap / 60)) if gap is not None else '-', sam[0][2]))
        marks = list(range(window, int(sam[-1][0]) + 1, window))
        if sam[-1][0] - (marks[-1] if marks else 0) > 60:
            marks.append(int(sam[-1][0]))
        prev_t, prev_free, cells = t0, free0, []
        for m in marks:
            s = max([x for x in sam if x[0] <= m], key=lambda x: x[0])
            t, free = s[0], s[1]
            drain = (prev_free - free) * GIB / 1e6 / max(t - prev_t, 1)
            delivered = fps * (t - t0) * fmb * 1e6
            written = (free0 - free) * GIB
            q = 100 * (delivered - written) / budget if budget else 0
            cc = [x[5] for x in sam if prev_t < x[0] <= t and x[5] is not None]
            tops = collections.Counter((x[6] or '').split(':')[0] for x in sam if prev_t < x[0] <= t and x[6])
            top = tops.most_common(1)[0][0] if tops else ''
            cells.append('%4ds: %5.1f/%4.0f%%/%s/%2.0fC' % (t, drain, q, ('%3.0f' % (sum(cc) / len(cc))) if cc else '  -', s[3] or 0))
            out.append({'take_id': tid, 'kind': 'window', 't_s': t, 'drain_mbps': round(drain, 1), 'queue_pct': round(q, 1),
                        'core_cpu_pct': round(sum(cc) / len(cc), 1) if cc else '', 'top_thread': top, 'pi_c': s[3], 'mem_avail_mb': s[2]})
            prev_t, prev_free = t, free
        print('      ' + ' | '.join(cells))
        print('      peak_queue=%s bytes_peak/budget=%.0f%% enqueued=%s files=%s mem end=%s' % (
            st.get('peak_queue'), 100 * (num(st.get('queue_bytes_peak')) or 0) / budget if budget else 0, st.get('enqueued'),
            r.get('files'), sam[-1][2]))
    print()


def cpu_slopes(rows, con, min_seconds, entries, out):
    """Core CPU (fraction of one core) against time while recording; slope -> c = slope / (fps^2 x entries)."""
    print('=== Core CPU over the take (fraction of one core) and the derived per-entry cost c ===')
    print('  model: extra CPU(t) = fps x [c x entries x N(t)], N(t) = fps x t  ->  slope = fps^2 x c x entries')
    cs = []
    for r in sorted([x for x in rows if (num(x.get('seconds')) or 0) >= min_seconds], key=lambda x: x['started']):
        tid = r['take_id']; fps = num(r['fps'])
        pts = [(x[0], x[5] / 100.0) for x in samples(con, tid) if x[5] is not None and x[7] == 'rec' and x[0] > 20]
        if len(pts) < 100:
            continue
        n = len(pts); mx = sum(p[0] for p in pts) / n; my = sum(p[1] for p in pts) / n
        sxx = sum((p[0] - mx) ** 2 for p in pts)
        slope = sum((p[0] - mx) * (p[1] - my) for p in pts) / sxx if sxx else 0
        icpt = my - slope * mx
        c_ns = slope / (fps * fps * entries) * 1e9 if fps else 0
        cs.append(c_ns)
        out.append({'take_id': tid, 'kind': 'cpu_slope', 'cpu_at_start': round(icpt, 3), 'cpu_slope_per_s': slope, 'c_ns_per_entry': round(c_ns, 1)})
        print('%-58s fps %4.0f  CPU %4.2f -> %4.2f over %4.0f s  slope %.2e /s  c = %5.0f ns per entry' % (
            tid[:58], fps, icpt, icpt + slope * pts[-1][0], pts[-1][0], slope, c_ns))
    if cs:
        cs.sort()
        print('  median c = %.0f ns per entry over %d takes (derived; assumes the whole slope is the directory walk)' % (cs[len(cs) // 2], len(cs)))
    print()


def budgets(con):
    print('=== RAM budget per take (MiB) against MemAvailable, in order ===')
    seq = con.execute("select take_id, line from journal where line like '%ram budget%' order by t_unix").fetchall()
    vals = []
    for tid, line in seq:
        m = re.search(r'ram budget (\d+) MiB \(MemAvailable (\d+) MiB', line)
        if m:
            vals.append((tid, int(m.group(1)), int(m.group(2))))
    if vals:
        b = sorted(v[1] for v in vals)
        print('  %d takes; budget min %d, median %d, max %d MiB; MemAvailable %d..%d MiB' % (
            len(vals), b[0], b[len(b) // 2], b[-1], min(v[2] for v in vals), max(v[2] for v in vals)))
        for tid, bud, mem in vals[::max(1, len(vals) // 12)]:
            print('  %-58s %5d MiB  (MemAvailable %5d)' % (tid[:58], bud, mem))
    print()


def tails(rows, con, stats, tail, step):
    print('=== drain MB/s per %d s over the last %d s of each buffer_full take >= 240 s (implied queue %% after the slash when > 5) ===' % (step, tail))
    for r in sorted([x for x in rows if x.get('outcome') == 'buffer_full' and (num(x.get('seconds')) or 0) >= 240], key=lambda x: x['started']):
        tid = r['take_id']; fps = num(r['fps']); fmb = file_mb(r); need = fps * fmb
        budget = num(stats.get(tid, {}).get('queue_budget')) or 0
        sam = samples(con, tid)
        if not sam:
            continue
        t0, free0, tend = sam[0][0], sam[0][1], sam[-1][0]
        prev, cells = None, []
        for m in range(int(max(0, tend - tail)), int(tend) + 1, step):
            cands = [x for x in sam if x[0] <= m]
            if not cands:
                continue
            s = max(cands, key=lambda x: x[0])
            if prev is not None and s[0] > prev[0]:
                d = (prev[1] - s[1]) * GIB / 1e6 / (s[0] - prev[0])
                q = 100 * (fps * (s[0] - t0) * fmb * 1e6 - (free0 - s[1]) * GIB) / budget if budget else 0
                cells.append('%4d:%4.0f%s' % (s[0], d, ('/%d%%' % q) if q > 5 else ''))
            prev = s
        print('%-58s %5.0fs need %5.1f budget %4.1f s' % (tid[:58], num(r['seconds']), need, budget / (need * 1e6) if need else 0))
        print('    ' + ' '.join(cells))
    print()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('run')
    ap.add_argument('--window', type=int, default=300)
    ap.add_argument('--min-seconds', type=int, default=600)
    ap.add_argument('--entries', type=int, default=5, help='exFAT directory entries per frame file (33-char names: 5)')
    ap.add_argument('--tail', type=int, default=0, help='also print the last N seconds of every failed take')
    ap.add_argument('--step', type=int, default=5)
    ap.add_argument('--csv', default='')
    a = ap.parse_args()
    rows, con, stats, journal = load(a.run)
    out = []
    regimes(rows, con, stats, journal, out)
    fill_curves(rows, con, stats, journal, idle_gaps(rows), a.window, a.min_seconds, out)
    cpu_slopes(rows, con, a.min_seconds, a.entries, out)
    budgets(con)
    if a.tail:
        tails(rows, con, stats, a.tail, a.step)
    if a.csv:
        keys = sorted({k for o in out for k in o})
        with open(a.csv, 'w', newline='') as f:
            w = csv.DictWriter(f, keys)
            w.writeheader()
            w.writerows(out)
        print('wrote', a.csv, len(out), 'rows')


if __name__ == '__main__':
    main()
