#!/usr/bin/env python3
"""measured_limits.py: the fps each NVMe mode held, from the take records only (nothing derived), by lever state.

  python3 measured_limits.py [--run ../../nvme-campaign/run-20261110] [--out ../measured-limits.md]

For each cell (mode, compression, Log) at the reference levers (TDN off, phase lock off, WebUI client on, audio on, aids on,
cDNG, split 5000) it takes the LONGEST duration at which any take was clean, and gives the highest clean fps at that
duration, the lowest fps that failed at that duration or shorter, and every take behind them. Tiers: 30, 15, 5, 3, 1 minute
(a take counts for the tier its length reaches). This is the "longest measured duration" rule: a cell never claims 30 minutes
it did not run. The same is done for each non-reference lever state, to show what each lever costs.
Input: <run>/results.csv, which is what the runner's ingest writes from every take (run it after pulling a night).
"""
import argparse
import csv
import collections
import os
import re

TIERS = ((1790, 30), (890, 15), (290, 5), (170, 3), (55, 1))
CLEAN = ('pass_', 'ab_clean')


def tier(sec):
    for lim, m in TIERS:
        if sec >= lim:
            return m
    return 0


def lever_state(r):
    cid = r.get('cfg_id', '')
    aud = 'aud0' not in cid
    aids = 'aids0' not in cid
    return (r.get('tdn') == 'True', r.get('lock') == 'True', r.get('web') == 'True', aud, aids)


def cell_key(r):
    return (r['mode'], r['comp'], r['log'] == 'True')


def main():
    ap = argparse.ArgumentParser()
    here = os.path.dirname(os.path.abspath(__file__))
    ap.add_argument('--run', default=os.path.join(here, '../../nvme-campaign/run-20261110'))
    ap.add_argument('--out', default=os.path.join(here, '../measured-limits.md'))
    a = ap.parse_args()
    rows = []
    for r in csv.DictReader(open(os.path.join(a.run, 'results.csv'))):
        if r.get('format', 'cdng') != 'cdng' or r.get('media_class') not in ('pi-nvme', ''):
            continue
        if r.get('verdict') in ('stop', 'skip', 'void') or not r.get('fps') or not r.get('seconds'):
            continue
        if r.get('outcome') in ('setup_mismatch', 'record_start_failed', 'fault', 'stopped_by_signal', 'void'):
            continue
        try:
            r['_fps'] = float(r['fps'])
            r['_sec'] = float(r['seconds'])
        except ValueError:
            continue
        r['_clean'] = r['outcome'].startswith(CLEAN)
        r['_min'] = tier(r['_sec'])
        rows.append(r)
    ref = (False, False, True, True, True)
    by = collections.defaultdict(list)
    for r in rows:
        by[(cell_key(r), lever_state(r))].append(r)
    out = ['# Measured limits per cell (NVMe, from the take records only)', '',
           'Source: `results.csv` of the NVMe run folder (%d takes counted). Reference levers: TDN off, phase lock off, WebUI client on, audio on, '
           'aids on, split 5000, cDNG. "Longest measured" = the longest duration at which any take of the cell was clean; the fps is the highest '
           'clean fps at that duration or longer. The next column lists the higher fps that were tried and how long each stayed clean before its first drop. A take shorter than '
           'its tier is not counted for it.' % len(rows), '',
           '| Mode | Compression | Log | Longest measured clean | Highest clean fps | Higher fps: how long it stayed clean (best of its takes) | Takes behind it |',
           '| --- | --- | --- | --- | --- | --- | --- |']
    cells = sorted({k[0] for k in by if k[1] == ref})
    table = {}
    for ck in cells:
        rs = by[(ck, ref)]
        clean = [r for r in rs if r['_clean']]
        if not clean:
            fails = sorted(r['_fps'] for r in rs)
            out.append('| %s | %s | %s | none clean | - | %g (shortest failure %.0f s) | %d |' % (ck[0], ck[1], 'on' if ck[2] else '', fails[0], min(r['_sec'] for r in rs), len(rs)))
            table[ck] = None
            continue
        top = max(r['_min'] for r in clean)
        best = max(r['_fps'] for r in clean if r['_min'] == top)
        # the highest clean fps at the top tier, and the failures at fps above it at the same or longer length
        fail = sorted(r['_fps'] for r in rs if not r['_clean'] and r['_fps'] > best and r['_min'] >= top)
        shorter = max((r['_fps'] for r in clean if r['_min'] < top and r['_fps'] > best), default=None)
        def until(r):
            try:
                return float(r.get('first_drop_s') or r['_sec'])
            except ValueError:
                return r['_sec']
        above = collections.defaultdict(float)
        for r in rs:
            if not r['_clean'] and r['_fps'] > best:
                above[r['_fps']] = max(above[r['_fps']], until(r))
        fail_txt = ', '.join('%g: clean %s' % (f, ('%.1f min' % (above[f] / 60)) if above[f] >= 60 else '%.0f s' % above[f]) for f in sorted(above)[:4])
        out.append('| %s | %s | %s | %d min | %g%s | %s | %d clean, %d failed |' % (
            ck[0], ck[1], 'on' if ck[2] else '', top, best,
            (' (%g held only %s)' % (shorter, ', '.join('%d min' % m for m in sorted({r['_min'] for r in clean if r['_fps'] == shorter}))) if shorter else ''),
            fail_txt or 'not tried above', len(clean), len(rs) - len(clean)))
        table[ck] = (top, best)
    out += ['', '## Each lever against the reference (same cell, one lever away)', '',
            '| Mode | Compression | Log | Lever state (tdn, lock, web, audio, aids) | Longest clean | Highest clean fps | Reference |', '| --- | --- | --- | --- | --- | --- | --- |']
    for (ck, lv), rs in sorted(by.items(), key=lambda kv: (kv[0][0], kv[0][1])):
        if lv == ref or ck not in table:
            continue
        clean = [r for r in rs if r['_clean']]
        if not clean:
            continue
        top = max(r['_min'] for r in clean)
        best = max(r['_fps'] for r in clean if r['_min'] == top)
        names = ['TDN' if lv[0] else '', 'lock' if lv[1] else '', 'no web' if not lv[2] else '', 'no audio' if not lv[3] else '', 'no aids' if not lv[4] else '']
        out.append('| %s | %s | %s | %s | %d min | %g | %s |' % (ck[0], ck[1], 'on' if ck[2] else '', ' '.join(n for n in names if n) or '-', top, best,
                   ('%d min, %g fps' % table[ck]) if table.get(ck) else '-'))
    open(a.out, 'w').write('\n'.join(out) + '\n')
    print('\n'.join(out[:60]))
    print('written', a.out)


if __name__ == '__main__':
    main()
