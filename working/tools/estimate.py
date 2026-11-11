#!/usr/bin/env python3
"""estimate.py: the sustained-fps model of the estimator campaign (plan working/drop-frames/estimator-campaign/plan.md, sections 2
and 6). Reads <run>/est/probes.jsonl (60-s probes, P0-P2, P5), validation.jsonl (P3) and ladder.jsonl (P4); writes
<run>/est/estimate.md, estimate-table.csv and selftest.md. Offline: runs on the Mac on a pulled run, or inside the runner.

  python3 -I estimate.py <run dir>              # fit, predict, check, write the outputs
  python3 -I estimate.py <run dir> --spec 4kHDR16:cdng:lj --levers tdn=1   # one prediction

The model (plan section 2). Sustained fps = min(sensor top, the probed stage limit with the levers' effects, the back end's
onset where the probes saw gaps, the drive's sustained write). The probed limit of a spec is the median of its reference-lever
probes (P1): the buffer slope ('fit' / 'stats') or the frames Core wrote per second ('delivered'); 'at least' = no stage below the
probe's fps. The levers act on the stage the spec is limited by: P2 gives their main effects on log(capacity) at the encoder and
storage anchors and on the gap rate at the back-end anchor (a 2^(5-1) half-fraction, so a main effect is the mean difference
on / off). Every number in the outputs carries its label: measured (a probe or a cell), derived (the model)."""
import argparse, csv, itertools, json, math, os, statistics, sys

SUB = 'est'      # the run's estimator folder: est, or est-<build> for a build's own set (the runner sets it)

LEVERS = ('tdn', 'lock', 'web', 'audio', 'aids')
REF = {'tdn': False, 'lock': False, 'web': True, 'audio': True, 'aids': True}
# The drives' sustained write (the stored drive profile, plan section 2; User 2026-11-11: the self-test does not measure the
# drive, the profile does). MP600 Mini A936B442006AC2: the slowest 10-s window of the S1 write, 596-627 MB/s (measured).
DRIVE = {'A936B442006AC2': {'name': 'Corsair MP600 Mini', 'sustained_mbps': 596.0, 'ns_per_entry': 63.3}}
# Cells measured before this run (the campaign rule: 3 + 5 min clean = carried, two concordant drops = out), at the reference
# levers. NVMe campaign 2026-11-10 (measured, findings.md); <run>/est/known-cells.json adds or replaces entries, and this run's
# P3 cells count too. A cell out at f caps the estimate at f - 1.
KNOWN_CELLS = {'4kHDR16:cdng:unc': {'carried': [27], 'out': [28]},
               '4kHDR16:cdng:unc:log': {'carried': [25], 'out': [28]},
               '4kHDR16:cdng:lj': {'out': [25]},
               '4kHDR16:cdng:lj:log': {'out': [25, 26]},
               '4kSDR12:cdng:unc': {'carried': [29, 30]},
               '4kSDR12:cdng:lj': {'carried': [29, 30]}}
MARGIN = 0.97          # the estimate is the whole fps at or below 97 % of the predicted limit (not for the sensor's own top)
FAMILIES = ('cdng-unc', 'cdng-lj', 'log', 'lossy', 'mlv', 'prores', 'h264')
MODE_PIX = {'4kSDR12': (3840, 2160, 12, False), '4kSDR10': (3840, 2160, 10, False), '4kHDR12': (3840, 2160, 12, True),
            '4kHDR16': (3840, 2200, 16, True), '2kSDR12': (1920, 1080, 12, False), '2kSDR10': (1920, 1080, 10, False),
            '2kHDR16': (1920, 1100, 16, True), '2kHDR12': (1920, 1080, 12, True), 'crop4k3SDR12': (2880, 2160, 12, False),
            '4kP': (3840, 2160, 10, False), '2kP': (1920, 1080, 10, False)}


def parts(spec):
    f = spec.split(':')
    return f[0], f[1], f[2:] + ['', '']


def family(spec):
    m, fmt, o = parts(spec)
    if fmt == 'cdng':
        return 'log' if 'log' in o else ('cdng-lj' if o[0] == 'lj' else 'cdng-unc')
    return {'lossydng': 'lossy'}.get(fmt, fmt)


def raw_bytes(spec):
    """Bytes the sensor delivers per frame (uncompressed; 16-bit Clear HDR carries 40 extra lines)."""
    w, h, b, _hdr = MODE_PIX[parts(spec)[0]]
    return w * h * b / 8.0


def pixels(spec):
    w, h, _b, _hdr = MODE_PIX[parts(spec)[0]]
    return w * h


def load(run):
    def jl(name):
        p = os.path.join(run, SUB, name + '.jsonl')
        out = []
        if os.path.exists(p):
            for l in open(p):
                try:
                    out.append(json.loads(l))
                except ValueError:
                    pass
        return out
    serial = ''
    for n in sorted(os.listdir(run)) if os.path.isdir(run) else []:
        if n.startswith('night-') and n.endswith('.json'):
            try:
                serial = json.load(open(os.path.join(run, n))).get('card', {}).get('serial', '') or serial
            except (OSError, ValueError):
                pass
    known = {k: {'carried': list(v.get('carried', [])), 'out': list(v.get('out', []))} for k, v in KNOWN_CELLS.items()}
    kp = os.path.join(run, SUB, 'known-cells.json')
    if os.path.exists(kp):
        for k, v in json.load(open(kp)).items():
            known[k] = v
    for x in jl('validation'):
        if all(bool(x.get('levers', {}).get(k, REF[k])) == REF[k] for k in LEVERS):
            for tag, c in x.get('cells', {}).items():
                if c.get('verdict') == 'drop':
                    known.setdefault(x['spec'], {'carried': [], 'out': []})['out'].append(c['fps'])
    return {'probes': jl('probes'), 'validation': jl('validation'), 'ladder': jl('ladder'), 'serial': serial, 'known': known}


def is_ref(lv):
    return all(bool(lv.get(k, REF[k])) == REF[k] for k in LEVERS)


def usable(r):
    return r.get('verdict') not in ('skip', 'void', 'stop', None) and r.get('outcome') not in ('setup_mismatch', 'skipped_unavailable')


def spec_base(records):
    """Per spec, from the reference-lever probes: the limit, how it was read, the top, the bytes per frame, the gap rate."""
    by = {}
    for r in records:
        if usable(r) and is_ref(r.get('levers') or {}) and r.get('kind') in ('cap', 'gap'):
            by.setdefault(r['spec'], []).append(r)
    base = {}
    for spec, rs in by.items():
        caps = [r['cap_fps'] for r in rs if r.get('cap_fps') and r.get('cap_how') in ('fit', 'stats', 'delivered')]
        least = [r['cap_fps'] for r in rs if r.get('cap_fps') and r.get('cap_how') == 'at least']
        top = max((r.get('top') or 0) for r in rs) or None
        bpf = [r['bpf'] for r in rs if r.get('bpf')]
        gapr = [(r['fps'], r.get('gaps_per_min') or 0) for r in rs]
        d = {'top': top, 'bpf': statistics.median(bpf) if bpf else None, 'gaps': gapr, 'n': len(rs)}
        if caps:
            d.update(cap=statistics.median(caps), how='measured', spread=(max(caps) - min(caps)) if len(caps) > 1 else None)
        elif least:
            d.update(cap=max(least), how='at least')
        base[spec] = d
    return base


def limiter(spec, b, drive):
    """The stage that sets the spec's limit at the reference levers."""
    fam = family(spec)
    gap_at = [f for f, g in b.get('gaps', []) if g and g > 0]
    if b.get('how') == 'at least':
        return 'back end' if gap_at else 'sensor'
    if gap_at and fam in ('cdng-unc', 'log', 'mlv'):
        return 'back end'
    if fam in ('cdng-unc', 'mlv'):
        return 'storage'
    if b.get('cap') and b.get('bpf') and drive and b['cap'] * b['bpf'] / 1e6 > 0.9 * drive['sustained_mbps']:
        return 'storage'
    return 'encoder'


def lever_effects(records):
    """P2 main effects per anchor: enc / stor on log(capacity), be on the gap rate per minute; with the replicate noise."""
    eff = {}
    for anchor in ('be', 'be2', 'enc', 'stor'):
        rs = [r for r in records if r.get('block') == 'P2' and r.get('kind') == anchor and usable(r)]
        if anchor in ('be', 'be2'):
            ys = [(r['levers'], r.get('gaps_per_min') or 0.0) for r in rs]
        else:
            ys = [(r['levers'], math.log(r['cap_fps'])) for r in rs if r.get('cap_fps') and r.get('cap_how') != 'at least']
        if len(ys) < 8:
            continue
        e = {}
        for k in LEVERS:
            on = [y for lv, y in ys if lv.get(k)]
            off = [y for lv, y in ys if not lv.get(k)]
            if on and off:
                e[k] = statistics.mean(on) - statistics.mean(off)
        for k1, k2 in itertools.combinations(LEVERS, 2):
            same = [y for lv, y in ys if bool(lv.get(k1)) == bool(lv.get(k2))]
            diff = [y for lv, y in ys if bool(lv.get(k1)) != bool(lv.get(k2))]
            if same and diff:
                e[k1 + 'x' + k2] = statistics.mean(same) - statistics.mean(diff)     # +-1 coding, as the main effects
        eff[anchor] = {'effects': e, 'n': len(ys)}
    # noise: the back-end anchor ran twice; the same design point's two gap rates give the SE of an effect
    be1 = {json.dumps(r['levers'], sort_keys=True): r.get('gaps_per_min') or 0 for r in records
           if r.get('block') == 'P2' and r.get('kind') == 'be' and usable(r)}
    diffs = [be1[k] - (r.get('gaps_per_min') or 0) for r in records if r.get('block') == 'P2' and r.get('kind') == 'be2'
             and usable(r) for k in [json.dumps(r['levers'], sort_keys=True)] if k in be1]
    if len(diffs) >= 4:
        sd = statistics.pstdev(diffs) / math.sqrt(2)
        for a in ('be', 'be2'):
            if a in eff:
                eff[a]['se'] = 2 * sd / math.sqrt(eff[a]['n'])
    reps = {}
    for r in records:
        if r.get('block') == 'P1' and usable(r) and r.get('cap_fps') and r.get('cap_how') in ('fit', 'stats', 'delivered'):
            reps.setdefault(r['spec'], []).append(math.log(r['cap_fps']))
    pairs = [v[0] - v[1] for v in reps.values() if len(v) >= 2]
    if len(pairs) >= 3:
        sd = statistics.pstdev(pairs) / math.sqrt(2)
        for a in ('enc', 'stor'):
            if a in eff:
                eff[a]['se'] = 2 * sd / math.sqrt(eff[a]['n'])
    return eff


def fit(data, only_blocks=None):
    recs = [r for r in data['probes'] if not only_blocks or r.get('block') in only_blocks]
    drive = DRIVE.get(data.get('serial') or '') or next(iter(DRIVE.values()))
    base = spec_base([r for r in recs if r.get('block') in ('P1', 'P0', 'P5') or only_blocks])
    lim = {s: limiter(s, b, drive) for s, b in base.items()}
    return {'base': base, 'limiter': lim, 'effects': lever_effects(data['probes']), 'drive': drive, 'records': recs,
            'known': data.get('known') or {}}


def scale_from_anchors(model, spec):
    """For the self-test: a spec P0 did not probe, from the anchors of its family (plan section 6.4). Lossless JPEG: per-frame
    time a + b x raw bytes through its two anchors; lossy DNG, ProRes, H.264: time proportional to bytes or pixels through the
    one anchor; uncompressed cDNG and MLV: the anchor's write rate / the spec's bytes."""
    base = model['base']
    fam = family(spec)
    def cap(s):
        b = base.get(s)
        return b['cap'] if b and b.get('how') == 'measured' else None
    if fam in ('cdng-unc', 'mlv'):
        a = base.get('4kSDR12:cdng:unc')
        if a and a.get('how') == 'measured' and a.get('bpf'):
            return a['cap'] * a['bpf'] / raw_bytes(spec), 'derived: anchor write rate / bytes'
    if fam in ('cdng-lj', 'log'):
        pts = [(raw_bytes(s), 1.0 / cap(s)) for s in ('4kHDR16:cdng:lj', '2kSDR12:cdng:lj') if cap(s)]
        if len(pts) == 2 and pts[0][0] != pts[1][0]:
            b_ = (pts[0][1] - pts[1][1]) / (pts[0][0] - pts[1][0])
            a_ = pts[0][1] - b_ * pts[0][0]
            by = raw_bytes(spec) * (0.75 if fam == 'log' else 1.0)      # Log stores 16 -> 12 bit
            t = a_ + b_ * by
            if t > 0:
                return 1.0 / t, 'derived: lossless a + b x bytes'
    if fam == 'lossy' and cap('4kSDR12:lossydng:3to1'):
        return cap('4kSDR12:lossydng:3to1') * raw_bytes('4kSDR12:lossydng:3to1') / raw_bytes(spec), 'derived: lossy x bytes'
    if fam == 'prores' and cap('4kP:prores:hq'):
        return cap('4kP:prores:hq') * pixels('4kP:prores:hq') / pixels(spec), 'derived: ProRes HQ x pixels'
    if fam == 'h264' and cap('4kP:h264:1920x1080'):
        return cap('4kP:h264:1920x1080'), 'derived: H.264 1080 anchor'
    return None, 'no anchor'


def predict(model, spec, levers=None, allow_scaling=False, use_known=True):
    """{'fps': whole estimate or None, 'limit': the predicted limit, 'limiter', 'label', 'note'}."""
    lv = dict(REF)
    lv.update({k: bool(v) for k, v in (levers or {}).items() if k in LEVERS})
    b = model['base'].get(spec)
    drive = model['drive']
    note = []
    if b is None or not b.get('cap'):
        if not allow_scaling:
            return {'fps': None, 'note': 'not probed', 'limiter': None}
        cap_, how_ = scale_from_anchors(model, spec)
        if not cap_:
            return {'fps': None, 'note': how_, 'limiter': None}
        b = {'cap': cap_, 'how': 'derived', 'top': None, 'bpf': None, 'gaps': []}
        lim = 'storage' if family(spec) in ('cdng-unc', 'mlv') else 'encoder'
        note.append(how_)
    else:
        lim = model['limiter'].get(spec) or limiter(spec, b, drive)
    limit = b['cap']
    label = 'measured' if b.get('how') == 'measured' else ('at least' if b.get('how') == 'at least' else 'derived')
    changed = [k for k in LEVERS if lv[k] != REF[k]]
    anchor = {'encoder': 'enc', 'storage': 'stor'}.get(lim)
    eff = model['effects']
    if changed and anchor and anchor in eff:
        e = eff[anchor]['effects']
        d = sum((e.get(k, 0.0) * (1 if lv[k] else -1)) for k in changed)
        se = eff[anchor].get('se')
        if se is None or abs(d) > se:
            limit = limit * math.exp(d)
            note.append('levers %s: x%.3f (P2 %s)' % (','.join(changed), math.exp(d), anchor))
        label = 'derived'
    # the back end: where the reference probes saw gaps, or a lever raises the gap rate at the anchor
    hdr = MODE_PIX[parts(spec)[0]][3]
    be_limit = None
    gap_fps = sorted(f for f, g in b.get('gaps', []) if g and g > 0)
    if gap_fps:
        be_limit = gap_fps[0] - 1
        note.append('back end: gaps at %s fps (measured)' % gap_fps[0])
    if hdr and 'be' in eff and changed:
        e = eff['be']['effects']
        d = sum((e.get(k, 0.0) * (1 if lv[k] else -1)) for k in changed)
        se = eff['be'].get('se') or 0.5
        if d > se:
            be_limit = min(be_limit or 99, 27 if not lv['tdn'] else 24)
            note.append('back end: levers %s raise the gap rate at 28 fps by %.1f/min (P2)' % (','.join(changed), d))
            label = 'derived'
    stor = None
    bpf = b.get('bpf') or (raw_bytes(spec) if family(spec) in ('cdng-unc', 'mlv') else None)
    if bpf and drive:
        stor = drive['sustained_mbps'] * 1e6 / bpf
    cell_cap = None
    kc = (model.get('known') or {}).get(spec) if use_known and not changed else None
    if kc and kc.get('out'):
        cell_cap = min(kc['out']) - 1 + 0.999           # the estimate becomes at most out - 1
        note.append('cell out at %s fps (measured)' % min(kc['out']))
    cands = [('sensor', b.get('top')), (lim, limit), ('back end', be_limit), ('storage (sustained)', stor),
             ('measured cell', cell_cap)]
    cands = [(n, v) for n, v in cands if v]
    if not cands:
        return {'fps': None, 'note': 'no limit', 'limiter': None}
    name, v = min(cands, key=lambda x: x[1])
    if name in ('sensor', 'measured cell') or (b.get('how') == 'at least' and name == lim):
        est = int(v)
    else:
        est = int(math.floor(MARGIN * v))
    return {'fps': est, 'limit': round(v, 2), 'limiter': name,
            'label': 'measured' if name == 'measured cell' else (label if name != 'storage (sustained)' else 'derived'),
            'note': '; '.join(note)}


def space(model):
    specs = sorted(model['base'])
    for spec in specs:
        for bits in itertools.product((False, True), repeat=len(LEVERS)):
            yield spec, dict(zip(LEVERS, bits))


def draw_combos(model, rng, n):
    """P3: n combinations, every family at least once (plan section 5), levers by die."""
    specs = [s for s, b in model['base'].items() if b.get('cap')]
    fams = {}
    for s in specs:
        fams.setdefault(family(s), []).append(s)
    picks = []
    for f in FAMILIES:
        if f in fams and len(picks) < n:
            picks.append(rng.choice(sorted(fams[f])))
    while len(picks) < n and specs:
        picks.append(rng.choice(sorted(specs)))
    return [(s, {k: bool(rng.getrandbits(1)) for k in LEVERS}) for s in picks]


def selftest_check(data):
    """Plan section 6.4: refit from P0 alone (+ the drive profile) and predict P1's reference specs; the share within +-1 fps."""
    full = fit(data)
    p0 = fit(data, only_blocks=('P0',))
    rows = []
    for spec, b in sorted(full['base'].items()):
        if not b.get('cap') or b.get('how') != 'measured':
            continue
        want = predict(full, spec, use_known=False)
        got = predict(p0, spec, allow_scaling=True, use_known=False)
        if want.get('fps') is None:
            continue
        err = None if got.get('fps') is None else got['fps'] - want['fps']
        rows.append((spec, want['fps'], got.get('fps'), err, got.get('note', '')))
    within = [r for r in rows if r[3] is not None and abs(r[3]) <= 1]
    return rows, (len(within) / len(rows) if rows else None)


def validation_summary(data):
    v = data['validation']
    at_p = [x for x in v if 'p' in x.get('cells', {})]
    at_p1 = [x for x in v if 'p+1' in x.get('cells', {})]
    clean_p = sum(1 for x in at_p if x['cells']['p']['verdict'] == 'clean')
    out_p1 = sum(1 for x in at_p1 if x['cells']['p+1']['verdict'] == 'drop')
    return {'n': len(v), 'clean_at_p': '%d of %d' % (clean_p, len(at_p)), 'out_at_p+1': '%d of %d' % (out_p1, len(at_p1))}


def write_outputs(run):
    data = load(run)
    model = fit(data)
    d = os.path.join(run, SUB)
    os.makedirs(d, exist_ok=True)
    tp = os.path.join(d, 'estimate-table.csv')
    with open(tp, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['spec', 'family'] + list(LEVERS) + ['estimate_fps', 'limit_fps', 'limited_by', 'label', 'note'])
        for spec, lv in space(model):
            p = predict(model, spec, lv)
            w.writerow([spec, family(spec)] + [int(lv[k]) for k in LEVERS] +
                       [p.get('fps'), p.get('limit'), p.get('limiter'), p.get('label'), p.get('note')])
    L = ['# Estimator campaign: sustained fps estimates', '',
         'Run `%s`; drive %s (sustained %.0f MB/s, stored profile). Estimates at the reference levers (TDN off, lock off, WebUI on, '
         'audio on, aids on); every lever state is in `estimate-table.csv`.' % (os.path.basename(run.rstrip('/')),
                                                                                model['drive']['name'], model['drive']['sustained_mbps']), '',
         '| spec | top | probed limit | how | estimate | limited by | note |', '| --- | --- | --- | --- | --- | --- | --- |']
    for spec, b in sorted(model['base'].items()):
        p = predict(model, spec)
        L.append('| %s | %s | %s | %s | %s | %s | %s |' % (spec, b.get('top'), b.get('cap'), b.get('how'), p.get('fps'),
                                                            p.get('limiter'), p.get('note', '')))
    L += ['', '## Lever effects (P2, main effects; enc/stor on log capacity, be on gaps per minute)', '']
    for a, e in sorted(model['effects'].items()):
        L.append('- %s (n=%d, SE %s): %s' % (a, e['n'], ('%.3f' % e['se']) if e.get('se') is not None else '-',
                                              ', '.join('%s %+.3f' % kv for kv in sorted(e['effects'].items()) if 'x' not in kv[0])))
        ints = [(k, v) for k, v in e['effects'].items() if 'x' in k and e.get('se') is not None and abs(v) > e['se']]
        if ints:
            L.append('  - two-way interactions above SE: ' + ', '.join('%s %+.3f' % kv for kv in ints))
    vs = validation_summary(data)
    L += ['', '## Validation (P3)', '', '- %s' % vs, '- success (pre-registered): clean at p in >= 10 of 12, out at p+1 in >= 8 of 12']
    if data['ladder']:
        L += ['', '## Ladder check (P4)', '']
        L += ['- %s fps: rung %s expected, %s %s %s' % (x['fps'], x['expected_rung'], x['verdict'], x['outcome'], x.get('mismatch') or '')
              for x in data['ladder']]
    mp = os.path.join(d, 'estimate.md')
    open(mp, 'w').write('\n'.join(L) + '\n')
    rows, share = selftest_check(data)
    S = ['# Self-test check (plan section 6.4)', '',
         'P0 alone (+ the drive profile) against the full fit: %s within +-1 fps (goal >= 90 %%).' % (
             '%.0f %%' % (100 * share) if share is not None else 'no data'), '',
         '| spec | full fit | from P0 | error | how |', '| --- | --- | --- | --- | --- |']
    S += ['| %s | %s | %s | %s | %s |' % r for r in rows]
    sp = os.path.join(d, 'selftest.md')
    open(sp, 'w').write('\n'.join(S) + '\n')
    return [tp, mp, sp]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('run')
    ap.add_argument('--spec')
    ap.add_argument('--levers', default='', help='e.g. tdn=1,web=0')
    ap.add_argument('--set', default='est', help='the estimator folder in the run: est, or est-<build>')
    a = ap.parse_args()
    global SUB
    SUB = a.set
    if a.spec:
        lv = {k: v in ('1', 'true', 'on') for k, v in (x.split('=') for x in a.levers.split(',') if '=' in x)}
        print(json.dumps(predict(fit(load(a.run)), a.spec, lv, allow_scaling=True), indent=1))
    else:
        print('\n'.join(write_outputs(a.run)))


if __name__ == '__main__':
    main()
