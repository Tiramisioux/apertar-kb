#!/usr/bin/env python3
"""est_settings_check.py: the estimator day's settings dry run. Nothing is recorded, nothing is written to the card.

  python3 -I ~/longtakes/bin-est/est_settings_check.py --out ~/longtakes/est-check-<tag> [--dual-off] [--blocks P0,P1,P2,LEV,P4]

Every configuration the estimator day asks Core for is set the way the runner sets it (longtakes.apply_cfg) and read back
the way the runner checks it before a take (longtakes.verify). Blocks:
  P0   the ten first probes (their own fps)
  P1   every mode x format / compression of the grid (44 specs, levers at the reference)
  P2   the 16 lever rows of the lever design on each of the three anchors (48)
  LEV  one spec per format family with every lever away from the reference (TDN on, lock on, audio off, aids off), so the
       random lever combinations of P3 are covered for every format
  P4   the Mode Ladder: the three rungs with example thresholds, and the fps that should land on each rung
Plus the night's fixed state (speed ramp off, merge off, ladder off, frames_per_folder 5000) and, with --dual-off, the Dual
sensor switch off (read back in the web state). The WebUI lever is the runner's own client, not a setting: not checked.
At the end everything found at the start is put back and read back (the runner's restore, including every format's
resolution profile, the UI switches and the ladder's rungs) and the Dual sensor switch is set back as found.
Results: <out>/check.md (one line per configuration, OK or what differed), check.jsonl, restore-CHECK.txt.
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))     # python3 -I leaves the script's folder out
import longtakes as L                                              # noqa: E402

FOUND_KEYS = ('fps', 'raw_bit_depth', 'cdng_compression', 'cdng_log', 'preview_tdn', 'fps_phase_lock', 'fps_speed_ramp',
              'clear_hdr', 'resolution', 'recording_format', 'ladder_enabled', 'frames_per_folder', 'clip_merge_enabled',
              'tuning_file')
LEV_AWAY = {'tdn': True, 'lock': True, 'audio': False, 'aids': False}
LEV_SPECS = ('4kHDR16:cdng:unc', '4kSDR12:cdng:lj', '4kHDR16:cdng:unc:log', '4kSDR12:lossydng:3to1', '4kSDR12:mlv',
             '4kP:prores:hq', '4kP:h264:1920x1080')
LADDER = [('4kHDR16:cdng:unc', '3840x2160:16:hdr:%s:none', 25), ('4kSDR12:cdng:lj', '3840x2160:12:sdr:%s:lossless_jpeg', 35),
          ('2kSDR12:cdng:lj', '1920x1080:12:sdr:%s:lossless_jpeg', 50)]
LADDER_TH = (27, 41)       # example thresholds (the day fills them from the estimate): <= 27 HDR16, <= 41 SDR12 lj, above 2K


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out', required=True)
    ap.add_argument('--dual-off', action='store_true', help='switch the Dual sensor switch off for the check (set back at the end)')
    ap.add_argument('--blocks', default='P0,P1,P2,LEV,P4')
    a = ap.parse_args()
    out = os.path.abspath(os.path.expanduser(a.out))
    os.makedirs(out, exist_ok=True)
    L.CS.update({'out': out, 'night': 'CHECK', 'stop': '', 'decisions': [], 'audio_expected': False,
                 'args': argparse.Namespace(no_dropin_check=True)})
    L.helper = lambda *x, **k: (0, 'not used by the settings check')      # no timers were masked: nothing to unmask
    t0 = time.time()
    lines, rows = [], []

    def note(s):
        print(s, flush=True)
        lines.append(s)

    st0 = L.state()
    if not st0:
        sys.exit('Core does not answer on its socket: nothing done')
    if st0.get('recording') or st0.get('clip_merge_active') or st0.get('media_writes_pending'):
        sys.exit('Core is recording, merging or writing: nothing done')
    found = {k: st0.get(k) for k in FOUND_KEYS}
    found.update({k: st0.get(k) for k in ('lossy_dng_ratio', 'prores_profile', 'prores_color_profile', 'h264_resolution')})
    u0 = (L.web_state(3.0) or {}).get('ui') or {}
    found['ui'] = {k: u0.get(k) for k in ('record_audio_enabled', 'focus_peaking_enabled', 'zebra_enabled') if k in u0}
    found['ladder_text'] = (L.core('get_mode_ladder').get('mode_ladder') or {}).get('resolutions_text')
    found['profiles'] = L.est_profiles()
    dual0 = u0.get('dual_sensor_enabled')
    json.dump({'found': found, 'dual_sensor_enabled': dual0, 'started': time.strftime('%F %T')}, open(out + '/found.json', 'w'), indent=1)
    note('# Estimator settings check, %s' % time.strftime('%F %T'))
    note('')
    note('Core: sensor %s on %s; found %s; dual_sensor_enabled %s' % (st0.get('sensor'), st0.get('camera_port'),
         ', '.join('%s=%s' % (k, found[k]) for k in FOUND_KEYS), dual0))
    note('')

    def check(block, label, ok, detail=''):
        rows.append({'block': block, 'what': label, 'ok': ok, 'detail': detail})
        note('- %s %s %s%s' % ('OK  ' if ok else 'FAIL', block, label, (': ' + detail) if detail else ''))

    # the night's fixed state, and the dual switch
    if a.dual_off:
        r = L.core('set_dual_sensor_enabled', enabled=False)
        u = (L.web_state(3.0) or {}).get('ui') or {}
        check('fixed', 'dual sensor off', bool(r.get('ok')) and u.get('dual_sensor_enabled') is False,
              'reply %s; ui.dual_sensor_enabled=%s' % (r.get('error') or 'ok', u.get('dual_sensor_enabled')))
    for cmd, kw, key, want in (('set_fps_speed_ramp', {'enabled': False}, 'fps_speed_ramp', False),
                               ('set_clip_merge', {'enabled': False}, 'clip_merge_enabled', False),
                               ('set_mode_ladder', {'enabled': 'false'}, 'ladder_enabled', False),
                               ('set_frames_per_folder', {'value': L.SPLIT_DEFAULT}, 'frames_per_folder', L.SPLIT_DEFAULT)):
        r = L.core(cmd, **kw)
        v = L.state().get(key)
        check('fixed', '%s=%s' % (key, want), bool(r.get('ok')) and str(v) == str(want),
              '' if r.get('ok') and str(v) == str(want) else 'reply %s; read back %s' % (r.get('error') or 'ok', v))

    def one(block, spec, fps=None, lv=None):
        c = L.est_cfg(spec, **(lv or {}))
        try:
            top = L.est_top(out, c)
            if not top:
                check(block, spec, False, 'Core gives no fps for it')
                return
            f = min(int(fps or min(top, 60)), int(top))
            st = L.apply_cfg(c, f)
            bad = L.verify(c, f, st)
            tag = ' '.join('%s=%s' % kv for kv in sorted((lv or {}).items()))
            check(block, '%s @ %d%s' % (spec, f, ' [%s]' % tag if tag else ''), not bad,
                  bad or 'top %g; %s %s %s-bit' % (top, st.get('recording_format'), st.get('resolution'), st.get('raw_bit_depth')))
        except Exception as e:      # noqa: BLE001 - a check that breaks is a finding, not the end of the check
            check(block, spec, False, 'error: %r' % e)

    blocks = [b for b in a.blocks.split(',') if b]
    if 'P0' in blocks:
        for _kind, spec, f, lv in L.EST_P0:
            one('P0', spec, f, lv)
    if 'P1' in blocks:
        for spec in L.est_grid():
            one('P1', spec)
    if 'P2' in blocks:
        design = L.est_p2_design()
        for name, spec, f in L.EST_P2_ANCHORS:
            for row in design:
                one('P2 ' + name, spec, f, row)
    if 'LEV' in blocks:
        for spec in LEV_SPECS:
            one('LEV', spec, None, LEV_AWAY)
    if 'P4' in blocks:
        L.set_format('cdng')
        text = ','.join(t % (str(LADDER_TH[i]) if i < len(LADDER_TH) else '') for i, (_s, t, _f) in enumerate(LADDER))
        r = L.core('set_mode_ladder', resolutions=text, enabled='true', dry_run='true')
        check('P4', 'ladder rungs accepted (dry_run) %s' % text, bool(r.get('ok')), r.get('error') or '')
        r = L.core('set_mode_ladder', resolutions=text, enabled='true')
        check('P4', 'ladder on', bool(r.get('ok')) and bool(L.state().get('ladder_enabled')), r.get('error') or '')
        for spec, _t, f in LADDER:
            c = L.est_cfg(spec)
            c.ladder = text
            st = L.apply_ladder_take(c, f)
            bad = L.verify(c, f, st)
            check('P4', 'at %d fps the ladder picks %s' % (f, spec), not bad,
                  bad or '%s %s-bit clear_hdr=%s %s' % (st.get('resolution'), st.get('raw_bit_depth'), st.get('clear_hdr'),
                                                       st.get('cdng_compression')))
        L.core('set_mode_ladder', enabled='false')

    # restore: the runner's own restore list, then the dual switch
    L.restore_night(out, found, ['CHECK'], 'settings check')
    if a.dual_off and dual0 is not None:
        L.core('set_dual_sensor_enabled', enabled=bool(dual0))
    rs = open(out + '/restore-CHECK.txt').read().strip().splitlines()[-1]
    u = (L.web_state(3.0) or {}).get('ui') or {}
    dual_ok = dual0 is None or u.get('dual_sensor_enabled') == dual0
    nfail = sum(1 for r in rows if not r['ok'])
    note('')
    note('## Result: %d checked, %d failed; restore: %s; dual_sensor_enabled back to %s: %s; %.0f min' % (
        len(rows), nfail, rs, dual0, 'yes' if dual_ok else 'NO (%s)' % u.get('dual_sensor_enabled'), (time.time() - t0) / 60))
    with open(out + '/check.md', 'w') as f:
        f.write('\n'.join(lines) + '\n')
    with open(out + '/check.jsonl', 'w') as f:
        f.write(''.join(json.dumps(r) + '\n' for r in rows))
    return 1 if nfail or not rs.startswith('RESTORE OK') or not dual_ok else 0


if __name__ == '__main__':
    sys.exit(main())
