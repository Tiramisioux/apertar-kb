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
import argparse, csv, glob, itertools, json, os, re, shutil, signal, socket, sqlite3, subprocess, sys, threading, time

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


# The sensor modes the campaign walks through, all activated in Apertar's Mode Ladder list (User, 2026-11-07).
# (key, width, height, raw bits, Clear HDR).  Only modes the storage can carry at the lowest fps (FPS_FLOOR) are run:
# DNG bytes per frame x 25 fps must fit in DISK_MBPS (the SSD measured 354 MB/s sustained over 60 GiB, USB 3.0 UAS).
MODES = [('4kSDR12', 3840, 2160, 12, False), ('4kSDR10', 3840, 2160, 10, False),
         ('2kSDR12', 1920, 1080, 12, False), ('2kSDR10', 1920, 1080, 10, False),
         ('2kHDR16', 1920, 1080, 16, True), ('2kHDR12', 1920, 1080, 12, True),
         ('4kHDR12', 3840, 2160, 12, True), ('4kHDR16', 3840, 2160, 16, True)]
MODE_FILTER = None
DISK_MBPS = 354.0
DISK_MARGIN = 0.98


def mode_size_mb(m):
    """DNG bytes per frame in MB: width x raw height x bits / 8 (16-bit Clear HDR raw frames carry 40 extra lines)."""
    key, w, h, bits, hdr = m
    raw_h = {2160: 2200, 1080: 1100}[h] if bits == 16 else h
    return w * raw_h * bits / 8 / 1e6


def mode_possible(m):
    return mode_size_mb(m) * FPS_FLOOR <= DISK_MBPS * DISK_MARGIN


def mode_cap_fps(m):
    """Highest fps the storage can carry at all for this mode."""
    return int(DISK_MBPS * DISK_MARGIN / mode_size_mb(m))


class Cfg:
    def __init__(self, mode, comp, log, tdn, lock, trim, web):
        self.mode = mode
        self.key, self.w, self.h, self.bits, self.hdr = mode
        self.comp, self.log, self.tdn, self.lock, self.trim, self.web = comp, log, tdn, lock, trim, web

    @property
    def id(self):
        return '%s_%s_log%d_tdn%d_lock%d_trim%d_web%d' % (
            self.key, 'unc' if self.comp == 'none' else 'lossless', int(self.log), int(self.tdn),
            int(self.lock), int(self.trim), int(self.web))

    def distance(self):   # number of factors away from the baseline
        return sum([self.comp != 'none', self.log, self.tdn, self.lock, not self.trim, self.web])


def included_modes():
    return [m for m in MODES if (m[0] in MODE_FILTER if MODE_FILTER else mode_possible(m))]


def all_configs():
    """Stage order: (1) the baseline of every mode, (d) every config one factor away from its baseline, (r) the rest."""
    base, d1, rest = [], [], []
    for mode in included_modes():
        cs = [Cfg(mode, comp, log, tdn, lock, trim, web)
              for comp in ('none', 'lossless_jpeg') for log in (False, True) for tdn in (False, True)
              for lock in (False, True) for trim in (True, False) for web in (False, True)]
        cs.sort(key=lambda c: (c.distance(), c.id))
        base.append(cs[0])
        d1 += [c for c in cs[1:] if c.distance() == 1]
        rest += [c for c in cs[1:] if c.distance() > 1]
    return base + d1 + rest


def config_score(rows):
    """Rank a config's takes: a pass beats everything (higher fps first, then longer); otherwise the longest take."""
    rows = [r for r in rows if r['outcome'] not in ('exhausted', 'stopped_externally', 'skipped_unavailable')
            and not r.get('variant')]
    if not rows:
        return None
    passes = [r for r in rows if r['outcome'].startswith('pass')]
    if passes:
        b = max(passes, key=lambda r: (float(r['fps']), float(r['seconds'] or 0)))
        return (1, float(b['fps']), float(b['seconds'] or 0))
    return (0, 0.0, max(float(r['seconds'] or 0) for r in rows))


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
    # Clear HDR and the resolution first, then a bit-depth round trip so every take starts from a fresh camera config.
    # (set_clear_hdr takes `enabled`; set_resolution takes width and height.)
    st = state()
    if bool(st.get('clear_hdr')) != c.hdr:
        core('set_clear_hdr', enabled=c.hdr); time.sleep(4)
    if st.get('resolution') != '%dx%d' % (c.w, c.h):
        core('set_resolution', width=c.w, height=c.h); time.sleep(4)
    other = {16: 12, 12: (16 if c.hdr else 10), 10: 12}[c.bits]
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
    if st.get('resolution') != '%dx%d' % (c.w, c.h): bad.append('res=%s' % st.get('resolution'))
    if bool(st.get('clear_hdr')) != c.hdr: bad.append('clear_hdr=%s' % st.get('clear_hdr'))
    return ' '.join(bad)


def clip_dirs():
    try:
        return {d for d in os.listdir(MEDIA) if os.path.isdir(os.path.join(MEDIA, d)) and d.startswith('cDNG')}
    except OSError:
        return set()


PRESERVE = set()      # clip folders that were on the drive when the campaign started: never deleted
CLEAR_ALL = False


def dropped_none(row):
    return int(_num(row.get('dropped')) or 0) == 0


def clear_media(out):
    """Remove leftover clip folders so the next take has the room. Folders that were there when the campaign started
    stay unless --clear-all was given (the 2026-11-07 drive holds 143 GB of older takes)."""
    n = 0
    for d in sorted(clip_dirs() - (set() if CLEAR_ALL else PRESERVE)):
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


# ---- SQLite database (User, 2026-11-07): while the next take is being set up, the previous take's logs go into
# <run>/longtakes.db (takes, samples, drop_events, stats, journal). One file, stdlib only, nothing runs during a recording.
DB_SCHEMA = '''
CREATE TABLE IF NOT EXISTS session(k TEXT PRIMARY KEY, v TEXT);
CREATE TABLE IF NOT EXISTS takes(take_id TEXT PRIMARY KEY, cfg_id TEXT, mode TEXT, bits INT, comp TEXT, log INT, tdn INT, lock INT,
  trim INT, web INT, fps REAL, outcome TEXT, seconds REAL, dropped INT, first_drop_s REAL, drop_kinds TEXT,
  cause_estimate TEXT, pi_c REAL, nvme_c REAL, pi_c_max REAL, nvme_c_max REAL, cpu_pct REAL, load1 REAL,
  mem_avail_mb REAL, fill_pct REAL, throttled TEXT, files INT, missing INT, audio TEXT, gb_written REAL,
  trim_events INT, drive_full TEXT, drive_full_at_s REAL, start_pi_c REAL, start_nvme_c REAL, clip TEXT,
  started TEXT, mismatch TEXT, variant TEXT, media_class TEXT, buffer_setting TEXT, buffer_safety_stop TEXT,
  buffer_flush_discarded TEXT, tune_readback TEXT);
CREATE TABLE IF NOT EXISTS samples(take_id TEXT, t_s REAL, pi_c REAL, nvme_c REAL, cpu_pct REAL, load1 REAL,
  mem_avail_mb REAL, fill_pct REAL, free_gb REAL, throttled TEXT, dropped INT, state TEXT);
CREATE INDEX IF NOT EXISTS samples_take ON samples(take_id);
CREATE TABLE IF NOT EXISTS drop_events(take_id TEXT, t_unix REAL, t_rel_s REAL, kind TEXT, frames INT, dt_us INT,
  nominal_us INT);
CREATE INDEX IF NOT EXISTS drop_take ON drop_events(take_id);
CREATE TABLE IF NOT EXISTS stats(take_id TEXT, k TEXT, v TEXT);
CREATE TABLE IF NOT EXISTS journal(take_id TEXT, t_unix REAL, line TEXT);
CREATE INDEX IF NOT EXISTS journal_take ON journal(take_id);
CREATE VIEW IF NOT EXISTS config_summary AS
  SELECT cfg_id, mode, bits, comp, log, tdn, lock, trim, web, COUNT(*) AS takes, MAX(seconds) AS best_seconds,
         (SELECT t2.fps FROM takes t2 WHERE t2.cfg_id = takes.cfg_id ORDER BY t2.seconds DESC LIMIT 1) AS best_fps,
         MAX(outcome LIKE 'pass%') AS passed, MAX(drive_full = 'yes') AS filled_drive
  FROM takes GROUP BY cfg_id;
'''


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _flag(v):
    return 1 if str(v) in ('True', '1') else 0


def db_ingest(out, row, payload):
    """Write one take (row = the results.csv row, payload = samples + raw journal lines) to longtakes.db. Idempotent."""
    tid = row.get('take_id')
    if not tid:
        return
    con = sqlite3.connect(out + '/longtakes.db', timeout=60)
    try:
        con.executescript(DB_SCHEMA)
        for t in ('takes', 'samples', 'drop_events', 'stats', 'journal'):
            con.execute('DELETE FROM %s WHERE take_id=?' % t, (tid,))
        r = row
        con.execute('INSERT INTO takes VALUES (%s)' % ','.join('?' * 44), (
            tid, r.get('cfg_id'), r.get('mode'), int(r.get('bits') or 0), r.get('comp'), _flag(r.get('log')), _flag(r.get('tdn')),
            _flag(r.get('lock')), _flag(r.get('trim')), _flag(r.get('web')), _num(r.get('fps')), r.get('outcome'),
            _num(r.get('seconds')), int(_num(r.get('dropped')) or 0), _num(r.get('first_drop_s')), r.get('drop_kinds'),
            r.get('cause_estimate'), _num(r.get('pi_c')), _num(r.get('nvme_c')), _num(r.get('pi_c_max')),
            _num(r.get('nvme_c_max')), _num(r.get('cpu_pct')), _num(r.get('load1')), _num(r.get('mem_avail_mb')),
            _num(r.get('fill_pct')), r.get('throttled'), int(_num(r.get('files')) or 0), int(_num(r.get('missing')) or 0),
            r.get('audio'), _num(r.get('gb_written')), int(_num(r.get('trim_events')) or 0), r.get('drive_full'),
            _num(r.get('drive_full_at_s')), _num(r.get('start_pi_c')), _num(r.get('start_nvme_c')), r.get('clip'),
            r.get('started'), r.get('mismatch'), r.get('variant'), r.get('media_class'), r.get('buffer_setting'),
            r.get('buffer_safety_stop'), r.get('buffer_flush_discarded'), r.get('tune_readback')))
        con.executemany('INSERT INTO samples VALUES (?,?,?,?,?,?,?,?,?,?,?,?)', [
            (tid, x.get('t_s'), x.get('pi_c'), x.get('nvme_c'), x.get('cpu_pct'), x.get('load1'), x.get('mem_avail_mb'),
             x.get('fill_pct'), x.get('free_gb'), x.get('throttled'), x.get('dropped'), x.get('state'))
            for x in payload.get('samples', [])])
        lines = payload.get('journal', [])
        t_rec = payload.get('t_rec_wall')
        for l in lines:
            m = re.match(r'(\d+\.\d+) ', l)
            if m and 'recording clip:' in l and t_rec is None:
                t_rec = float(m.group(1))
        ev, jl = [], []
        for l in lines:
            m = re.match(r'(\d+\.\d+) ', l)
            t = float(m.group(1)) if m else None
            jl.append((tid, t, l))
            d = re.search(r'drop\[([a-z-]+)\]: \+(\d+).*?dt_us=(\d+) nominal_us=(\d+)', l)
            if d and t is not None:
                ev.append((tid, t, round(t - t_rec, 3) if t_rec else None, d.group(1), int(d.group(2)),
                           int(d.group(3)), int(d.group(4))))
        con.executemany('INSERT INTO drop_events VALUES (?,?,?,?,?,?,?)', ev)
        con.executemany('INSERT INTO journal VALUES (?,?,?)', jl)
        try:
            stats = json.loads(row.get('stats') or '{}')
        except ValueError:
            stats = {}
        con.executemany('INSERT INTO stats VALUES (?,?,?)', [(tid, k, str(v)) for k, v in stats.items()])
        con.commit()
    finally:
        con.close()


INGEST = {'t': None}


def start_ingest(out, row, payload):
    join_ingest()

    def work():
        try:
            db_ingest(out, row, payload or {})
        except Exception as e:      # the database must never stop the campaign
            log(out, 'WARNING: database ingest failed for %s: %s' % (row.get('take_id'), e))
    INGEST['t'] = threading.Thread(target=work, daemon=True)
    INGEST['t'].start()


def join_ingest():
    t = INGEST['t']
    if t is not None:
        t.join(120)
        INGEST['t'] = None


def backfill(out):
    """Put takes from results.csv that are not in the database yet (older runs, or a crash) into it."""
    try:
        con = sqlite3.connect(out + '/longtakes.db', timeout=60)
        con.executescript(DB_SCHEMA)
        have = {r[0] for r in con.execute('SELECT take_id FROM takes')}
        con.close()
    except sqlite3.Error as e:
        log(out, 'WARNING: database not usable: %s' % e)
        return
    n = 0
    for r in load_rows(out):
        if r.get('outcome') == 'exhausted':
            continue
        tid = r.get('take_id')
        if not tid:
            g = sorted(glob.glob('%s/samples/%s_fps%d_*.csv' % (out, r['cfg_id'], int(float(r['fps'])))))
            if not g:
                continue
            tid = os.path.basename(g[-1])[:-4]
            r['take_id'] = tid
        if tid in have:
            continue
        sam = []
        sp = '%s/samples/%s.csv' % (out, tid)
        if os.path.exists(sp):
            sam = list(csv.DictReader(open(sp)))
        jp = '%s/journal/%s.log' % (out, tid)
        jl = open(jp).read().splitlines() if os.path.exists(jp) else []
        db_ingest(out, r, {'samples': sam, 'journal': jl})
        n += 1
    if n:
        log(out, 'database: backfilled %d earlier take(s)' % n)


FIELDS = ['take_id', 'cfg_id', 'mode', 'bits', 'comp', 'log', 'tdn', 'lock', 'trim', 'web', 'fps', 'outcome', 'seconds', 'dropped',
          'first_drop_s', 'drop_kinds', 'cause_estimate', 'pi_c', 'nvme_c', 'pi_c_max', 'nvme_c_max', 'cpu_pct',
          'load1', 'mem_avail_mb', 'fill_pct', 'throttled', 'files', 'missing', 'audio', 'gb_written', 'trim_events',
          'drive_full', 'drive_full_at_s', 'start_pi_c', 'start_nvme_c', 'clip', 'stats', 'mismatch', 'started', 'variant', 'media_class', 'buffer_setting',
          'buffer_safety_stop', 'buffer_flush_discarded', 'tune_readback']


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
        '| mode | comp | log | tdn | lock | trim | web | fps | outcome | s | dropped | first drop s | kinds | Pi C | NVMe C (peak) | cpu % | RAM avail MB | fill % | drive full at s | cause (estimate) |',
        '|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|']
    yn = lambda v: 'on' if v in ('True', '1', True) else 'off'
    for r in rows:
        L.append('| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s (%s) | %s | %s | %s | %s | %s |' % (
            r.get('mode') or r['bits'], 'unc' if r['comp'] == 'none' else 'lossless', yn(r['log']), yn(r['tdn']), yn(r['lock']),
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


# ---- Storage tuning A/B (User, 2026-11-07). Core re-reads the media tuning files when a take starts, so workers, queue,
# sync_ms and raw_buffers change between takes through the override file; kernel_tune (dirty pages, scheduler,
# nr_requests, rq_affinity via the root helper) is applied when the drive is mounted, so it is switched by eject + mount.
AB_VARIANTS = [('base', {}), ('workers2', {'workers': 2}), ('workers6', {'workers': 6}), ('queue24', {'queue': 24}),
               ('queue48', {'queue': 48}), ('sync500', {'sync_ms': 500}), ('sync2000', {'sync_ms': 2000}),
               ('rawbuf12', {'raw_buffers': 12}), ('kerneltune', {'kernel_tune': 'on'})]
KT = {'on': False, 'dev': '/dev/sda1'}
TUNE_CLI = os.path.expanduser('~/ApertarCore/scripts/apertar-tune')


def sh(args):
    r = subprocess.run(args, capture_output=True, text=True)
    return r.returncode, (r.stdout + r.stderr).strip()


def kernel_readback():
    dev = os.path.basename(KT['dev']).rstrip('0123456789')
    f = lambda p: (rd(p, '?') or '?').replace('\n', ' ')
    sched = f('/sys/block/%s/queue/scheduler' % dev)
    return 'dirty_bytes=%s dirty_bg=%s writeback_cs=%s sched=%s nr_requests=%s rq_affinity=%s' % (
        f('/proc/sys/vm/dirty_bytes'), f('/proc/sys/vm/dirty_background_bytes'), f('/proc/sys/vm/dirty_writeback_centisecs'),
        sched, f('/sys/block/%s/queue/nr_requests' % dev), f('/sys/block/%s/queue/rq_affinity' % dev))


def set_variant(out, name, settings):
    """Put the override file in the state for this variant; switch kernel_tune by remounting if it changed."""
    sh([sys.executable, TUNE_CLI, 'clear'])
    if settings:
        rc, msg = sh([sys.executable, TUNE_CLI, 'set'] + ['%s=%s' % kv for kv in settings.items()])
        if rc:
            log(out, 'WARNING: apertar-tune set %s failed: %s' % (settings, msg[:200]))
    want = settings.get('kernel_tune') == 'on'
    if want != KT['on']:
        # Call the root helper the way Core does (sudo -n, allowed for apertar-media-tune) instead of remounting: an
        # eject powers a USB drive off (2026-11-07: the SSD vanished from the bus and needed a replug).
        root = os.path.basename(KT['dev']).rstrip('0123456789')
        rc, msg = sh(['sudo', '-n', '/usr/local/libexec/apertar-media-tune', 'apply' if want else 'restore', root,
                      KT.get('class', 'usb-storage'), 'exfat'])
        log(out, 'variant %s: kernel tuning %s (%s class) rc=%d: %s' % (
            name, 'applied' if want else 'restored', KT.get('class', 'usb-storage'), rc, msg.replace('\n', ' | ')[:240]))
        KT['on'] = want
    return kernel_readback()


def run_take(out, c, fps, max_seconds, written, stop_on_drop=True, variant='', tune_note=''):
    tid = '%s_fps%s_%s' % (c.id, int(fps), time.strftime('%H%M%S'))
    row = {'take_id': tid, 'cfg_id': c.id, 'mode': c.key, 'bits': c.bits, 'comp': c.comp, 'log': c.log, 'tdn': c.tdn, 'lock': c.lock,
           'trim': c.trim, 'web': c.web, 'fps': fps, 'started': time.strftime('%F %T'), 'variant': variant,
           'tune_readback': tune_note}
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
    join_ingest()      # the previous take's logs went into the database while this one was being set up
    os.makedirs(out + '/samples', exist_ok=True)
    t_wall = time.time()
    t0 = time.monotonic()
    sam = Sampler(t0, out + '/samples/%s.csv' % tid)
    sam.start()
    r = core('record_start')
    if not r.get('ok') and 'not supported by this device' in str(r.get('error')):
        log(out, 'audio format rejected by the device: switching the audio format to auto (restored at the end)')
        core('set_audio_capture_options', format='auto')
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
        if stop_on_drop and last['dropped'] and last['dropped'] > 0:
            outcome, ctx_drop = 'drop', dict(last)
        elif os.statvfs(MEDIA).f_bavail * os.statvfs(MEDIA).f_frsize < CAPACITY_GUARD:
            outcome = 'pass_drive_full'
        elif el >= (max_seconds or 1800):
            outcome = 'pass_30min' if not max_seconds else 'pass_capped_%ds' % max_seconds
        elif last['state'] != 'rec' and el > 5:
            outcome, ctx_drop = ('drive_full' if last['free_gb'] < 1.5 else 'stopped_externally'), dict(last)
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
    row['buffer_setting'] = st_end.get('buffer_setting')
    row['buffer_safety_stop'] = st_end.get('buffer_safety_stop')
    row['buffer_flush_discarded'] = st_end.get('buffer_flush_discarded')
    for l in jl:
        m = re.search(r'recording clip: .*?media_class=([a-z-]+)', l)
        if m:
            row['media_class'] = m.group(1)
    dropped = max(int(st_end.get('recording_dropped_frames', 0) or 0), int(ctx.get('dropped', 0) or 0), missing)
    gb = 0
    if clip and os.path.isdir(clip) and files:
        names = [n for n in os.listdir(clip) if n.endswith('.dng')][:20]
        if names:
            gb = files * (sum(os.path.getsize(os.path.join(clip, n)) for n in names) / len(names)) / 1e9
    if not stop_on_drop and outcome.startswith('pass'):
        outcome = 'ab_clean' if dropped == 0 else 'ab_dropped'
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
        if dropped > 0 or outcome in ('fault', 'recording_stopped_by_core', 'drive_full', 'stopped_externally'):
            written_total = written['gb'] + gb
            row['cause_estimate'] = estimate_cause(c, fps, row, ctx, kinds, stats, written_total)
            if outcome in ('fault', 'recording_stopped_by_core', 'drive_full', 'stopped_externally'):
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
    row['_payload'] = {'samples': [{k: v for k, v in x.items() if k != '_st'} for x in sam.rows], 'journal': jl,
                       't_rec_wall': t_rec_wall}
    return row


def main():
    global WEB_REMOTE, CLEAR_ALL, MODE_FILTER, DISK_MBPS, AB_VARIANTS
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--max-seconds', type=int, default=0, help='cap every stage-1/3 take (smoke test)')
    ap.add_argument('--only', type=int, default=0, help='run only the first N unfinished configs')
    ap.add_argument('--web-remote', action='store_true',
                    help='WebUI-on takes use a real client on another machine (webui_remote.py on the Mac) instead of a local stand-in')
    ap.add_argument('--clear-all', action='store_true', help='also delete clip folders that were on the drive at the start')
    ap.add_argument('--modes', default='', help='comma list of mode keys to run (default: every mode the storage can carry)')
    ap.add_argument('--fps-start', type=float, default=0, help='override the starting fps (smoke test)')
    ap.add_argument('--disk-mbps', type=float, default=DISK_MBPS, help='sustained write speed of the drive, MB/s')
    ap.add_argument('--stages', default='1d2r', help='1 = baseline of every mode, d = configs one factor away, 2 = storage A/B on the best configs, r = the rest')
    ap.add_argument('--ab-seconds', type=int, default=120, help='length of one A/B take')
    ap.add_argument('--ab-variants', default='', help='comma list of A/B variants to run (default: all)')
    ap.add_argument('--ab-reps', type=int, default=3, help='repeats of every A/B variant (interleaved)')
    a = ap.parse_args()
    out = os.path.expanduser(a.out)
    if a.ab_variants:
        AB_VARIANTS = [v for v in AB_VARIANTS if v[0] in a.ab_variants.split(',')]
    WEB_REMOTE, CLEAR_ALL, DISK_MBPS = a.web_remote, a.clear_all, a.disk_mbps
    MODE_FILTER = [m for m in a.modes.split(',') if m] or None
    os.makedirs(out + '/webui', exist_ok=True)
    cfgs = all_configs()
    inc = included_modes()
    excl = [m for m in MODES if m not in inc]
    n_base = len(inc)
    n_d1 = sum(1 for c in cfgs if c.distance() == 1)
    if a.dry_run:
        for m in MODES:
            print('%-8s %5.2f MB/frame  %4.0f MB/s at %d fps (%3.0f%% of %.0f)  storage cap %d fps  %s' % (
                m[0], mode_size_mb(m), mode_size_mb(m) * FPS_FLOOR, FPS_FLOOR, 100 * mode_size_mb(m) * FPS_FLOOR / DISK_MBPS,
                DISK_MBPS, mode_cap_fps(m), 'RUN' if m in inc else 'excluded: storage too slow'))
        print('stage 1: %d baseline configs; d: %d single-factor configs; 2: A/B on the best config of each mode at >= 70%% of '
              'the disk speed (+ the baseline); r: %d other configs' % (n_base, n_d1, len(cfgs) - n_base - n_d1))
        print('A/B variants:', ', '.join(v for v, _ in AB_VARIANTS))
        return
    st0 = state()
    if not st0:
        sys.exit('Core is not answering on ' + SOCK)
    src = subprocess.run(['findmnt', '-no', 'SOURCE', MEDIA], capture_output=True, text=True).stdout.strip()
    KT['dev'] = src or KT['dev']
    parent = subprocess.run(['lsblk', '-no', 'pkname', src], capture_output=True, text=True).stdout.strip().splitlines()
    parent = '/dev/' + parent[0] if parent else src
    if not os.path.exists(out + '/session.json'):
        sess = {'started': time.strftime('%F %T'), 'pi_model': rd('/proc/device-tree/model', '').strip('\0'),
                'kernel': subprocess.run(['uname', '-r'], capture_output=True, text=True).stdout.strip(),
                'core_commit': subprocess.run(['git', '-C', os.path.expanduser('~/ApertarCore'), 'log', '--oneline', '-1'],
                                              capture_output=True, text=True).stdout.strip(),
                'drive': subprocess.run(['lsblk', '-dno', 'MODEL,SIZE,TRAN', parent], capture_output=True, text=True).stdout.strip(),
                'mount': subprocess.run(['findmnt', '-no', 'SOURCE,FSTYPE,OPTIONS', MEDIA], capture_output=True, text=True).stdout.strip(),
                'disk_mbps_sustained': DISK_MBPS,
                'modes_run': [(m[0], round(mode_size_mb(m), 2), mode_cap_fps(m)) for m in inc],
                'modes_excluded_storage_too_slow': [(m[0], round(mode_size_mb(m) * FPS_FLOOR)) for m in excl],
                'tuning_file': st0.get('tuning_file'), 'ui_running': rd('/proc/loadavg'),
                'ui_service': subprocess.run(['systemctl', 'is-active', 'apertar-ui-direct'], capture_output=True, text=True).stdout.strip(),
                'throttled_at_start': subprocess.run(['vcgencmd', 'get_throttled'], capture_output=True, text=True).stdout.strip(),
                'kernel_tune_readback_at_start': kernel_readback(),
                'original_settings': {k: st0.get(k) for k in ('fps', 'raw_bit_depth', 'cdng_compression', 'cdng_log',
                                                               'preview_tdn', 'fps_phase_lock', 'fps_speed_ramp', 'clear_hdr', 'resolution')},
                'pi_revision': next((l.split(':')[1].strip() for l in open('/proc/cpuinfo') if l.startswith('Revision')), ''),
                'pi_mac_eth0': rd('/sys/class/net/eth0/address'),
                'preexisting_clips': sorted(clip_dirs()),
                'audio': 'as configured in Core (input and levels unchanged)'}
        json.dump(sess, open(out + '/session.json', 'w'), indent=1)
        write_md(out)
    orig = json.load(open(out + '/session.json'))['original_settings']
    backfill(out)
    try:
        con = sqlite3.connect(out + '/longtakes.db', timeout=60)
        con.executescript(DB_SCHEMA)
        for k, v in json.load(open(out + '/session.json')).items():
            con.execute('INSERT OR REPLACE INTO session VALUES (?,?)', (k, json.dumps(v)))
        con.commit(); con.close()
    except sqlite3.Error as e:
        log(out, 'WARNING: database session info failed: %s' % e)
    PRESERVE.update(json.load(open(out + '/session.json')).get('preexisting_clips', []))
    log(out, 'preserving %d pre-existing clip folder(s)%s' % (len(PRESERVE), ' (--clear-all: they WILL be deleted)' if CLEAR_ALL else ''))
    log(out, 'campaign start: modes %s; excluded (storage too slow at %d fps): %s; %d configs; drive %.0f MB/s; out=%s' % (
        [m[0] for m in inc], FPS_FLOOR, [m[0] for m in excl], len(cfgs), DISK_MBPS, out))
    core('set_fps_speed_ramp', enabled=False)
    aud = ui_audio()
    sess = json.load(open(out + '/session.json'))
    sess.setdefault('audio_original', aud)
    json.dump(sess, open(out + '/session.json', 'w'), indent=1)
    stop = {'now': False}
    signal.signal(signal.SIGTERM, lambda *_: stop.update(now=True))
    written = {'gb': 0}
    ext_stops = {}
    counter = {'n': 0}

    def take(c, fps, **kw):
        row = run_take(out, c, fps, kw.pop('max_seconds', a.max_seconds), written, **kw)
        payload = row.pop('_payload', None)
        append_row(out, row)
        start_ingest(out, row, payload)     # runs while the next take is set up
        if row.get('media_class'):
            KT['class'] = row['media_class']
        o = row.get('outcome', '')
        if o in ('record_start_failed', 'setup_mismatch', 'media_not_mounted'):
            log(out, 'setup problem (%s): %s - campaign needs a human' % (o, row.get('cause_estimate') or row.get('mismatch')))
            stop['now'] = True
        return row

    def walk_config(c):
        """Step fps down from the mode's storage cap until a take passes (30 min or drive full)."""
        rows = [r for r in load_rows(out) if r['cfg_id'] == c.id and not r.get('variant')]
        if any(r['outcome'].startswith('pass') or r['outcome'] in ('skipped_unavailable', 'exhausted') for r in rows):
            return
        if a.only and counter['n'] >= a.only:
            stop['now'] = True
            return
        counter['n'] += 1
        apply_cfg(c, 25)
        fmax = float(state().get('fps_take_max') or state().get('fps_max') or 30)
        fps = float(int(min(fmax, mode_cap_fps(c.mode))))
        if a.fps_start: fps = a.fps_start
        rows = [r for r in rows if r['outcome'] != 'stopped_externally']
        if rows:
            fps = min(fps, min(float(r['fps']) for r in rows) - 1)
        log(out, '== config %s: stepping down from %s fps (storage cap %d, mode max %.0f)' % (c.id, fps, mode_cap_fps(c.mode), fmax))
        while fps >= FPS_FLOOR and not stop['now']:
            clear_media(out)
            if os.statvfs(MEDIA).f_bavail * os.statvfs(MEDIA).f_frsize < 20 * 2**30:
                log(out, 'drive still nearly full after clearing the clips: stopping')
                stop['now'] = True; break
            row = take(c, fps)
            o = row.get('outcome', '')
            if stop['now']: break
            if o == 'stopped_externally' and dropped_none(row):
                ext_stops[c.id] = ext_stops.get(c.id, 0) + 1
                log(out, 'take stopped by someone else with no drop (%ds): not a result; retrying %s fps (%d/2)' % (
                    float(row.get('seconds') or 0), fps, ext_stops[c.id]))
                if ext_stops[c.id] <= 2:
                    continue
                stop['now'] = True; break
            if o == 'skipped_unavailable': break
            if o.startswith('pass'): break
            fps -= 1
        else:
            if not stop['now']:
                append_row(out, {'cfg_id': c.id, 'mode': c.key, 'bits': c.bits, 'comp': c.comp, 'log': c.log, 'tdn': c.tdn,
                                 'lock': c.lock, 'trim': c.trim, 'web': c.web, 'fps': FPS_FLOOR, 'outcome': 'exhausted',
                                 'started': time.strftime('%F %T')})

    def ab_stage():
        """Short A/B takes of the storage tuning on the best setups: per mode the best config found so far (a pass beats
        a drop, then higher fps, then longer) plus the plain baseline when that is a different config. Only modes that
        need >= 70% of the disk speed. Fps = the first fps above where the config was clean (or 25 if it never was).
        Every take runs its full length (no stop at the first drop); the metric is dropped frames and queue peak."""
        rows_all = load_rows(out)
        for m in inc:
            mine = [c for c in cfgs if c.mode == m]
            scored = [(config_score([r for r in rows_all if r['cfg_id'] == c.id]), c) for c in mine]
            scored = [(sc, c) for sc, c in scored if sc is not None]
            if not scored:
                continue
            best = max(scored, key=lambda t: t[0])[1]
            targets = [best] + ([mine[0]] if mine[0].id != best.id and config_score(
                [r for r in rows_all if r['cfg_id'] == mine[0].id]) is not None else [])
            for c in targets:
                if stop['now']: return
                base_rows = [r for r in rows_all if r['cfg_id'] == c.id and not r.get('variant')]
                passes = sorted(int(float(r['fps'])) for r in base_rows if r['outcome'].startswith('pass'))
                cap = mode_cap_fps(m)
                ab_fps = (passes[-1] + 1 if passes[-1] + 1 <= cap else passes[-1]) if passes else FPS_FLOOR
                util = mode_size_mb(m) * ab_fps / DISK_MBPS
                if util < 0.70:
                    log(out, 'A/B %s %s: skipped, %.0f%% of the disk speed at %d fps (not storage-limited)' % (m[0], c.id, 100 * util, ab_fps))
                    continue
                log(out, '== A/B %s%s at %d fps (%.0f%% of the disk speed): %d variants x %d reps, %d s each' % (
                    c.id, ' (best)' if c is best else ' (baseline)', ab_fps, 100 * util, len(AB_VARIANTS), a.ab_reps, a.ab_seconds))
                done = collections_count(load_rows(out), c.id)
                for rep in range(a.ab_reps):
                    for vname, settings in AB_VARIANTS:
                        if stop['now']: return
                        if done.get(vname, 0) > rep: continue
                        clear_media(out)
                        note = set_variant(out, vname, settings)
                        for attempt in range(3):      # a take stopped by someone else is not a result: run it again
                            row = take(c, ab_fps, max_seconds=a.ab_seconds, stop_on_drop=False, variant=vname, tune_note=note)
                            if stop['now'] or not (row.get('outcome') == 'stopped_externally' and dropped_none(row)):
                                break
                            log(out, 'A/B take stopped by someone else (%ss): repeating (%d/2)' % (row.get('seconds'), attempt + 1))
                            clear_media(out)
                        log(out, 'A/B %s rep %d %s: %s dropped=%s' % (c.id, rep + 1, vname, row.get('outcome'), row.get('dropped')))
                set_variant(out, 'base', {})

    try:
        if '1' in a.stages:
            for c in cfgs[:n_base]:
                if stop['now']: break
                walk_config(c)
        if 'd' in a.stages:
            for c in cfgs[n_base:n_base + n_d1]:
                if stop['now']: break
                walk_config(c)
        if '2' in a.stages and not stop['now']:
            ab_stage()
        if 'r' in a.stages:
            for c in cfgs[n_base + n_d1:]:
                if stop['now']: break
                walk_config(c)
    finally:
        try:
            set_variant(out, 'base', {})      # override file cleared; kernel tuning restored if it was on
        except Exception as e:
            log(out, 'WARNING: could not restore the tuning override: %s' % e)
        ow, oh = (orig.get('resolution') or '3840x2160').split('x')
        for cmd, kw in (('set_clear_hdr', {'enabled': bool(orig.get('clear_hdr', True))}),
                        ('set_resolution', {'width': int(ow), 'height': int(oh)}),
                        ('set_preview_tdn', {'enabled': bool(orig.get('preview_tdn'))}),
                        ('set_fps_phase_lock', {'enabled': bool(orig.get('fps_phase_lock'))}),
                        ('set_media_trim', {'enabled': True}),
                        ('set_cdng_compression', {'value': orig.get('cdng_compression') or 'none'}),
                        ('set_raw_bit_depth', {'value': orig.get('raw_bit_depth') or 16}),
                        ('set_fps_speed_ramp', {'enabled': bool(orig.get('fps_speed_ramp'))}),
                        ('set_fps', {'value': float(orig.get('fps') or 25)})):
            core(cmd, **kw)
        join_ingest()
        orig_fmt = (json.load(open(out + '/session.json')).get('audio_original') or {}).get('audio_sample_format')
        if orig_fmt and orig_fmt != 'auto':
            core('set_audio_capture_options', format=orig_fmt)
        log(out, 'campaign ended (settings restored except Log, which stays as last set)')


def collections_count(rows, cfg_id):
    d = {}
    for r in rows:
        if r['cfg_id'] == cfg_id and r.get('variant') and r['outcome'].startswith('ab_'):
            d[r['variant']] = d.get(r['variant'], 0) + 1
    return d


if __name__ == '__main__':
    main()
