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


def main():
    tmp = tempfile.mkdtemp(prefix='longtakes_test_')
    setup(tmp)
    test_cells(tmp)
    test_walk(tmp)
    test_go(tmp)
    test_budget()
    test_post(tmp)
    test_fill_gate(tmp)
    print('%d failed' % len(FAIL) if FAIL else 'all passed')
    sys.exit(1 if FAIL else 0)


if __name__ == '__main__':
    main()
