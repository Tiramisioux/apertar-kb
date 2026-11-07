#!/usr/bin/env python3
"""longtakes.py: unattended long-take campaign for Apertar (runs ON the Pi).

Plan: working/drop-frames/longtakes-campaign-plan.md.  Usage:
  python3 -I longtakes.py --out ~/longtakes/<session>            # run / resume the whole campaign
  python3 -I longtakes.py --out DIR --dry-run                    # list the configs only
  python3 -I longtakes.py --out DIR --max-seconds 20 --only 1    # smoke test: 1 config, takes capped at 20 s

For each config (bit depth, compression, Log, TDN, phase lock, trim, WebUI client) it records 4K Clear HDR takes
starting at the sensor's max fps and steps fps down by 1 until a take is clean for 30 min or until the drive is
full with no dropped frame ("pass_drive_full"). A take stops at the FIRST dropped frame. No cooldown waits.
Only clip folders this script created under /media/RAW are ever deleted. Audio settings are never changed.
Resume: run it again with the same --out; finished configs are skipped.
"""
import argparse, csv, itertools, json, os, re, shutil, signal, socket, subprocess, sys, threading, time

SOCK = '/tmp/apertar-core.sock'
MEDIA = '/media/RAW'
FPS_FLOOR = 25   # lowest fps tried (User, 2026-11-06)
CAPACITY_GUARD = 6 * 2**30       # stop a take (clean) when less than this is free
PI_TEMP = '/sys/class/thermal/thermal_zone0/temp'


def hwmon(name):
    for d in (os.listdir('/sys/class/hwmon') if os.path.isdir('/sys/class/hwmon') else []):
        p = '/sys/class/hwmon/' + d
        try:
            if open(p + '/name').read().strip() == name:
                return p + '/temp1_input'
        except OSError:
            pass
    return None


NVME_TEMP = hwmon('nvme')


def rd(path, default=None):
    try:
        return open(path).read().strip()
    except OSError:
        return default


def core(name, **kw):
    msg = {'cmd': name}
    for k, v in kw.items():
        msg[k] = v
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.settimeout(20)
    try:
        s.connect(SOCK)
        s.sendall((json.dumps(msg) + '\n').encode())
        buf = b''
        while True:
            while b'\n' in buf:
                line, buf = buf.split(b'\n', 1)
                if line.startswith(b'{"ok"'):
                    return json.loads(line)
            chunk = s.recv(1 << 20)
            if not chunk:
                return {'ok': False, 'error': 'socket closed'}
            buf += chunk
    except (OSError, ValueError) as e:
        return {'ok': False, 'error': str(e)}
    finally:
        s.close()


def state():
    r = core('get_state')
    return r if r.get('ok') else {}


class Cfg:
    FIELDS = ('bits', 'comp', 'log', 'tdn', 'lock', 'trim', 'web')

    def __init__(self, bits, comp, log, tdn, lock, trim, web):
        self.bits, self.comp, self.log, self.tdn, self.lock, self.trim, self.web = bits, comp, log, tdn, lock, trim, web

    @property
    def id(self):
        return '%db_%s_log%s_tdn%s_lock%s_trim%s_web%s' % (
            self.bits, 'unc' if self.comp == 'none' else 'lossless', int(self.log), int(self.tdn),
            int(self.lock), int(self.trim), int(self.web))

    def distance(self):   # number of factors away from the baseline
        return sum([self.comp != 'none', self.log, self.tdn, self.lock, not self.trim, self.web])


def all_configs():
    out = []
    for bits in (16, 12):
        cs = [Cfg(bits, comp, log, tdn, lock, trim, web)
              for comp in ('none', 'lossless_jpeg') for log in (False, True) for tdn in (False, True)
              for lock in (False, True) for trim in (True, False) for web in (False, True)]
        cs.sort(key=lambda c: (c.distance(), c.id))
        out += cs
    return out


class Sampler(threading.Thread):
    """1 Hz: temps, cpu, ram, drive fill, throttle flags, Core drop counter. Keeps every sample for the take."""
    def __init__(self, t0, csv_path):
        super().__init__(daemon=True)
        self.t0, self.stop_ev, self.rows = t0, threading.Event(), []
        self.f = open(csv_path, 'w', newline='')
        self.w = csv.writer(self.f)
        self.w.writerow(['t_s', 'pi_c', 'nvme_c', 'cpu_pct', 'load1', 'mem_avail_mb', 'fill_pct', 'free_gb',
                         'throttled', 'dropped', 'state'])
        self.prev = self.cpu_times()

    @staticmethod
    def cpu_times():
        v = [int(x) for x in open('/proc/stat').readline().split()[1:]]
        return sum(v), v[3] + v[4]

    def sample(self):
        tot, idle = self.cpu_times()
        pt, pi_ = self.prev
        cpu = 100.0 * (1 - (idle - pi_) / max(1, tot - pt))
        self.prev = (tot, idle)
        mem = 0
        for l in open('/proc/meminfo'):
            if l.startswith('MemAvailable'):
                mem = int(l.split()[1]) // 1024
        sv = os.statvfs(MEDIA)
        total, free = sv.f_blocks * sv.f_frsize, sv.f_bavail * sv.f_frsize
        thr = subprocess.run(['vcgencmd', 'get_throttled'], capture_output=True, text=True).stdout.strip().split('=')[-1]
        st = state()
        pi = int(rd(PI_TEMP, '0')) / 1000
        nv = int(rd(NVME_TEMP, '0')) / 1000 if NVME_TEMP else None
        return {'t_s': round(time.monotonic() - self.t0, 1), 'pi_c': pi, 'nvme_c': nv, 'cpu_pct': round(cpu, 1),
                'load1': os.getloadavg()[0], 'mem_avail_mb': mem, 'fill_pct': round(100 * (1 - free / total), 1),
                'free_gb': round(free / 2**30, 1), 'throttled': thr, 'dropped': st.get('recording_dropped_frames', -1),
                'state': 'rec' if st.get('recording') else str(st.get('state')), '_st': st}

    def run(self):
        while not self.stop_ev.is_set():
            r = self.sample()
            self.rows.append(r)
            self.w.writerow([r[k] for k in ('t_s', 'pi_c', 'nvme_c', 'cpu_pct', 'load1', 'mem_avail_mb', 'fill_pct',
                                              'free_gb', 'throttled', 'dropped', 'state')])
            self.f.flush()
            self.stop_ev.wait(0.5)

    def last(self):
        return self.rows[-1] if self.rows else {}


def log(out, msg):
    line = time.strftime('%F %T ') + msg
    print(line, flush=True)
    with open(out + '/runner.log', 'a') as f:
        f.write(line + '\n')


def settle(timeout=40):
    t = time.monotonic()
    while time.monotonic() - t < timeout:
        st = state()
        if st.get('state') == 'ready' and not st.get('recording'):
            return st
        time.sleep(1)
    return state()


def apply_cfg(c, fps):
    other = 12 if c.bits == 16 else 16
    core('set_clear_hdr', value=True)
    core('set_raw_bit_depth', value=other); time.sleep(5)
    core('set_raw_bit_depth', value=c.bits); time.sleep(6)
    settle()
    core('set_cdng_compression', value=c.comp)
    core('set_cdng_log', value='on' if c.log else 'off')
    core('set_preview_tdn', enabled=c.tdn)
    core('set_fps_phase_lock', enabled=c.lock)
    core('set_media_trim', enabled=c.trim)
    core('set_fps', value=float(fps))
    time.sleep(4)
    return settle()


def verify(c, fps, st):
    """Return '' if Core reports what we asked for, else the mismatch."""
    bad = []
    if st.get('raw_bit_depth') != c.bits: bad.append('bits=%s' % st.get('raw_bit_depth'))
    if st.get('cdng_compression') != c.comp: bad.append('comp=%s' % st.get('cdng_compression'))
    if bool(st.get('cdng_log_applied')) != c.log: bad.append('log_applied=%s' % st.get('cdng_log_applied'))
    if bool(st.get('preview_tdn')) != c.tdn: bad.append('tdn=%s' % st.get('preview_tdn'))
    if bool(st.get('fps_phase_lock')) != c.lock: bad.append('lock=%s' % st.get('fps_phase_lock'))
    if abs(float(st.get('fps', 0)) - fps) > 0.01: bad.append('fps=%s' % st.get('fps'))
    if st.get('resolution') != '3840x2160': bad.append('res=%s' % st.get('resolution'))
    return ' '.join(bad)


def clip_dirs():
    try:
        return {d for d in os.listdir(MEDIA) if os.path.isdir(os.path.join(MEDIA, d)) and d.startswith('cDNG')}
    except OSError:
        return set()


def clear_media(out):
    """Remove every clip folder (cDNG_*) so the next take has the whole drive (User, 2026-11-06). Other files stay."""
    n = 0
    for d in sorted(clip_dirs()):
        shutil.rmtree(os.path.join(MEDIA, d), ignore_errors=True)
        n += 1
    if n:
        log(out, 'cleared %d clip folder(s) from %s; free now %.0f GiB' % (
            n, MEDIA, os.statvfs(MEDIA).f_bavail * os.statvfs(MEDIA).f_frsize / 2**30))
        time.sleep(8)   # Core's own trim (if on) runs after a big delete; we do not wait for cooling


WEB_REMOTE = False


def web_peers():
    """Remote clients holding a connection to Core's WebUI port (loopback ones do not count)."""
    r = subprocess.run(['ss', '-tnH', 'state', 'established', '( sport = :8000 )'], capture_output=True, text=True)
    n = 0
    for l in r.stdout.splitlines():
        f = l.split()
        if len(f) >= 4 and not f[3].startswith(('127.', '[::1]', '::1')):
            n += 1
    return n


def web_flag(out, v):
    with open(out + '/web_flag', 'a') as f:
        f.write('%d\n' % v)


def wait_peers(want, timeout):
    t = time.monotonic()
    while time.monotonic() - t < timeout:
        if (web_peers() > 0) == want:
            return True
        time.sleep(1)
    return False


def ui_audio():
    import urllib.request
    try:
        u = json.load(urllib.request.urlopen('http://127.0.0.1:8000/api/state', timeout=10)).get('ui', {})
        return {k: u.get(k) for k in ('audio_sample_format', 'audio_sample_rate', 'audio_channels', 'record_audio_enabled',
                                      'audio_input_device')}
    except Exception as e:
        return {'error': str(e)}


def journal(t_wall):
    r = subprocess.run(['journalctl', '-u', 'apertar-core', '--since', '@%d' % int(t_wall), '-o', 'short-unix',
                        '--no-pager'], capture_output=True, text=True)
    return r.stdout.splitlines()


STAT_KEYS = ('enqueued', 'dropped_queue_full', 'dropped_gap_estimate', 'peak_queue', 'write_failures', 'fault')


def parse_journal(lines, t_rec_wall):
    kinds, first, stats = {}, None, {}
    trims = 0
    for l in lines:
        m = re.search(r'drop\[([a-z-]+)\]: \+(\d+)', l)
        if m:
            kinds[m.group(1)] = kinds.get(m.group(1), 0) + int(m.group(2))
            if first is None:
                try: first = float(l.split()[0]) - t_rec_wall
                except ValueError: pass
        if 'apertar-media-trim' in l and 'COMMAND' in l:
            trims += 1
        for k in STAT_KEYS:
            m = re.search(r'\b%s=([A-Za-z0-9_/]+)' % k, l)
            if m: stats[k] = m.group(1)
    return kinds, first, stats, trims


def estimate_cause(c, fps, rec, ctx, kinds, stats, written_gb_since_trim):
    """Heuristic only: every estimate is 'probable' or 'unconfirmed' (see recipe.md for the mechanisms)."""
    why = []
    q = int(stats.get('dropped_queue_full', 0) or 0)
    if c.comp == 'lossless_jpeg' and fps > 17:
        why.append('probable: lossless JPEG encoder too slow above ~17.5 fps (recipe row 2)')
    if q or 'queue-full' in kinds:
        why.append('write queue full = the drive fell behind')
        if ctx.get('fill_pct', 0) >= 75: why.append('drive >=75%% full (%.0f%%)' % ctx['fill_pct'])
        if (ctx.get('nvme_c') or 0) >= 70: why.append('NVMe hot (%.0f C), throttle possible' % ctx['nvme_c'])
        if not c.trim and written_gb_since_trim > 800:
            why.append('trim off and ~%d GB written since a trim: untrimmed-drive stall (recipe row 4)' % written_gb_since_trim)
    if 'capture-gap' in kinds:
        why.append('capture gap = CFE had no free raw buffer; ISP back end behind (memory bandwidth, '
                   'recipe section 4)' + ('; TDN on adds back-end load (row 7)' if c.tdn else '')
                   + ('; WebUI client adds preview load' if c.web else ''))
    thr = int(ctx.get('throttled', '0x0'), 16)
    if thr & 0xF: why.append('Pi throttled/under-voltage NOW (flags %s)' % ctx.get('throttled'))
    if ctx.get('mem_avail_mb', 9999) < 400: why.append('RAM available low (%d MB)' % ctx['mem_avail_mb'])
    if not why: why.append('unconfirmed: no counter or context pointed to a cause')
    return '; '.join(why)


FIELDS = ['cfg_id', 'bits', 'comp', 'log', 'tdn', 'lock', 'trim', 'web', 'fps', 'outcome', 'seconds', 'dropped',
          'first_drop_s', 'drop_kinds', 'cause_estimate', 'pi_c', 'nvme_c', 'pi_c_max', 'nvme_c_max', 'cpu_pct',
          'load1', 'mem_avail_mb', 'fill_pct', 'throttled', 'files', 'missing', 'audio', 'gb_written', 'trim_events',
          'drive_full', 'drive_full_at_s', 'start_pi_c', 'start_nvme_c', 'clip', 'stats', 'mismatch', 'started']


def append_row(out, row):
    p = out + '/results.csv'
    new = not os.path.exists(p)
    with open(p, 'a', newline='') as f:
        w = csv.DictWriter(f, FIELDS, extrasaction='ignore')
        if new: w.writeheader()
        w.writerow(row)
    write_md(out)


def load_rows(out):
    p = out + '/results.csv'
    return list(csv.DictReader(open(p))) if os.path.exists(p) else []


def write_md(out):
    rows = load_rows(out)
    sess = json.load(open(out + '/session.json')) if os.path.exists(out + '/session.json') else {}
    L = ['# Long-take campaign results', '', 'Pi: %s | Core %s | drive: %s | started %s' % (
        sess.get('pi_model'), sess.get('core_commit'), sess.get('nvme'), sess.get('started')), '',
        'Temperatures and loads are at the drop (or at the end of a clean take). Causes are estimates: '
        'probable / unconfirmed, never confirmed.',
        'Target per take: 30 min, or as long as the drive allows at these settings (pass_drive_full = clean until <6 GiB free). Every take that fills the drive is logged (drive full at s). Lowest fps tried: 25.', '',
        '| bits | comp | log | tdn | lock | trim | web | fps | outcome | s | dropped | first drop s | kinds | Pi C | NVMe C (peak) | cpu % | RAM avail MB | fill % | drive full at s | cause (estimate) |',
        '|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|']
    yn = lambda v: 'on' if v in ('True', '1', True) else 'off'
    for r in rows:
        L.append('| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s (%s) | %s | %s | %s | %s | %s |' % (
            r['bits'], 'unc' if r['comp'] == 'none' else 'lossless', yn(r['log']), yn(r['tdn']), yn(r['lock']),
            yn(r['trim']), yn(r['web']), r['fps'], r['outcome'], r['seconds'], r['dropped'], r['first_drop_s'],
            r['drop_kinds'], r['pi_c'], r['nvme_c'], r['nvme_c_max'], r['cpu_pct'], r['mem_avail_mb'],
            r['fill_pct'], r.get('drive_full_at_s', ''), r['cause_estimate']))
    best = {}
    for r in rows:
        if r['outcome'].startswith('pass'):
            best[r['cfg_id']] = r
    L += ['', '## Best clean fps per config (first pass while stepping down)', '', '| config | fps | outcome | minutes |', '|---|---|---|---|']
    for k, r in best.items():
        L.append('| %s | %s | %s | %.1f |' % (k, r['fps'], r['outcome'], float(r['seconds']) / 60))
    open(out + '/results.md', 'w').write('\n'.join(L) + '\n')


def run_take(out, c, fps, max_seconds, written):
    tid = '%s_fps%s_%s' % (c.id, int(fps), time.strftime('%H%M%S'))
    row = {'cfg_id': c.id, 'bits': c.bits, 'comp': c.comp, 'log': c.log, 'tdn': c.tdn, 'lock': c.lock,
           'trim': c.trim, 'web': c.web, 'fps': fps, 'started': time.strftime('%F %T')}
    st = apply_cfg(c, fps)
    mism = verify(c, fps, st)
    row['mismatch'] = mism
    if mism:
        row['outcome'] = 'skipped_unavailable' if 'log_applied' in mism and c.log else 'setup_mismatch'
        log(out, '%s fps=%s: %s (%s)' % (c.id, fps, row['outcome'], mism))
        return row
    if st.get('media_state') != 'mounted':
        row['outcome'] = 'media_not_mounted'
        return row
    row['start_pi_c'] = int(rd(PI_TEMP, '0')) / 1000
    row['start_nvme_c'] = int(rd(NVME_TEMP, '0')) / 1000 if NVME_TEMP else ''
    before = clip_dirs()
    web = None
    web_remote_ok = None
    if c.web and WEB_REMOTE:
        web_flag(out, 1)
        web_remote_ok = wait_peers(True, 30)
        if not web_remote_ok:
            log(out, 'WARNING: the Mac WebUI client did not connect within 30 s; this take runs without a client')
            row['mismatch'] = 'web_client_not_connected'
    elif c.web:
        web = subprocess.Popen([sys.executable, '-I', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'webui_client.py'),
                                '--host', '127.0.0.1', '--port', '8000', '--log', out + '/webui/%s.log' % tid],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(3)
    os.makedirs(out + '/samples', exist_ok=True)
    t_wall = time.time()
    t0 = time.monotonic()
    sam = Sampler(t0, out + '/samples/%s.csv' % tid)
    sam.start()
    r = core('record_start')
    t_rec_wall, t_rec = time.time(), time.monotonic()
    outcome, ctx_drop = None, None
    if not r.get('ok'):
        outcome = 'record_start_failed'
        row['cause_estimate'] = str(r.get('error'))
    while outcome is None:
        time.sleep(0.5)
        last = sam.last()
        el = time.monotonic() - t_rec
        if not last:
            continue
        if last['dropped'] and last['dropped'] > 0:
            outcome, ctx_drop = 'drop', dict(last)
        elif os.statvfs(MEDIA).f_bavail * os.statvfs(MEDIA).f_frsize < CAPACITY_GUARD:
            outcome = 'pass_drive_full'
        elif el >= (max_seconds or 1800):
            outcome = 'pass_30min' if not max_seconds else 'pass_capped_%ds' % max_seconds
        elif last['state'] != 'rec' and el > 5:
            outcome, ctx_drop = ('drive_full' if last['free_gb'] < 1.5 else 'recording_stopped_by_core'), dict(last)
        elif (last['_st'].get('recording_error') or last['_st'].get('recording_fault')):
            outcome, ctx_drop = 'fault', dict(last)
    seconds = time.monotonic() - t_rec
    ctx_end = dict(sam.last())
    core('record_stop')
    if web: web.terminate()
    if c.web and WEB_REMOTE:
        web_flag(out, 0)
        wait_peers(False, 15)
    # let Core finish the tail and write the stats line
    t = time.monotonic()
    while time.monotonic() - t < 180:
        s2 = state()
        if s2 and not s2.get('recording') and not s2.get('media_writes_pending'):
            break
        time.sleep(1)
    time.sleep(3)
    sam.stop_ev.set(); sam.join(5); sam.f.close()
    ctx = ctx_drop or ctx_end
    full = outcome in ('pass_drive_full', 'drive_full') or ctx.get('free_gb', 99) < 1.5
    row['drive_full'] = 'yes' if full else 'no'
    row['drive_full_at_s'] = round(seconds, 1) if full else ''
    new = sorted(clip_dirs() - before)
    clip = os.path.join(MEDIA, new[-1]) if new else ''
    files = missing = 0
    audio, size = '', 0
    if clip and os.path.isdir(clip):
        nums, af = [], []
        for n in os.listdir(clip):
            fp = os.path.join(clip, n)
            m = re.search(r'_(\d{9})\.dng$', n)
            if m: nums.append(int(m.group(1)))
            elif not n.endswith('.dng'): af.append('%s:%d' % (n, os.path.getsize(fp)))
        nums.sort()
        files = len(nums)
        missing = (nums[-1] + 1 - len(nums)) if nums else 0
        audio = ' '.join(af) if af else 'NONE'
    jl = journal(t_wall)
    os.makedirs(out + '/journal', exist_ok=True)
    with open(out + '/journal/%s.log' % tid, 'w') as jf:   # raw Core journal for the take, to re-check a cause later
        jf.write('\n'.join(jl) + '\n')
    kinds, first, stats, trims = parse_journal(jl, t_rec_wall)
    st_end = state()
    dropped = max(int(st_end.get('recording_dropped_frames', 0) or 0), int(ctx.get('dropped', 0) or 0), missing)
    gb = (files * (16.9 if c.bits == 16 else 12.7) / 1000) if files else 0
    pis = [x['pi_c'] for x in sam.rows]; nvs = [x['nvme_c'] for x in sam.rows if x['nvme_c']]
    row.update({
        'outcome': outcome, 'seconds': round(seconds, 1), 'dropped': dropped,
        'first_drop_s': round(first, 1) if first is not None else '',
        'drop_kinds': ' '.join('%s:%d' % kv for kv in kinds.items()),
        'pi_c': ctx.get('pi_c'), 'nvme_c': ctx.get('nvme_c'), 'pi_c_max': max(pis) if pis else '',
        'nvme_c_max': max(nvs) if nvs else '', 'cpu_pct': ctx.get('cpu_pct'), 'load1': ctx.get('load1'),
        'mem_avail_mb': ctx.get('mem_avail_mb'), 'fill_pct': ctx.get('fill_pct'), 'throttled': ctx.get('throttled'),
        'files': files, 'missing': missing, 'audio': audio, 'gb_written': round(gb, 1), 'trim_events': trims,
        'clip': os.path.basename(clip), 'stats': json.dumps(stats)})
    if outcome != 'record_start_failed':
        if dropped > 0 or outcome in ('fault', 'recording_stopped_by_core', 'drive_full'):
            written_total = written['gb'] + gb
            row['cause_estimate'] = estimate_cause(c, fps, row, ctx, kinds, stats, written_total)
            if outcome in ('fault', 'recording_stopped_by_core', 'drive_full'):
                row['cause_estimate'] = '%s: %s %s | %s' % (outcome, st_end.get('recording_error'), st_end.get('recording_fault'), row['cause_estimate'])
        else:
            row['cause_estimate'] = ''
    # delete only what this take made, then count what was written since the last trim
    if clip and os.path.isdir(clip) and clip.startswith(MEDIA + '/cDNG'):
        shutil.rmtree(clip, ignore_errors=True)
    written['gb'] = 0 if (trims or (c.trim and gb > 1)) else written['gb'] + gb
    if c.trim and gb > 1:
        time.sleep(8)   # Core's delete-batch trim runs on its own; we do not wait for cooling
    log(out, '%s fps=%s -> %s after %.0fs dropped=%s kinds=%s pi=%.0fC nvme=%s' % (
        c.id, fps, outcome, seconds, dropped, row['drop_kinds'], ctx.get('pi_c', 0), ctx.get('nvme_c')))
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--max-seconds', type=int, default=0, help='cap every take (smoke test)')
    ap.add_argument('--only', type=int, default=0, help='run only the first N unfinished configs')
    ap.add_argument('--web-remote', action='store_true',
                    help='WebUI-on takes use a real client on another machine (webui_remote.py on the Mac) instead of a local stand-in')
    ap.add_argument('--fps-start', type=float, default=0, help='override the starting fps (smoke test)')
    a = ap.parse_args()
    out = os.path.expanduser(a.out)
    global WEB_REMOTE
    WEB_REMOTE = a.web_remote
    os.makedirs(out + '/webui', exist_ok=True)
    cfgs = all_configs()
    if a.dry_run:
        for i, c in enumerate(cfgs, 1): print(i, c.id)
        print(len(cfgs), 'configs')
        return
    st0 = state()
    if not st0:
        sys.exit('Core is not answering on ' + SOCK)
    if not os.path.exists(out + '/session.json'):
        sess = {'started': time.strftime('%F %T'), 'pi_model': rd('/proc/device-tree/model', '').strip('\0'),
                'kernel': subprocess.run(['uname', '-r'], capture_output=True, text=True).stdout.strip(),
                'core_commit': subprocess.run(['git', '-C', os.path.expanduser('~/ApertarCore'), 'log', '--oneline', '-1'],
                                              capture_output=True, text=True).stdout.strip(),
                'nvme': subprocess.run(['lsblk', '-dno', 'MODEL,SIZE', '/dev/nvme0n1'], capture_output=True, text=True).stdout.strip(),
                'mount': subprocess.run(['findmnt', '-no', 'SOURCE,FSTYPE,OPTIONS', MEDIA], capture_output=True, text=True).stdout.strip(),
                'tuning_file': st0.get('tuning_file'), 'ui_running': rd('/proc/loadavg'),
                'ui_service': subprocess.run(['systemctl', 'is-active', 'apertar-ui-direct'], capture_output=True, text=True).stdout.strip(),
                'throttled_at_start': subprocess.run(['vcgencmd', 'get_throttled'], capture_output=True, text=True).stdout.strip(),
                'original_settings': {k: st0.get(k) for k in ('fps', 'raw_bit_depth', 'cdng_compression', 'cdng_log',
                                                               'preview_tdn', 'fps_phase_lock', 'fps_speed_ramp')},
                'audio': 'unchanged: record_audio_enabled, input as configured (USB PnP Sound Device hw:2,0)'}
        json.dump(sess, open(out + '/session.json', 'w'), indent=1)
        write_md(out)
    orig = json.load(open(out + '/session.json'))['original_settings']
    log(out, 'campaign start: %d configs, out=%s' % (len(cfgs), out))
    core('set_fps_speed_ramp', enabled=False)
    # The configured USB PnP Sound Device only does S16_LE mono 44.1/48 kHz; a fixed s24 format makes record_start
    # fail. Use Auto format (the device picks), keep rate and channels. The original is restored at the end.
    aud = ui_audio()
    sess = json.load(open(out + '/session.json'))
    sess.setdefault('audio_original', aud)
    sess['audio_used'] = dict(aud, audio_sample_format='auto')
    json.dump(sess, open(out + '/session.json', 'w'), indent=1)
    if aud.get('audio_sample_format') not in (None, 'auto'):
        log(out, 'audio: format %s -> auto (device is S16-only)' % aud.get('audio_sample_format'))
        core('set_audio_capture_options', format='auto')
    stop = {'now': False}
    signal.signal(signal.SIGTERM, lambda *_: stop.update(now=True))
    written = {'gb': 0}
    done_n = 0
    try:
        for c in cfgs:
            if stop['now']: break
            rows = [r for r in load_rows(out) if r['cfg_id'] == c.id]
            if any(r['outcome'].startswith('pass') or r['outcome'] in ('skipped_unavailable', 'exhausted') for r in rows):
                continue
            if a.only and done_n >= a.only: break
            done_n += 1
            apply_cfg(c, 25)
            fmax = float(state().get('fps_take_max') or state().get('fps_max') or 30)
            fps = float(int(fmax))
            if a.fps_start: fps = a.fps_start
            if rows:
                fps = min(fps, min(float(r['fps']) for r in rows) - 1)
            log(out, '== config %s: stepping down from %s fps' % (c.id, fps))
            while fps >= FPS_FLOOR and not stop['now']:
                clear_media(out)
                if os.statvfs(MEDIA).f_bavail * os.statvfs(MEDIA).f_frsize < 20 * 2**30:
                    log(out, 'drive still nearly full after clearing the clips: stopping')
                    stop['now'] = True; break
                row = run_take(out, c, fps, a.max_seconds, written)
                append_row(out, row)
                o = row.get('outcome', '')
                if o in ('media_not_mounted',):
                    log(out, 'media not mounted: campaign needs a human'); stop['now'] = True; break
                if o in ('record_start_failed', 'setup_mismatch', 'media_not_mounted'):
                    log(out, 'setup problem (%s): %s - campaign needs a human' % (o, row.get('cause_estimate') or row.get('mismatch')))
                    stop['now'] = True; break
                if o == 'skipped_unavailable': break
                if o.startswith('pass'): break
                fps -= 1
            else:
                if not stop['now']:
                    append_row(out, {'cfg_id': c.id, 'bits': c.bits, 'comp': c.comp, 'log': c.log, 'tdn': c.tdn,
                                     'lock': c.lock, 'trim': c.trim, 'web': c.web, 'fps': FPS_FLOOR, 'outcome': 'exhausted',
                                     'started': time.strftime('%F %T')})
    finally:
        for cmd, kw in (('set_preview_tdn', {'enabled': bool(orig.get('preview_tdn'))}),
                        ('set_fps_phase_lock', {'enabled': bool(orig.get('fps_phase_lock'))}),
                        ('set_media_trim', {'enabled': True}),
                        ('set_cdng_compression', {'value': orig.get('cdng_compression') or 'none'}),
                        ('set_raw_bit_depth', {'value': orig.get('raw_bit_depth') or 16}),
                        ('set_fps_speed_ramp', {'enabled': bool(orig.get('fps_speed_ramp'))}),
                        ('set_fps', {'value': float(orig.get('fps') or 25)})):
            core(cmd, **kw)
        orig_fmt = (json.load(open(out + '/session.json')).get('audio_original') or {}).get('audio_sample_format')
        if orig_fmt and orig_fmt != 'auto':
            core('set_audio_capture_options', format=orig_fmt)
        log(out, 'campaign ended (settings restored except Log, which stays as last set)')


if __name__ == '__main__':
    main()
