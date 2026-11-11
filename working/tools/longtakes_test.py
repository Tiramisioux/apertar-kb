#!/usr/bin/env python3
"""longtakes_test.py: offline tests of the NVMe campaign logic in longtakes.py (build list H18). Runs on the Mac, no Pi, no Core.

  python3 -I longtakes_test.py        # prints one line per test, exit 1 on any failure
"""
import json, os, sys, tempfile, types

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import longtakes as L   # noqa: E402

FAIL = []


def check(name, got, want):
    ok = got == want
    print('%-4s %s: %r%s' % ('ok' if ok else 'FAIL', name, got, '' if ok else ' (want %r)' % (want,)))
    if not ok:
        FAIL.append(name)


def fake_ctake(script):
    """script: fps -> list of verdicts in take order (3-min and 5-min mixed, as the cell asks for them)."""
    calls = []

    def ct(out, c, fps, tier, stage, variant, stop_on_drop=True, merge_on=False):
        seq = script.setdefault(fps, [])
        v = seq.pop(0) if seq else 'clean'
        calls.append((fps, tier, v))
        return {'verdict': v, 'outcome': 'pass' if v == 'clean' else 'drop'}
    return ct, calls


def setup(tmp):
    L.CS.update({'out': '', 'night': 'T', 'stop': '', 'decisions': [], 'args': types.SimpleNamespace(no_dropin_check=True)})
    L.STOP['sig'] = ''
    os.makedirs(tmp, exist_ok=True)


def test_cells(tmp):
    c = L.arm_cfg('4kHDR16')
    orig = L.ctake
    for name, script, want, ntakes in (
            ('clean 3 + clean 5 = carried', {28: ['clean', 'clean']}, 'carried', 2),
            ('two 3-min drops = out', {28: ['drop', 'drop']}, 'out', 2),
            ('1-1, third clean, 5-min clean = carried', {28: ['drop', 'clean', 'clean', 'clean']}, 'carried', 4),
            ('1-1, third drop = out', {28: ['drop', 'clean', 'drop']}, 'out', 3),
            ('3 clean, 5 drop, third 3 drop = out', {28: ['clean', 'drop', 'drop']}, 'out', 3),
            ('3 clean, 5 drop, 3 clean, second 5 clean = carried', {28: ['clean', 'drop', 'clean', 'clean']}, 'carried', 4)):
        ct, calls = fake_ctake(script)
        L.ctake = ct
        v, _cap = L.cell(tmp, c, 28, 'S2')
        check('cell: ' + name, (v, len(calls)), (want, ntakes))
    # the tiers asked for: 180 then 300
    ct, calls = fake_ctake({28: ['clean', 'clean']})
    L.ctake = ct
    L.cell(tmp, c, 28, 'S2')
    check('cell: tiers 3 then 5 min', [x[1] for x in calls], [180, 300])
    L.ctake = orig


def test_walk(tmp):
    c = L.arm_cfg('4kHDR16')
    orig, orig_save = L.ctake, L.save_arms
    L.save_arms = lambda out, arms: None
    # 28 carried, 29 carried, 30 out -> best 29
    ct, calls = fake_ctake({28: ['clean', 'clean'], 29: ['clean', 'clean'], 30: ['drop', 'drop']})
    L.ctake = ct
    arms = {}
    check('walk up: best 29', L.walk(tmp, c, 28, 30, 25, 'S2', arms, '4kHDR16'), 29)
    # 28 out, 27 carried -> best 27, walk stops going down
    ct, calls = fake_ctake({28: ['drop', 'drop'], 27: ['clean', 'clean']})
    L.ctake = ct
    arms = {}
    check('walk down: best 27', L.walk(tmp, c, 28, 30, 25, 'S2', arms, '4kHDR16'), 27)
    check('walk down: cells', arms['4kHDR16']['cells'], {'28': 'out', '27': 'carried'})
    # at the top: 30 carried, no 31
    ct, calls = fake_ctake({30: ['clean', 'clean']})
    L.ctake = ct
    arms = {}
    check('walk at top stops', (L.walk(tmp, c, 30, 30, 25, 'S2', arms, 'x'), len(calls)), (30, 2))
    L.ctake, L.save_arms = orig, orig_save


def test_go(tmp):
    L.save_arms(tmp, {'4kHDR16': {'s4_pass': 28}, '4kSDR12': {'s4_pass': 41}, '4kHDR12': {}})
    check('GO unconditional', L.go_condition(tmp, 'unconditional')[0], True)
    check('GO all_passed S4 false', L.go_condition(tmp, 'if all_passed S4')[0], False)
    check('GO passed 4kHDR16 S4', L.go_condition(tmp, 'if passed 4kHDR16 S4')[0], True)
    check('GO unparseable', L.go_condition(tmp, 'yes please'), (False, 'unparseable'))


def test_budget():
    check('cold delete 10,000 flat', round(L.cold_budget_s(10000, 0), 1), 13.6)
    check('cold delete 45,000 in 9 parts', round(L.cold_budget_s(45000, 9), 1), round(9 * 13.6 * 0.25, 1))
    check('cold delete 45,000 flat (merged)', round(L.cold_budget_s(45000, 0)), 275)


def test_post(tmp):
    """Boundary flag, index jumps, the numbering-gap columns are filled by campaign_post from a synthetic take."""
    L.CS['serial'] = 'TEST'
    row = {'take_id': 't1', 'rec_offset_s': 1.0, 'files': 12000, 'seconds': 400, 'tier_s': 300, 'outcome': 'pass_5min',
           '_gaps': [(10002, 10004), (7000, 7000)], 'core_cpu_slope': '', 'nvme_c_max': 50}
    samples = []
    for i in range(420):
        t = 1.0 + i
        buf = 5.0 + (40.0 if 1.0 + 5000 / 30.0 <= t <= 1.0 + 5000 / 30.0 + 1 else 0.0)
        samples.append({'t_s': t, 'state': 'rec', 'dropped': 0, 'buffer_used': buf, 'buffer_capacity': 100.0, 'core_cpu_pct': 50.0,
                        'dev_w_ios': i * 10, 'dev_w_ticks': i * 20, 'nvme_c': 50, 'dirty_kb': 100, 'clients': 1})
    jl = ['1.0 x ApertarCore audio capture: format=S24_3LE', '2.0 x ApertarCore drop[copy-slot]: frame=10001 held=6/6 dropped_total=1',
          '3.0 x ApertarCore frame index jump: frame=7001 count=7000 skipped=1 dt_us=55000 since_first_us=233000000 total=1']
    c = L.arm_cfg('4kHDR16')
    L.CS['audio_expected'] = True
    row['audio_missing'] = 0
    L.campaign_post(tmp, row, c, 30.0, samples, jl, '', {'dropped_copy_slot': '1', 'index_jumps': '1'}, {})
    check('post: boundaries crossed (12000 frames, 5000 per part)', row['boundaries_crossed'], 2)
    check('post: boundary drops (10001-10004 after 10000)', row['boundary_drops'], 4)
    check('post: drop frames', row['drop_frames'], '10002-10004 7000')
    check('post: boundary buffer bump seen', row['boundary_buf_bump_pct'] >= 39, True)
    con = L.cdb(tmp)
    check('post: index jump stored', list(con.execute('SELECT frame, skipped, dt_us FROM index_jumps')), [(7001, 1, 55000)])
    check('post: boundaries stored', [r[1] for r in con.execute('SELECT * FROM boundaries ORDER BY k')], [1, 2])
    con.close()
    check('post: not void', row['outcome'], 'pass_5min')
    # a take with audio expected but no audio capture line is a void
    row2 = dict(row, take_id='t2', audio_missing=1, outcome='pass_5min', _gaps=[])
    L.campaign_post(tmp, row2, c, 30.0, samples, [], '', {}, {})
    check('post: audio_missing = void', (row2['outcome'], row2['outcome_raw']), ('void', 'pass_5min'))
    # --audio-optional (User 2026-11-10): the same take counts, audio_missing stays 1
    L.CS['args'].audio_optional = True
    row3 = dict(row, take_id='t3', audio_missing=1, outcome='pass_5min', _gaps=[])
    L.campaign_post(tmp, row3, c, 30.0, samples, [], '', {}, {})
    check('post: audio_missing with --audio-optional counts', (row3['outcome'], row3['audio_missing']), ('pass_5min', 1))
    L.CS['args'].audio_optional = False


def test_fill_gate(tmp):
    """The gate deletes the OLDEST ledger clips until it fits, and stops at a re-stat mismatch."""
    deleted = []
    free = {'b': 50e9}
    orig = (L.ledger_live, L.delete_clip, L.os.statvfs, L.wait_trim)
    clips = [{'clip': 'c1', 'files': 100, 'created': 1, 'bytes': 100e9}, {'clip': 'c2', 'files': 100, 'created': 2, 'bytes': 300e9},
             {'clip': 'c3', 'files': 100, 'created': 3, 'bytes': 300e9}]
    L.ledger_live = lambda out: [c for c in clips if c['clip'] not in deleted]

    def dc(out, c):
        deleted.append(c['clip']); free['b'] += c['bytes']; return ''
    L.delete_clip = dc
    L.os.statvfs = lambda p: types.SimpleNamespace(f_bavail=int(free['b'] / 4096), f_frsize=4096, f_blocks=1)
    L.wait_trim = lambda t, cap=60: True
    L.CS['cold_wait_s'] = 0
    check('fill gate: fits after two deletes', (L.fill_gate(tmp, 400e9), deleted), ('', ['c1', 'c2']))
    L.ledger_live, L.delete_clip, L.os.statvfs, L.wait_trim = orig


def test_estimator(tmp):
    """Estimator campaign (2026-11-11): ids of the old configs unchanged, the new ones distinct; the half-fraction; ProRes lines."""
    import itertools as it
    check('est: old cfg id unchanged', L.arm_cfg('4kHDR16').id, '4kHDR16_unc_log0_tdn0_lock0_trim1_web1_fpf5000')
    check('est: prores id', L.est_cfg('4kP:prores:hq').id, '4kP_unc_log0_tdn0_lock0_trim1_web1_prores-hq_aud1_aids1')
    check('est: lossy id', L.est_cfg('4kSDR12:lossydng:5to1', tdn=True).id,
          '4kSDR12_unc_log0_tdn1_lock0_trim1_web1_fpf5000_lossydng-5to1_aud1_aids1')
    g = L.est_grid()
    check('est: grid 44 specs, unique', (len(g), len(set(g))), (44, 44))
    d = L.est_p2_design()
    bal = all(sum(1 for r in d if r[k]) == 8 for k in L.EST_LEVERS)
    pairs = all(sum(1 for r in d if (r[a], r[b]) == v) == 4 for a, b in it.combinations(L.EST_LEVERS, 2)
                for v in it.product((False, True), repeat=2))
    check('est: P2 16 runs, balanced, every pair balanced', (len(d), bal, pairs), (16, True, True))
    jl = ['100.0 x ApertarCore ProRes drop[queue-full]: total=1', '101.0 x ApertarCore ProRes drop[queue-full]: total=30',
          '102.0 x ApertarCore ProRes recording stats: queued=1500 submitted=1440 dropped_queue_full=60 failures=0 peak_queue=8/8']
    kinds, first, stats, _t = L.parse_journal(jl, 99.0)
    check('est: ProRes drop lines and stats', (kinds, first, stats.get('submitted'), stats.get('dropped_queue_full')),
          ({'prores-queue-full': 30}, 1.0, '1440', '60'))
    c = L.est_cfg('4kP:prores:hq')
    r = {'stats': json.dumps({'submitted': '1440'}), 'seconds': 60.0, 'dropped': 60, 'capacity_fps': '', 'capacity_how': 'at least',
         'outcome': 'ab_dropped', 'gb_written': 14.4, 'verdict': 'drop'}
    rec = L.est_record('P1', 'cap', '4kP:prores:hq', {}, c, 25, 30.0, r, 1)
    check('est: ProRes capacity = frames written per second', (rec['cap_fps'], rec['cap_how'], rec['bpf']), (24.0, 'delivered', 10000000))
    # apply_cfg: ProRes sends its profile, no raw bit-depth round trip, and the levers
    sent = []
    orig = (L.core, L.state, L.settle, L.time.sleep)
    L.core = lambda name, **kw: sent.append((name, kw)) or {'ok': True}
    L.state = lambda: {'recording_format': 'cdng', 'clear_hdr': False, 'resolution': '3840x2160'}
    L.settle = lambda timeout=40: {}
    L.time.sleep = lambda s: None
    L.apply_cfg(c, 25)
    names = [n for n, _ in sent]
    check('est: apply_cfg prores', ('set_record_format' in names, 'set_raw_bit_depth' in names, ('set_prores_profile', {'value': 'hq'}) in sent,
                                     ('set_zebra_enabled', {'enabled': True}) in sent), (True, False, True, True))
    L.core, L.state, L.settle, L.time.sleep = orig
    ow = L.web_state
    L.web_state = lambda timeout=1.0: {'ui': {'record_audio_enabled': True, 'focus_peaking_enabled': True, 'zebra_enabled': True}}
    st = {'recording_format': 'prores', 'prores_profile': 'hq', 'prores_color_profile': 'standard', 'raw_bit_depth': 12,
          'clear_hdr': True, 'preview_tdn': False, 'fps_phase_lock': False, 'fps': 25, 'resolution': '3840x2160'}
    check('est: verify prores ignores bits and clear_hdr', L.verify(c, 25, st), '')
    check('est: verify prores catches the profile', L.verify(c, 25, dict(st, prores_profile='422')), 'prores=422')
    L.web_state = lambda timeout=1.0: {'ui': {'record_audio_enabled': False, 'focus_peaking_enabled': True, 'zebra_enabled': True}}
    check('est: verify catches the audio lever', L.verify(c, 25, st), 'audio=False')
    L.web_state = ow


def test_estimate_model(tmp):
    import estimate as E
    run = os.path.join(tmp, 'estrun')
    os.makedirs(run + '/est', exist_ok=True)
    recs = []
    def add(block, kind, spec, cap, how='fit', lv=None, gaps=0.0, fps=30, top=30, bpf=None, rep=1):
        recs.append({'block': block, 'kind': kind, 'spec': spec, 'levers': dict(E.REF, **(lv or {})), 'cap_fps': cap, 'cap_how': how,
                     'gaps_per_min': gaps, 'fps': fps, 'top': top, 'bpf': bpf, 'verdict': 'drop', 'outcome': 'ab_dropped', 'rep': rep})
    add('P1', 'cap', '4kHDR16:cdng:lj', 18.0, 'delivered', fps=30, bpf=8e6)
    add('P1', 'cap', '2kSDR12:cdng:lj', 70.0, 'delivered', fps=60, top=60, bpf=1.5e6)
    add('P1', 'cap', '4kSDR12:cdng:unc', 48.0, 'fit', fps=60, top=60, bpf=12.44e6)
    add('P1', 'cap', '4kSDR10:cdng:unc', 57.0, 'fit', fps=60, top=60, bpf=10.37e6)
    add('P1', 'cap', '4kP:prores:hq', 30.0, 'at least', fps=30)
    for r in L.est_p2_design():
        cap = 18.0 * (0.9 if r['web'] else 1.0) / (0.9 if E.REF['web'] else 1.0)
        add('P2', 'enc', '4kHDR16:cdng:lj', cap, 'delivered', lv=r, fps=25)
    for line in recs:
        pass
    with open(run + '/est/probes.jsonl', 'w') as f:
        f.write('\n'.join(json.dumps(x) for x in recs) + '\n')
    m = E.fit(E.load(run))
    p_ref = E.predict(m, '4kHDR16:cdng:lj')
    p_web0 = E.predict(m, '4kHDR16:cdng:lj', {'web': False})
    check('estimate: HDR16 lossless at the reference (known cell out at 25 caps it; the probe says 18)', (p_ref['fps'], p_ref['limiter']), (17, 'encoder'))
    check('estimate: WebUI off lifts the encoder limit by 1/0.9', (p_web0['fps'], round(p_web0['limit'], 1)), (19, 20.0))
    p_unc = E.predict(m, '4kSDR12:cdng:unc')
    check('estimate: SDR12 unc: the probe (48) vs sustained 596 MB/s (47.9)', (p_unc['fps'], p_unc['limiter']), (46, 'storage (sustained)'))
    check('estimate: ProRes HQ: at least the top', E.predict(m, '4kP:prores:hq')['fps'], 30)
    p0 = E.fit(E.load(run), only_blocks=('P1',))
    check('estimate: scaling, 4kSDR10 unc from the SDR12 write rate', round(E.scale_from_anchors(p0, '4kSDR10:cdng:unc')[0], 1), 57.6)
    paths = E.write_outputs(run)
    check('estimate: outputs written', [os.path.basename(x) for x in paths], ['estimate-table.csv', 'estimate.md', 'selftest.md'])


def main():
    tmp = tempfile.mkdtemp(prefix='longtakes_test_')
    setup(tmp)
    test_cells(tmp)
    test_walk(tmp)
    test_go(tmp)
    test_budget()
    test_post(tmp)
    test_fill_gate(tmp)
    test_estimator(tmp)
    test_estimate_model(tmp)
    print('%d failed' % len(FAIL) if FAIL else 'all passed')
    sys.exit(1 if FAIL else 0)


if __name__ == '__main__':
    main()
