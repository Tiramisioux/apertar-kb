#!/usr/bin/env python3
"""b1_test.py CSV [--json]: analysis of test B1 (writer vs sync), as fixed in the pre-registered plan.

Plan (verbatim): "Two blocks; extension: a third block. Block: 4 units, 2 per arm ('writer' and 'sync'), in one of
the 6 balanced orders. Unit: P1, 3 min -> P2, 3 min. Analysis (fixed in advance, all one-sided, writer > sync):
per-unit lost = P1 + P2; exact permutation test stratified by block. Attainable minimum p: 1/36 = 0.028 (2 blocks),
1/216 = 0.0046 (3). Manipulation check: pgsteal_kswapd >= 10x higher in every writer take than in every sync take,
or the run is void (the drop-in did not take). Covariate: MemFree before P1 and P2. Also reported: P1 and P2
separately per arm."

CSV header, exactly:
  block,unit,arm,P1_lost,P2_lost,P1_memfree,P2_memfree,P1_pgsteal_kswapd,P2_pgsteal_kswapd
memfree in MB; arm is writer or sync; block and unit are labels. Every block needs exactly 2 writer and 2 sync
units, otherwise the script exits non-zero without computing anything.

Statistic: T = sum of lost over the writer units (equivalent to the writer-minus-sync difference, since the total
lost is fixed under relabeling). Exact one-sided p = #(relabelings with T >= observed) / 6^blocks, enumerating the
C(4,2)=6 writer assignments of each block independently. Ties count as >= (conservative).

  python3 -I b1_test.py data.csv [--json]
  python3 -I b1_test.py --self-test

Mode --tdn: evening-3 TDN test (pre-registered, design A). Blocks of 4 units, exactly 2 with arm F (TDN off) and 2
with arm N (TDN on). Two per-unit statistics, each tested separately: "P2 queued share" = P2_queued (float 0..1) and
"losses" = P1_lost + P2_lost (integers). Hypothesis one-sided F < N. T = sum of the statistic over the F units.
Exact p = #(relabelings with T <= observed) / 6^blocks (C(4,2)=6 F assignments per block, enumerated independently;
1 or more blocks), computed with Fraction; ties count as <= (conservative; float ties for P2_queued within 1e-12).
Minimum attainable p with one block = 1/6. Output per statistic: observed T, p (fraction and decimal), and every
relabeling (which units are F) with its T, the observed one marked.
CSV header, exactly:
  block,unit,arm,P1_lost,P2_lost,P2_queued
arm is F or N; P1_lost and P2_lost are integers; P2_queued is within 0..1. Invalid input exits non-zero (2) without
computing anything.

  python3 -I b1_test.py --tdn data.csv [--json]
  python3 -I b1_test.py --tdn --self-test
"""
import argparse
import csv
import itertools
import json
import sys
from fractions import Fraction

HEADER = ['block', 'unit', 'arm', 'P1_lost', 'P2_lost', 'P1_memfree', 'P2_memfree',
          'P1_pgsteal_kswapd', 'P2_pgsteal_kswapd']
FACTOR = 10


class InputError(Exception):
    pass


def num(row, key, line):
    try:
        return float(row[key])
    except (TypeError, ValueError):
        raise InputError(f'line {line}: {key} is not a number: {row[key]!r}')


def load(path):
    with open(path, newline='') as f:
        rd = csv.DictReader(f)
        if rd.fieldnames != HEADER:
            raise InputError(f'header must be exactly: {",".join(HEADER)}\n  got: {",".join(rd.fieldnames or [])}')
        units = []
        for i, row in enumerate(rd, start=2):
            if None in row or any(v is None for v in row.values()):
                raise InputError(f'line {i}: wrong number of columns')
            units.append(parse_row(row, i))
    return units


def parse_row(row, line):
    arm = row['arm'].strip()
    if arm not in ('writer', 'sync'):
        raise InputError(f'line {line}: arm must be writer or sync, got {row["arm"]!r}')
    u = {'block': row['block'].strip(), 'unit': row['unit'].strip(), 'arm': arm}
    for k in HEADER[3:]:
        u[k] = num(row, k, line)
    return u


def validate(units):
    if not units:
        raise InputError('no data rows')
    blocks = {}
    for u in units:
        blocks.setdefault(u['block'], []).append(u)
    for b, us in blocks.items():
        w = sum(1 for u in us if u['arm'] == 'writer')
        s = sum(1 for u in us if u['arm'] == 'sync')
        if len(us) != 4 or w != 2 or s != 2:
            raise InputError(f'block {b!r}: needs exactly 2 writer and 2 sync units, found {w} writer and {s} sync '
                             f'({len(us)} units)')
    return blocks


def lost(u):
    return u['P1_lost'] + u['P2_lost']


def permutation(blocks):
    """Exact stratified permutation test. Returns dict with Fractions."""
    per_block = []
    obs = 0
    for us in blocks.values():
        vals = [lost(u) for u in us]
        sums = [sum(vals[i] for i in c) for c in itertools.combinations(range(4), 2)]
        per_block.append(sums)
        obs += sum(lost(u) for u in us if u['arm'] == 'writer')
    total = 6 ** len(blocks)
    count = sum(1 for combo in itertools.product(*per_block) if sum(combo) >= obs)
    return {'T': obs, 'count': count, 'total': total, 'p': Fraction(count, total),
            'min_p': Fraction(1, total)}


def manip_check(units):
    w = [u[k] for u in units if u['arm'] == 'writer' for k in ('P1_pgsteal_kswapd', 'P2_pgsteal_kswapd')]
    s = [u[k] for u in units if u['arm'] == 'sync' for k in ('P1_pgsteal_kswapd', 'P2_pgsteal_kswapd')]
    mw, ms = min(w), max(s)
    ok = mw > 0 if ms == 0 else mw >= FACTOR * ms
    return {'min_writer': mw, 'max_sync': ms, 'factor': FACTOR, 'pass': ok}


def stats(vals):
    return {'mean': sum(vals) / len(vals), 'min': min(vals), 'max': max(vals)}


def per_arm(units):
    out = {}
    for arm in ('writer', 'sync'):
        us = [u for u in units if u['arm'] == arm]
        d = {'n': len(us)}
        for p in ('P1', 'P2'):
            l = [u[p + '_lost'] for u in us]
            d[p + '_lost_total'] = sum(l)
            d[p + '_lost_mean'] = sum(l) / len(l)
            d[p + '_memfree'] = stats([u[p + '_memfree'] for u in us])
        out[arm] = d
    return out


def analyse(units):
    blocks = validate(units)
    return {'units': units, 'n_blocks': len(blocks), 'permutation': permutation(blocks),
            'manipulation': manip_check(units), 'per_arm': per_arm(units)}


def g(x):
    return f'{x:g}'


def report(r):
    L = []
    L.append('per-unit')
    L.append(f'{"block":<8}{"unit":<8}{"arm":<8}{"P1":>8}{"P2":>8}{"lost":>8}{"MemFree P1":>12}{"MemFree P2":>12}')
    for u in r['units']:
        L.append(f'{u["block"]:<8}{u["unit"]:<8}{u["arm"]:<8}{g(u["P1_lost"]):>8}{g(u["P2_lost"]):>8}'
                 f'{g(lost(u)):>8}{g(u["P1_memfree"]):>12}{g(u["P2_memfree"]):>12}')
    p = r['permutation']
    L.append('')
    L.append('permutation test (one-sided, writer > sync, stratified by block)')
    L.append('statistic T = sum of lost over writer units (equivalent to writer-minus-sync difference)')
    L.append(f'observed T: {g(p["T"])}')
    L.append(f'relabelings with T >= observed: {p["count"]}')
    L.append(f'total relabelings: {p["total"]}')
    L.append(f'p: {p["p"]} = {float(p["p"]):.4f}')
    L.append(f'minimum attainable p: {p["min_p"]} = {float(p["min_p"]):.4f}')
    m = r['manipulation']
    L.append('')
    L.append('manipulation check (pgsteal_kswapd)')
    L.append(f'min over writer takes: {g(m["min_writer"])}')
    L.append(f'max over sync takes: {g(m["max_sync"])}')
    L.append(f'required: min writer >= {m["factor"]} x max sync' + (' (max sync is 0: min writer > 0)' if m['max_sync'] == 0 else ''))
    L.append('PASS' if m['pass'] else 'FAIL')
    if not m['pass']:
        L.append('run VOID')
    L.append('')
    L.append('per arm')
    for arm, d in r['per_arm'].items():
        L.append(f'{arm} (n={d["n"]})')
        for pp in ('P1', 'P2'):
            L.append(f'  {pp} lost: total {g(d[pp + "_lost_total"])}, mean {g(d[pp + "_lost_mean"])}')
        for pp in ('P1', 'P2'):
            s = d[pp + '_memfree']
            L.append(f'  MemFree before {pp} (MB): mean {g(s["mean"])}, min {g(s["min"])}, max {g(s["max"])}')
    return '\n'.join(L)


def to_json(r):
    p = r['permutation']
    out = dict(r)
    out['permutation'] = {'T': p['T'], 'count': p['count'], 'total': p['total'], 'p': float(p['p']),
                          'p_fraction': str(p['p']), 'min_p': float(p['min_p']), 'min_p_fraction': str(p['min_p'])}
    return json.dumps(out, indent=2)


# ---- TDN mode (evening 3) ----

TDN_HEADER = ['block', 'unit', 'arm', 'P1_lost', 'P2_lost', 'P2_queued']
TDN_TOL = 1e-12
TDN_STATS = (('P2_queued', 'P2 queued share', lambda u: u['P2_queued']),
             ('losses', 'losses (P1_lost + P2_lost)', lambda u: u['P1_lost'] + u['P2_lost']))


def tdn_parse_row(row, line):
    arm = row['arm'].strip()
    if arm not in ('F', 'N'):
        raise InputError(f'line {line}: arm must be F or N, got {row["arm"]!r}')
    u = {'block': row['block'].strip(), 'unit': row['unit'].strip(), 'arm': arm}
    for k in ('P1_lost', 'P2_lost'):
        v = num(row, k, line)
        if v != v or v in (float('inf'), float('-inf')) or v != int(v):
            raise InputError(f'line {line}: {k} must be an integer, got {row[k]!r}')
        u[k] = int(v)
    q = num(row, 'P2_queued', line)
    if not (0.0 <= q <= 1.0):  # also rejects nan
        raise InputError(f'line {line}: P2_queued must be within 0..1, got {row["P2_queued"]!r}')
    u['P2_queued'] = q
    return u


def tdn_load(path):
    with open(path, newline='') as f:
        rd = csv.DictReader(f)
        if rd.fieldnames != TDN_HEADER:
            raise InputError(f'header must be exactly: {",".join(TDN_HEADER)}\n  got: {",".join(rd.fieldnames or [])}')
        units = []
        for i, row in enumerate(rd, start=2):
            if None in row or any(v is None for v in row.values()):
                raise InputError(f'line {i}: wrong number of columns')
            units.append(tdn_parse_row(row, i))
    return units


def tdn_validate(units):
    if not units:
        raise InputError('no data rows')
    blocks = {}
    for u in units:
        blocks.setdefault(u['block'], []).append(u)
    for b, us in blocks.items():
        f = sum(1 for u in us if u['arm'] == 'F')
        n = sum(1 for u in us if u['arm'] == 'N')
        if len(us) != 4 or f != 2 or n != 2:
            raise InputError(f'block {b!r}: needs exactly 2 F and 2 N units, found {f} F and {n} N ({len(us)} units)')
        if len({u['unit'] for u in us}) != 4:
            raise InputError(f'block {b!r}: unit labels must be distinct within a block')
    return blocks


def tdn_permutation(blocks, stat):
    """Exact stratified one-sided test, F < N: p = #(T <= observed) / 6^blocks. Returns dict (Fraction p)."""
    names = list(blocks)
    per_block = []  # per block: list of (F-unit labels, sum of stat over them) for the 6 assignments
    obs = 0
    for b in names:
        us = blocks[b]
        opts = [([f'{b}/{us[i]["unit"]}' for i in c], sum(stat(us[i]) for i in c))
                for c in itertools.combinations(range(4), 2)]
        per_block.append(opts)
        obs += sum(stat(u) for u in us if u['arm'] == 'F')
    obs_f = sorted(f'{b}/{u["unit"]}' for b in names for u in blocks[b] if u['arm'] == 'F')
    rel = []
    for combo in itertools.product(*per_block):
        t = sum(c[1] for c in combo)
        fl = sorted(x for c in combo for x in c[0])
        rel.append({'F_units': fl, 'T': t, 'observed': fl == obs_f})
    total = 6 ** len(names)
    count = sum(1 for r in rel if r['T'] <= obs + TDN_TOL)
    return {'T': obs, 'count': count, 'total': total, 'p': Fraction(count, total),
            'min_p': Fraction(1, total), 'relabelings': rel}


def tdn_analyse(units):
    blocks = tdn_validate(units)
    return {'units': units, 'n_blocks': len(blocks),
            'stats': {key: tdn_permutation(blocks, fn) for key, _, fn in TDN_STATS}}


def tdn_report(r):
    L = ['TDN test (one-sided, F < N, stratified by block; T = sum over F units; p = #(T <= observed) / 6^blocks)',
         f'blocks: {r["n_blocks"]}', '', 'per-unit',
         f'{"block":<8}{"unit":<8}{"arm":<5}{"P1_lost":>9}{"P2_lost":>9}{"losses":>8}{"P2_queued":>11}']
    for u in r['units']:
        L.append(f'{u["block"]:<8}{u["unit"]:<8}{u["arm"]:<5}{u["P1_lost"]:>9}{u["P2_lost"]:>9}'
                 f'{u["P1_lost"] + u["P2_lost"]:>8}{g(u["P2_queued"]):>11}')
    for key, label, _ in TDN_STATS:
        p = r['stats'][key]
        L += ['', f'statistic: {label}', f'observed T: {g(p["T"])}',
              f'relabelings with T <= observed: {p["count"]} of {p["total"]}',
              f'p: {p["p"]} = {float(p["p"]):.4f}',
              f'minimum attainable p: {p["min_p"]} = {float(p["min_p"]):.4f}',
              'all relabelings (F units, T):']
        for i, rl in enumerate(p['relabelings'], start=1):
            L.append(f'  {i:>3}  F = {", ".join(rl["F_units"])}  T = {g(rl["T"])}' + ('  <- observed' if rl['observed'] else ''))
    return '\n'.join(L)


def tdn_to_json(r):
    out = {'units': r['units'], 'n_blocks': r['n_blocks'], 'stats': {}}
    for key, p in r['stats'].items():
        out['stats'][key] = {'T': p['T'], 'count': p['count'], 'total': p['total'], 'p': float(p['p']),
                             'p_fraction': str(p['p']), 'min_p': float(p['min_p']),
                             'min_p_fraction': str(p['min_p']), 'relabelings': p['relabelings']}
    return json.dumps(out, indent=2)


def tdn_mk(block, unit, arm, p1, p2, q):
    return {'block': block, 'unit': unit, 'arm': arm, 'P1_lost': p1, 'P2_lost': p2, 'P2_queued': q}


def tdn_block(b, vals, arms=('F', 'F', 'N', 'N')):
    """vals: 4 (losses-as-P1, queued) pairs; losses placed in P1_lost with P2_lost 0."""
    return [tdn_mk(b, f'u{i + 1}', arms[i], v[0], 0, v[1]) for i, v in enumerate(vals)]


def tdn_self_test():
    import os
    import tempfile
    fails = 0

    def case(name, ok):
        nonlocal fails
        print(f'{name}: {"PASS" if ok else "FAIL"}')
        fails += (not ok)

    def P(units, key):
        return tdn_analyse(units)['stats'][key]['p']

    lo = [(1, 0.1), (2, 0.2), (10, 0.8), (11, 0.9)]  # F units first (low), N units last (high)
    sep = tdn_block('B1', lo)
    case('(1) one block, F below N: p == 1/6 for both statistics',
         P(sep, 'losses') == Fraction(1, 6) and P(sep, 'P2_queued') == Fraction(1, 6))
    rev = tdn_block('B1', lo, arms=('N', 'N', 'F', 'F'))
    case('(2) one block, F above N: p == 1 for both statistics',
         P(rev, 'losses') == 1 and P(rev, 'P2_queued') == 1)
    tie = tdn_block('B1', [(5, 0.5), (5, 0.5), (5, 0.5), (5, 0.5)])
    r = tdn_analyse(tie)['stats']
    case('(3a) all tied: every relabeling counts as <=, p == 1',
         r['losses']['p'] == 1 and r['P2_queued']['p'] == 1 and r['losses']['count'] == 6)
    # losses F=(1,5) N=(5,9): sums over pairs: 6,6,10,10,14,14 -> observed 6; T<=6 is 2 of 6 (ties at 6 count)
    tie2 = tdn_block('B1', [(1, 0.1), (5, 0.5), (5, 0.5), (9, 0.9)], arms=('F', 'N', 'F', 'N'))
    tie2[0]['arm'], tie2[1]['arm'], tie2[2]['arm'], tie2[3]['arm'] = 'F', 'F', 'N', 'N'
    case('(3b) partial tie: F=(1,5) vs N=(5,9): T=6 ties with another relabeling, p == 2/6 (not 1/6)',
         P(tie2, 'losses') == Fraction(2, 6))
    # F = (0.1, 0.3), N = (0.2+0.1, 0.9): observed T = 0.4; the relabeling F = (0.1, 0.2+0.1) sums to 0.4000000000000001,
    # above T in floats, so it counts only through the tolerance: p = 2/6 with it, 1/6 without
    fl = tdn_block('B1', [(0, 0.1), (0, 0.3), (0, 0.2 + 0.1), (0, 0.9)])
    case('(3c) float ties within 1e-12 count as <= (0.1+0.2 vs 0.3)',
         P(fl, 'P2_queued') == Fraction(2, 6))
    two = tdn_block('B1', lo) + tdn_block('B2', lo)
    case('(4) two blocks, complete separation: p == 1/36 for both statistics',
         P(two, 'losses') == Fraction(1, 36) and P(two, 'P2_queued') == Fraction(1, 36)
         and tdn_analyse(two)['stats']['losses']['total'] == 36 and len(tdn_analyse(two)['stats']['losses']['relabelings']) == 36)
    bad = tdn_block('B1', lo, arms=('F', 'F', 'F', 'N'))
    try:
        tdn_validate(bad)
        case('(5a) block with 3 F units refused', False)
    except InputError as e:
        print(f'    message: {e}')
        case('(5a) block with 3 F units refused', True)
    d = tempfile.mkdtemp()
    path = os.path.join(d, 'bad.csv')
    with open(path, 'w') as f:
        f.write(','.join(TDN_HEADER) + '\n' + ''.join(
            f'B1,u{i + 1},{a},1,1,0.5\n' for i, a in enumerate(('F', 'F', 'F', 'N'))))
    try:
        tdn_analyse(tdn_load(path))
        case('(5b) invalid CSV (3 F units) refused end to end', False)
    except InputError:
        case('(5b) invalid CSV (3 F units) refused end to end', True)
    for name, line in (('P2_queued 1.5', 'B1,u1,F,1,1,1.5'), ('non-integer P1_lost', 'B1,u1,F,1.5,1,0.5'),
                       ('arm x', 'B1,u1,x,1,1,0.5')):
        with open(path, 'w') as f:
            f.write(','.join(TDN_HEADER) + '\n' + line + '\n')
        try:
            tdn_load(path)
            case(f'(5c) {name} refused', False)
        except InputError:
            case(f'(5c) {name} refused', True)
    os.remove(path)
    os.rmdir(d)
    print('SELF-TEST ' + ('PASS' if not fails else 'FAIL'))
    return 1 if fails else 0


# ---- self-test ----

def mk(block, unit, arm, p1, p2, kswapd):
    return {'block': block, 'unit': unit, 'arm': arm, 'P1_lost': p1, 'P2_lost': p2, 'P1_memfree': 1000.0,
            'P2_memfree': 1000.0, 'P1_pgsteal_kswapd': kswapd if arm == 'writer' else 1.0,
            'P2_pgsteal_kswapd': kswapd if arm == 'writer' else 1.0}


def synth(nblocks, separated=True, equal=False):
    units = []
    for b in range(nblocks):
        for i, arm in enumerate(('writer', 'sync', 'sync', 'writer')):
            if equal:
                lo = 5
            else:
                lo = (100 + i + 10 * b) if arm == 'writer' else (1 + i)
            units.append(mk(f'B{b + 1}', f'U{i + 1}', arm, lo, lo, 1000.0))
    return units


def self_test():
    fails = 0

    def case(name, ok):
        nonlocal fails
        print(f'{name}: {"PASS" if ok else "FAIL"}')
        fails += (not ok)

    def run(units):
        return analyse(units)

    r = run(synth(2))
    case('(a) 2 blocks, complete separation: p == 1/36', r['permutation']['p'] == Fraction(1, 36))
    r = run(synth(3))
    case('(b) 3 blocks, complete separation: p == 1/216', r['permutation']['p'] == Fraction(1, 216))
    r = run(synth(2, equal=True))
    case('(c) all-equal losses: p == 1', r['permutation']['p'] == 1)
    bad = synth(1)
    bad[1]['arm'] = 'writer'
    try:
        validate(bad)
        case('(d) block with 3 writer units rejected', False)
    except InputError as e:
        print(f'    message: {e}')
        case('(d) block with 3 writer units rejected', True)
    u = synth(2)
    u[0]['P2_pgsteal_kswapd'] = 9.0  # sync max is 1 -> 10x needs >= 10
    case('(e) manipulation check FAILs when one writer take is below 10x largest sync take',
         not manip_check(u)['pass'] and manip_check(synth(2))['pass'])
    ok0 = synth(1)
    for x in ok0:
        if x['arm'] == 'sync':
            x['P1_pgsteal_kswapd'] = x['P2_pgsteal_kswapd'] = 0.0
    case('(extra) max sync 0: PASS iff min writer > 0',
         manip_check(ok0)['pass'] and not manip_check([dict(x, P1_pgsteal_kswapd=0.0) if x['arm'] == 'writer' else x for x in ok0])['pass'])
    print('SELF-TEST ' + ('PASS' if not fails else 'FAIL'))
    return 1 if fails else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('csv', nargs='?')
    ap.add_argument('--json', action='store_true', help='print JSON instead of text')
    ap.add_argument('--self-test', action='store_true')
    ap.add_argument('--tdn', action='store_true', help='evening-3 TDN test (header block,unit,arm,P1_lost,P2_lost,P2_queued)')
    a = ap.parse_args()
    if a.self_test:
        sys.exit(tdn_self_test() if a.tdn else self_test())
    if not a.csv:
        ap.error('CSV path required (or --self-test)')
    try:
        if a.tdn:
            r = tdn_analyse(tdn_load(a.csv))
        else:
            r = analyse(load(a.csv))
    except (InputError, OSError) as e:
        print(f'b1_test: {e}', file=sys.stderr)
        sys.exit(2)
    if a.tdn:
        print(tdn_to_json(r) if a.json else tdn_report(r))
    else:
        print(to_json(r) if a.json else report(r))


if __name__ == '__main__':
    main()
