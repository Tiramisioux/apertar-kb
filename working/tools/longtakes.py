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

Added 2026-11-08 (storage-slowdown plan): every 1 Hz sample also carries Core's write-buffer level (buffer_used/capacity),
the recording disk's /sys/block stat counters (writes, sectors, write ticks, in flight: the device's own latency), Dirty and
Writeback from /proc/meminfo and Core's trim state; every take carries the RAM budget in MiB and in seconds of input, the
recorder's stop time and whether Core logged "nothing was written" at the stop, the idle gap since the previous take, the
slope of Core's CPU over the take (the directory-walk signature) and whether a trim finished since the previous take. DNGs
are counted recursively (a clip split into part_*/ folders counts the same). Analysis: longtakes_fill.py.

Unattended ladder (same date, plan section 7 and 7.1): before every take, and before every camera mode switch or clip
clean-up, the runner waits for a quiet Pi (no other probe or build, Core awake, ready and not recording, medium mounted, no
under-voltage, enough free space, no other session's lock under /run/apertar-media), checks the kernel log and media_alive
(watchdog: stops the campaign, never retries) and the write budget (--budget-gb). One runner per --out (an instance lock); a
DONE marker is written when the campaign ends or stops for a human, so a crontab @reboot resume does not restart it; SIGTERM
or Ctrl-C stops the running take (record_stop), restores the settings and leaves no DONE marker (a reboot resumes). It deletes
only the clip folders it made itself (own_clips.txt); other sessions' clips stay. Modes whose metered capacity x factor falls
below the 25 fps floor are metered only. Stages for --stages: m = capacity meter (90 s per mode and variant at
min(mode max, 1.25 x the storage cap); capacity = fps minus the buffer's slope, else from Core's stats line, with a second meter
take at 1.3 x the estimate when the first filled the buffer), s = split test (1 x 30 min against 3 x 10 min at 0.95 x capacity),
L = one 30-min take per mode at 0.9 x capacity, M = the MLV one-file control, k = frames_per_folder on/off (skipped when Core
lacks the knob), S = soak (the best clean 30-min fps twice).
  python3 -I longtakes.py --out ~/longtakes/ladder --stages msLMkS --modes 2kSDR12,2kHDR16 --budget-gb 3500 --fix-budget
  python3 -I longtakes.py --out ~/longtakes/smoke --stages m --meter-seconds 20 --no-gate --modes 2kSDR12   # smoke test
"""
import argparse, collections, csv, fcntl, glob, itertools, json, os, re, shutil, signal, socket, sqlite3, subprocess, sys, threading, time

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
SCREEN = {'s': 300}     # round 0: every config in the walk records this long (5 min); 10, 20 and 30 min only for the survivors
TIER_NAMES = {180: '3min', 300: '5min', 600: '10min', 900: '15min', 1200: '20min', 1800: '30min'}


def mode_size_mb(m):
    """DNG bytes per frame in MB: width x raw height x bits / 8 (16-bit Clear HDR raw frames carry 40 extra lines)."""
    key, w, h, bits, hdr = m
    raw_h = {2160: 2200, 1080: 1100}.get(h, h + 40) if bits == 16 else h
    return w * raw_h * bits / 8 / 1e6


def mode_possible(m):
    return mode_size_mb(m) * FPS_FLOOR <= DISK_MBPS * DISK_MARGIN


MODE_MAX = {}     # mode key -> the fps the mode itself allows, learned when its walk starts
# NVMe 4K campaign (plan nvme-campaign/plan.md, revision 2026-11-10; --stages N): set by campaign_main(). 'pre' and 'post' are
# hooks run_take() calls before record_start (void / WAITING checks) and after the take (stats, the merge, the clip ledger).
CAMPAIGN = {'on': False, 'pre': None, 'post': None}


def mode_top_fps(m):
    return MODE_MAX.get(m[0], mode_cap_fps(m))


def mode_cap_fps(m):
    """Highest fps the storage can carry at all for this mode."""
    return int(DISK_MBPS * DISK_MARGIN / mode_size_mb(m))


class Cfg:
    def __init__(self, mode, comp, log, tdn, lock, trim, web, split=None):
        self.mode = mode
        self.key, self.w, self.h, self.bits, self.hdr = mode
        self.comp, self.log, self.tdn, self.lock, self.trim, self.web = comp, log, tdn, lock, trim, web
        self.split = split      # frames_per_folder for the take (NVMe campaign R1: 5000 = split, 0 = flat); None = leave Core's

    @property
    def id(self):
        return '%s_%s_log%d_tdn%d_lock%d_trim%d_web%d%s' % (
            self.key, 'unc' if self.comp == 'none' else 'lossless', int(self.log), int(self.tdn),
            int(self.lock), int(self.trim), int(self.web), '' if self.split is None else '_fpf%d' % int(self.split))

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


def is_result(o):
    """An outcome that says something about the take itself (not a gate, watchdog, budget or setup stop): the resume skips
    only these."""
    o = o or ''
    return o.startswith(('pass', 'ab_')) or o in ('buffer_full', 'drop', 'fault', 'drive_full', 'recording_stopped_by_core')


def is_clean(o):
    """Ran its full length with no dropped frame (a take with stop_on_drop=False ends in ab_clean, not pass_*)."""
    o = o or ''
    return o.startswith('pass') or o == 'ab_clean'


def config_score(rows):
    """Rank a config's takes: a pass beats everything (higher fps first, then longer); otherwise the longest take."""
    rows = [r for r in rows if r['outcome'] not in ('exhausted', 'stopped_externally', 'skipped_unavailable', 'pruned')
            and not r.get('variant')]
    if not rows:
        return None
    passes = [r for r in rows if r['outcome'].startswith('pass')]
    if passes:
        b = max(passes, key=lambda r: (float(r['fps']), float(r['seconds'] or 0)))
        return (1, float(b['fps']), float(b['seconds'] or 0))
    return (0, 0.0, max(float(r['seconds'] or 0) for r in rows))


def factors_of(c):
    """The factors this config switches on, against the baseline (trim counts when it is OFF)."""
    f = set()
    if c.comp != 'none': f.add('comp')
    if c.log: f.add('log')
    if c.tdn: f.add('tdn')
    if c.lock: f.add('lock')
    if not c.trim: f.add('trim')
    if c.web: f.add('web')
    return f


# What can change the outcome, by what limits the mode (User, 2026-11-07: do not try things that cannot have an effect).
RELEVANT = {'storage': {'comp', 'log', 'trim'},          # fewer bytes, or drive stalls
            'capture': {'tdn', 'lock', 'web', 'log'}}    # camera / ISP / memory load


def limiter_of(rows, cap_fps):
    """What stopped a mode's baseline: {'storage'}, {'capture'}, both, or set() when it was clean at the highest fps."""
    rows = [r for r in rows if r['outcome'] not in ('exhausted', 'stopped_externally', 'skipped_unavailable', 'pruned')
            and not r.get('variant')]
    passes = [r for r in rows if r['outcome'].startswith('pass')]
    if passes and max(float(r['fps']) for r in passes) >= cap_fps:
        return set()
    fails = [r for r in rows if not r['outcome'].startswith('pass')]
    if passes:      # only the failure just above the clean fps says what limits it
        top = max(float(r['fps']) for r in passes)
        fails = [r for r in fails if float(r['fps']) > top] or fails
    lim = set()
    for r in fails:
        kinds = r.get('drop_kinds') or ''
        if r['outcome'] == 'buffer_full' or 'queue-full' in kinds or 'buffer_full' in kinds:
            lim.add('storage')
        if 'capture-gap' in kinds:
            lim.add('capture')
    return lim


def compare_scores(sc, base):
    """'better' / 'worse' / 'neutral' / None (no data) against the baseline's score (see config_score)."""
    if sc is None or base is None:
        return None
    if sc[0] != base[0]:
        return 'better' if sc[0] > base[0] else 'worse'
    if sc[0] == 1:                       # both passed: higher clean fps wins
        if sc[1] != base[1]:
            return 'better' if sc[1] > base[1] else 'worse'
        return 'neutral'
    a, b = max(sc[2], 0.1), max(base[2], 0.1)    # both failed: time to failure, 2x either way counts
    return 'better' if a >= 2 * b else ('worse' if a <= 0.5 * b else 'neutral')


def beneficial_factors(rows, mode_cfgs):
    """Single factors whose config beat the mode's baseline; combinations are only made from these."""
    base = config_score([r for r in rows if r['cfg_id'] == mode_cfgs[0].id])
    good = set()
    for c in mode_cfgs[1:]:
        fs = factors_of(c)
        if len(fs) == 1 and compare_scores(config_score([r for r in rows if r['cfg_id'] == c.id]), base) == 'better':
            good |= fs
    return good


def prune_reason(c, rows, mode_cfgs):
    """None if the config is worth testing, else why it cannot add information."""
    base_rows = [r for r in rows if r['cfg_id'] == mode_cfgs[0].id]
    lim = limiter_of(base_rows, mode_top_fps(c.mode))
    fs = factors_of(c)
    if not fs:
        return None
    if not base_rows:
        return None
    if not lim:
        return 'baseline already clean at the highest fps the storage allows: nothing to improve'
    rel = set().union(*[RELEVANT[l] for l in lim])
    if len(fs) == 1:
        if not fs <= rel:
            return 'cannot affect a %s limit (%s): %s' % ('/'.join(sorted(lim)), 'baseline stopped by', ','.join(sorted(fs)))
        return None
    good = beneficial_factors(rows, mode_cfgs)
    if not fs <= good:
        return 'combination skipped: %s did not help on its own' % ','.join(sorted(fs - good))
    return None


def bracket_search(f0, prior, attempt):
    """Highest fps that passes. f0 = first guess (the previous round's best). prior = [(fps, outcome)] already recorded for
    this config and round. attempt(f) -> True (pass) / False (fail) / None (stop the campaign). A failure costs a whole
    take, so: after a failure go down 3, 6, 12 ... fps until a take passes, then bisect between the highest pass (lo) and
    the lowest failure (hi). Returns (lo, hi); lo None = nothing passed down to FPS_FLOOR."""
    passes = [f for f, o in prior if o.startswith('pass')]
    lo = int(max(passes)) if passes else None
    fails = sorted(int(f) for f, o in prior if not o.startswith('pass') and (lo is None or f > lo))
    hi = fails[0] if fails else None
    step = 3
    f = int(f0) if hi is None else hi - step
    while lo is None:
        f = max(int(f), FPS_FLOOR)
        ok = attempt(f)
        if ok is None:
            return None, hi
        if ok:
            lo = f
        else:
            hi = f
            if f <= FPS_FLOOR:
                return None, hi
            step *= 2
            f = f - step
    while hi is not None and hi - lo > 1:
        mid = (lo + hi) // 2
        ok = attempt(mid)
        if ok is None:
            return lo, hi
        if ok: lo = mid
        else: hi = mid
    return lo, hi


def smart_next_fps(row, fps):
    """After a buffer_full failure: the frames the drive actually wrote per second during the take is
    fps x (enqueued - frames still queued at the stop) / enqueued (conservation: the rest of the frames were in the queue).
    Jump to about that fps (10 % headroom), never to less than FPS_FLOOR, never higher than fps - 1. None = no usable estimate."""
    try:
        st = json.loads(row.get('stats') or '{}')
        enq = int(st.get('enqueued', 0))
        peak = int(str(st.get('peak_queue', '0')).split('/')[0])
    except (ValueError, TypeError):
        return None
    t_rec = enq / float(fps)
    if enq < 60 or t_rec < 1.5 or peak <= 0:     # too short a take to say anything
        return None
    est = fps * max(enq - peak, 0) / enq
    nxt = int(est * (1.35 if t_rec < 4.0 else 1.15))     # the writers' start-up makes a short take's estimate low
    return max(FPS_FLOOR, min(int(fps) - 1, nxt)), est


def storage_frontier(rows, size_mb):
    """Lowest data rate (MB/s) at which an uncompressed, Log-off take of THIS frame size (+-3 %) already filled the RAM buffer;
    None if none did. Modes with other frame sizes are not comparable: the drive's limit is per file as well as per MB/s
    (2026-11-07: 2K frames filled the buffer at 118 MB/s, 4K frames at 220 MB/s)."""
    rates = []
    for r in rows:
        if r['outcome'] == 'buffer_full' and r.get('comp') == 'none' and r.get('log') in ('False', '0', False):
            for m in MODES:
                if m[0] == r.get('mode') and abs(mode_size_mb(m) - size_mb) <= 0.03 * size_mb:
                    rates.append(mode_size_mb(m) * float(r['fps']))
    return min(rates) if rates else None


SAMPLE_COLS = ('t_s', 'pi_c', 'nvme_c', 'cpu_pct', 'load1', 'mem_avail_mb', 'fill_pct', 'free_gb', 'throttled', 'dropped',
               'state', 'core_cpu_pct', 'core_top_thread', 'buffer_used', 'buffer_capacity', 'dev_w_ios', 'dev_w_sectors',
               'dev_w_ticks', 'dev_inflight', 'dirty_kb', 'writeback_kb', 'trim_running', 'trim_last_unix', 't_unix',
               'clients', 'merge_pending', 'ui_fds', 'ui_dmabuf', 'arec_fds', 'core_fds', 'cma_free_kb', 'audio_ready',
               'uiconf_rec', 'uiconf_dev', 'uiconf_mtime')
UI_SAMPLE_COLS = ('ui_fds', 'ui_dmabuf', 'arec_fds', 'core_fds', 'cma_free_kb', 'audio_ready', 'uiconf_rec', 'uiconf_dev', 'uiconf_mtime')
DEV = {'disk': ''}      # the recording drive's whole-disk name (sda, nvme0n1) for /sys/block/<disk>/stat; set in main()
LAST_END = {'t': None}  # wall time the previous take ended (idle gap, trim-since-last-take)

# ---- unattended operation (2026-11-08, storage-slowdown plan section 4.6): a gate that waits for a quiet Pi before every
# take, a watchdog that stops the campaign on hardware trouble, a write budget, a lock file other sessions can see.
GATE = {'on': True, 'timeout_s': 6 * 3600, 'poll_s': 120}
BUDGET = {'gb': 0.0, 'used': 0.0}        # --budget-gb: the campaign stops before a take that would exceed it
HALT = {'why': ''}                        # set by the watchdog; the take() wrapper stops the campaign
RUN_DIR = '/run/apertar-media' if os.path.isdir('/run/apertar-media') else '/tmp'
LOCK = RUN_DIR + '/longtakes.lock'
HWCONF = '/home/pi/apertar-hardware.conf'
# Kernel lines that end the campaign. Boot-time lines never reach the watchdog (its first window starts when the runner
# starts), so "AER enabled", "Shutdown timeout set" and the USB resets of enumeration do not count; USB and SCSI lines count
# only for the recording disk itself (hardware_ok builds those patterns from /sys/block/<disk>).
KERNEL_BAD = re.compile(r'(nvme nvme\d+: (I/O \d+ (QID \d+ )?timeout|controller is down|resetting controller|Device not ready|'
                        r'disabling|Removing after probe failure)|AER: (Corrected|Uncorrected|Multiple|Fatal|Non-Fatal|device recovery)|'
                        r'exFAT-fs.*(error|read-only|corrupt|invalid)|I/O error|critical (medium|target) error|under-?voltage)', re.I)
WATCH = {'since': None}
STOP = {'sig': ''}          # set by SIGTERM / SIGINT: the running take is stopped, the settings restored, no DONE marker written
OWN = {'clips': set()}      # clip folders this run made (<out>/own_clips.txt): the only ones clear_media() ever deletes
NOTES = []                  # one-time messages from quiet_reasons(), logged by wait_for_quiet()
SAID = {}                   # keys of messages already logged once
WAKE = {'sent': None}


def ps_cmds():
    r = subprocess.run(['ps', '-eo', 'pid=,cmd='], capture_output=True, text=True)
    return [l.strip() for l in r.stdout.splitlines() if l.strip()]


def foreign_locks():
    """Lock files of other campaign sessions under /run/apertar-media (ours excluded; a dead owner's lock is ignored)."""
    out = []
    for f in glob.glob(RUN_DIR + '/*.lock'):
        if os.path.abspath(f) == os.path.abspath(LOCK):
            continue
        try:
            text = open(f).read()
            m = re.search(r'pid=(\d+)', text)
            if not m:                                   # not a campaign lock (the convention: pid=... what=...)
                continue
            if not os.path.exists('/proc/%s' % m.group(1)):
                continue                                # its owner is gone
            out.append('%s: %s' % (os.path.basename(f), text.strip()[:80]))
        except OSError:
            pass
    return out


def probe_running(cmds, me):
    """A python process running one of the storage probes (not an editor or a grep that merely names the script)."""
    pat = re.compile(r'python[0-9.]*(\s+-\S+)*\s+\S*exfat_(dir|write|merge)_probe\.py')
    return any(pat.search(l) and not l.startswith(me + ' ') for l in cmds)


BUILD_TOOLS = re.compile(r'(^|/)(cc1plus|cc1|g\+\+(-\d+)?|gcc(-\d+)?|c\+\+|clang(\+\+)?(-\d+)?|ld|ld\.gold|ld\.lld|collect2|'
                         r'make|gmake|cmake|ninja|cargo|rustc)( |$)')


def quiet_reasons(need_free_gib=20.0):
    """Why the Pi is not ready for a take right now; [] when it is. Each reason names what to wait for. need_free_gib 0 = do
    not check the free space (before the runner has cleared its own leftover clips)."""
    why = []
    cmds = ps_cmds()
    me = str(os.getpid())
    if probe_running(cmds, me):
        why.append('another storage probe is running')
    if any(BUILD_TOOLS.search(l.split(' ', 1)[1] if ' ' in l else l) for l in cmds):
        why.append('a build is running')
    fl = foreign_locks()
    if fl:
        why.append('another session holds a lock (%s)' % '; '.join(fl))
    st = state()
    if not st:
        why.append('Core is not answering')
    else:
        if st.get('standby'):
            # Core went to standby while idle (its sleep mode): wake it and wait; a wake that does not take needs a human.
            if WAKE['sent'] is None:
                core('wake')
                WAKE['sent'] = time.time()
                why.append('Core was in standby: wake sent')
            elif time.time() - WAKE['sent'] > 180:
                why.append('NEEDS A HUMAN: Core stays in standby after a wake command')
            else:
                why.append('Core is waking from standby')
        else:
            WAKE['sent'] = None
            if st.get('recording') or st.get('state') != 'ready':
                why.append('Core is %s' % ('recording' if st.get('recording') else st.get('state')))
        if st.get('storage_preroll_active'):
            why.append('a storage pre-roll is running')
        if st.get('media_state') != 'mounted' or st.get('media_alive') is False:
            why.append('medium not mounted or not alive (%s)' % st.get('media_state'))
        if st.get('ladder_enabled'):
            why.append('NEEDS A HUMAN: the Mode Ladder is on and the campaign cannot switch modes; turn it off (WebUI, Camera > Mode Ladder)')
        if web_state().get('media_trim_running'):
            why.append('a trim is running')
    try:
        thr = subprocess.run(['vcgencmd', 'get_throttled'], capture_output=True, text=True).stdout.strip().split('=')[-1]
        if int(thr, 16) & 0xF:
            why.append('throttled or under-voltage now (%s)' % thr)
    except (ValueError, OSError):
        pass
    try:
        sv = os.statvfs(MEDIA)
        free = sv.f_bavail * sv.f_frsize / 2**30
        if need_free_gib and free < need_free_gib:
            why.append('only %.0f GiB free, the take needs %.0f' % (free, need_free_gib))
        stale = []
        for d in os.listdir(MEDIA):
            if d.startswith('probe_exfat_'):
                age = time.time() - os.path.getmtime(os.path.join(MEDIA, d))
                if 'another storage probe is running' in why or age < 600:
                    why.append('a probe_exfat_* folder is on the medium (another probe mid-run)')
                    break
                stale.append(d)
        if stale and SAID.get('stale') != set(stale):
            SAID['stale'] = set(stale)
            NOTES.append('ignoring %d stale probe folder(s) on %s (no probe runs, older than 10 min; left by a crashed probe, not '
                         'deleted: not ours): %s' % (len(stale), MEDIA, ', '.join(sorted(stale))[:200]))
    except OSError:
        why.append('%s not readable' % MEDIA)
    return why


def wait_for_quiet(out, need_free_gib=20.0):
    """Wait until quiet_reasons() is empty (polling), up to GATE['timeout_s']. Returns '' when quiet, else why it gave up:
    'needs_human' (a condition nobody but a human can clear), 'gate_timeout', 'signal' (SIGTERM / Ctrl-C arrived)."""
    if not GATE['on']:
        return ''
    t0 = time.monotonic()
    last = None
    while True:
        why = quiet_reasons(need_free_gib)
        while NOTES:
            log(out, 'gate: ' + NOTES.pop(0))
        if not why:
            if last is not None:
                log(out, 'gate: quiet again after %.0f min' % ((time.monotonic() - t0) / 60))
            return ''
        if any(w.startswith('NEEDS A HUMAN') for w in why):
            log(out, 'gate: ' + '; '.join(why))
            return 'needs_human'
        if why != last:
            log(out, 'gate: waiting (%s)' % '; '.join(why))
            last = why
        if time.monotonic() - t0 > GATE['timeout_s']:
            log(out, 'gate: still not quiet after %.1f h, giving up: %s' % (GATE['timeout_s'] / 3600, '; '.join(why)))
            return 'gate_timeout'
        slept = 0
        while slept < GATE['poll_s']:
            if STOP['sig']:
                return 'signal'
            time.sleep(5)
            slept += 5


def hold_lock(what, seconds):
    try:
        with open(LOCK, 'w') as f:
            f.write('pid=%d what=%s started=%s planned_end=%s\n' % (
                os.getpid(), what, time.strftime('%F %T'), time.strftime('%F %T', time.localtime(time.time() + seconds))))
    except OSError:
        pass


def release_lock():
    try:
        os.unlink(LOCK)
    except OSError:
        pass


def usb_dev_of(disk):
    """The USB device (e.g. 1-1) behind a sdX disk, from its sysfs path; None for NVMe or unknown."""
    try:
        p = os.path.realpath('/sys/block/%s/device' % disk)
    except OSError:
        return None
    m = re.search(r'/usb\d+/(\d+-[\d.]+)/', p)
    return m.group(1) if m else None


def hardware_ok(out):
    """Kernel log since the last check (needs the systemd-journal group; else dmesg) and Core's media_alive. (ok, why).
    The first window starts when the runner started (WATCH['since'] is set in main), never in the boot messages."""
    since = WATCH['since'] or time.time()
    WATCH['since'] = time.time()
    lines = []
    r = subprocess.run(['journalctl', '-k', '--since', '@%d' % int(since), '-o', 'short-unix', '--no-pager', '-q'],
                       capture_output=True, text=True)
    if r.returncode == 0:
        lines = r.stdout.splitlines()
    else:
        r = subprocess.run(['dmesg', '--since', '-%dmin' % max(1, int((time.time() - since) / 60) + 1)], capture_output=True, text=True)
        if r.returncode == 0:
            lines = r.stdout.splitlines()
        elif not WATCH.get('warned'):
            WATCH['warned'] = True
            log(out, 'watchdog: the kernel log is not readable from this account; watching media_alive only')
    pats = [KERNEL_BAD]
    disk = DEV['disk']
    if disk:
        pats.append(re.compile(r'\[%s\].*(error|uas_eh|abort|reset|offline|timed? ?out)' % re.escape(disk), re.I))
        ud = usb_dev_of(disk)
        if ud:
            pats.append(re.compile(r'usb %s(\.\d+)*: (USB disconnect|reset |device descriptor|device not accepting|cannot)' % re.escape(ud), re.I))
    bad = [l for l in lines if any(p.search(l) for p in pats)]
    if bad:
        return False, 'kernel log: ' + ' | '.join(b[-160:] for b in bad[:3])
    st = state()
    if st and st.get('media_alive') is False:
        return False, 'Core reports media_alive=false (media_state=%s)' % st.get('media_state')
    return True, ''


def projected_gb(c, fps, seconds):
    """Upper bound of a take's writes (uncompressed size; lossless and Log write less)."""
    return mode_size_mb(c.mode) * fps * max(seconds or 1800, 1) / 1000.0


def capacity_from_samples(rows, fps, frame_bytes, unit):
    """The writers' capacity in fps from the buffer level: fps minus the slope of the buffer (frames per second) once it
    holds more than two frames. (capacity_fps, how); how = 'fit', 'at least' (the buffer never filled), or '' (no data)."""
    pts = []
    for x in rows:
        if x.get('state') != 'rec' or x.get('buffer_used') in (None, '') or (x.get('t_s') or 0) < 3:
            continue
        try:
            used = float(x['buffer_used'])
        except (TypeError, ValueError):
            continue
        if unit == 'bytes':
            if not frame_bytes:
                return None, ''
            used /= frame_bytes
        pts.append((float(x['t_s']), used))
    if len(pts) < 10:
        return None, ''
    start = next((i for i, p in enumerate(pts) if p[1] > 2), None)
    if start is None or len(pts) - start < 8:
        return float(fps), 'at least'
    pts = pts[start:]
    mx = sum(p[0] for p in pts) / len(pts); my = sum(p[1] for p in pts) / len(pts)
    sxx = sum((p[0] - mx) ** 2 for p in pts)
    if not sxx:
        return None, ''
    slope = sum((p[0] - mx) * (p[1] - my) for p in pts) / sxx
    return round(max(0.0, fps - slope), 2), 'fit'


def edit_storage_keys(path, keys):
    """Set (value) or remove (None) keys under [storage] in apertar-hardware.conf. A commented copy of a key is replaced by
    the live key. Returns {key: original line or None} for every key touched (None = the key was absent)."""
    text = open(path).read()
    lines = text.split('\n')
    before = {}
    i = next((i for i, l in enumerate(lines) if l.strip().lower() == '[storage]'), None)
    if i is None:
        before.update({k: None for k in keys})
        add = ['%s=%s' % (k, v) for k, v in keys.items() if v is not None]
        if add:
            while lines and not lines[-1].strip():
                lines.pop()
            lines += ['', '[storage]'] + add + ['']
    else:
        j = i + 1
        while j < len(lines) and not lines[j].strip().startswith('['):
            j += 1
        section = lines[i + 1:j]
        for k, v in keys.items():
            for n, l in enumerate(section):
                if re.match(r'^[#;]?\s*%s\s*=' % re.escape(k), l.strip()):
                    before[k] = l
                    if v is None:
                        del section[n]
                    else:
                        section[n] = '%s=%s' % (k, v)
                    break
            else:
                before[k] = None
                if v is not None:
                    last = max((n for n, l in enumerate(section) if l.strip()), default=-1)   # after the last non-blank line
                    section.insert(last + 1, '%s=%s' % (k, v))
        lines[i + 1:j] = section
    tmp = path + '.longtakes-tmp'
    with open(tmp, 'w') as f:
        f.write('\n'.join(lines))
    os.replace(tmp, path)
    return before


def set_storage_keys(path, keys, out):
    """Set keys under [storage] for the run (Core reads [storage] at each take and writes its own keys there through its
    store, so only our keys are touched, never the whole file). The original lines are kept in <out>/storage_keys_orig.json
    on the first call; restore_storage_keys() puts them back and removes the file."""
    rec = out + '/storage_keys_orig.json'
    before = edit_storage_keys(path, keys)
    if not os.path.exists(rec):
        json.dump(before, open(rec, 'w'))
    return rec


def restore_storage_keys(path, out):
    """Put the keys set_storage_keys() changed back as they were: the original line (live or commented), or removed."""
    rec = out + '/storage_keys_orig.json'
    if not os.path.exists(rec):
        return False
    before = json.load(open(rec))
    edit_storage_keys(path, {k: None for k in before})           # drop our live lines
    text = open(path).read()
    lines = text.split('\n')
    i = next((i for i, l in enumerate(lines) if l.strip().lower() == '[storage]'), None)
    keep = [l for l in before.values() if l is not None]
    if keep:
        if i is None:
            while lines and not lines[-1].strip():
                lines.pop()
            lines += ['', '[storage]'] + keep + ['']
        else:
            j = i + 1
            while j < len(lines) and not lines[j].strip().startswith('['):
                j += 1
            last = max((n for n in range(i + 1, j) if lines[n].strip()), default=i)
            lines[last + 1:last + 1] = keep
        tmp = path + '.longtakes-tmp'
        with open(tmp, 'w') as f:
            f.write('\n'.join(lines))
        os.replace(tmp, path)
    os.unlink(rec)
    return True


def dev_stat(disk):
    """/sys/block/<disk>/stat: writes completed, sectors written, write ticks (ms), in flight. Cumulative; differentiate later."""
    try:
        f = open('/sys/block/%s/stat' % disk).read().split()
        return int(f[4]), int(f[6]), int(f[7]), int(f[8])
    except (OSError, IndexError, ValueError):
        return None, None, None, None


def resolve_disk():
    """The whole-disk name (sda, nvme0n1) behind the mount, for /sys/block/<disk>/stat and the watchdog; '' if not mounted."""
    src_ = subprocess.run(['findmnt', '-no', 'SOURCE', MEDIA], capture_output=True, text=True).stdout.strip()
    if not src_:
        return ''
    KT['dev'] = src_
    parent = subprocess.run(['lsblk', '-no', 'pkname', src_], capture_output=True, text=True).stdout.strip().splitlines()
    DEV['disk'] = os.path.basename('/dev/' + parent[0] if parent else src_)
    DEV['parent'] = '/dev/' + parent[0] if parent else src_
    return DEV['disk']


def buffer_level():
    """Core's write-buffer level from the lock-free GET /api/buffer (get_state does not carry it): (used, capacity, unit);
    unit is 'bytes' for the RAM buffer and 'frames' for the frame queue."""
    import urllib.request
    try:
        b = json.load(urllib.request.urlopen('http://127.0.0.1:8000/api/buffer', timeout=0.5))
        return b.get('buffer_used'), b.get('buffer_capacity'), b.get('buffer_unit')
    except Exception:
        return None, None, None


def web_state(timeout=1.0):
    """Core's web state (GET /api/state): the trim fields (media_trim_*), the clip-merge state and the buffer level live here,
    not in get_state. {} when the WebUI port does not answer."""
    import urllib.request
    try:
        return json.load(urllib.request.urlopen('http://127.0.0.1:8000/api/state', timeout=timeout))
    except Exception:
        return {}


UI_CG = '/sys/fs/cgroup/system.slice/apertar-ui-direct.service/cgroup.procs'


def ui_health():
    """The touch UI's resources (night 1, 2026-11-10: the UI began failing dmabuf exports at 03:56 and the next takes had no
    audio): open fds and dmabuf fds of the Qt UI and of its meter arecord, Core's fds, and the kernel's free CMA."""
    h = {'ui_fds': None, 'ui_dmabuf': None, 'arec_fds': None, 'core_fds': None, 'cma_free_kb': None}
    h.update(uiconf_audio())

    def fds(pid):
        n = d = 0
        try:
            for f in os.listdir('/proc/%d/fd' % pid):
                n += 1
                try:
                    if 'dmabuf' in os.readlink('/proc/%d/fd/%s' % (pid, f)):
                        d += 1
                except OSError:
                    pass
        except OSError:
            return None, None
        return n, d
    try:
        for x in open(UI_CG).read().split():
            comm = rd('/proc/%s/comm' % x, '')
            if comm == 'Apertar-UI':
                h['ui_fds'], h['ui_dmabuf'] = fds(int(x))
            elif comm == 'arecord':
                h['arec_fds'] = fds(int(x))[0]
    except (OSError, ValueError):
        pass
    try:     # Core's process by name in its cgroup (no systemctl subprocess every 5 s; the MainPID is the start script)
        for x in open('/sys/fs/cgroup/system.slice/apertar-core.service/cgroup.procs').read().split():
            if rd('/proc/%s/comm' % x, '') == 'apertar-core':
                h['core_fds'] = fds(int(x))[0]
    except (OSError, ValueError):
        pass
    try:
        for l in open('/proc/meminfo'):
            if l.startswith('CmaFree'):
                h['cma_free_kb'] = int(l.split()[1])
    except (OSError, ValueError):
        pass
    return h


UICONF = os.path.expanduser('~/.config/CinePi/UI.conf')


def uiconf_audio():
    """The two keys Core's record_start reads from the touch UI's settings file (readSharedUiSettings, recordAudioEnabled
    defaults to false when the file or key is missing), read straight from the file, not through Core."""
    h = {'uiconf_rec': None, 'uiconf_dev': None, 'uiconf_mtime': None}
    try:
        h['uiconf_mtime'] = round(os.stat(UICONF).st_mtime, 2)
        for l in open(UICONF):
            k, _, v = l.strip().partition('=')
            if k == 'recordAudioEnabled':
                h['uiconf_rec'] = 1 if v.strip() in ('true', '1') else 0
            elif k == 'audioInputDevice':
                h['uiconf_dev'] = v.strip()
    except OSError:
        pass
    return h


def audio_forensics(out, tag, ui_since=None):
    """Never raises: a failing snapshot is noted in audio-events.log and the take's bookkeeping goes on."""
    try:
        return _audio_forensics(out, tag, ui_since)
    except Exception as e:
        try:
            with open(os.path.join(out, 'audio-events.log'), 'a') as f:
                f.write(time.strftime('%F %T ') + 'snapshot %s failed: %r\n' % (tag, e))
        except OSError:
            pass
        return 'snapshot-failed'


def _audio_forensics(out, tag, ui_since=None):
    """Everything about the audio path at one moment, into <run>/audio-forensics/<time>-<tag>/ (User 2026-11-10: "log
    carefully the loss of sound so we can debug it later"). Read-only, no sudo; called between takes only: at the night start
    (baseline), when the pre-check finds Core without the mic, and after a take with no audio."""
    d = os.path.join(out, 'audio-forensics', time.strftime('%Y%m%d-%H%M%S-') + re.sub(r'[^A-Za-z0-9_.-]', '_', tag)[:80])
    os.makedirs(d, exist_ok=True)

    def put(name, text):
        with open(os.path.join(d, name), 'w') as f:
            f.write(text if text.endswith('\n') else text + '\n')

    def run(cmd, timeout=20):
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            return 'rc=%d\n%s%s' % (r.returncode, r.stdout, r.stderr)
        except (OSError, subprocess.SubprocessError) as e:
            return 'failed: %r' % e
    try:
        shutil.copy2(UICONF, os.path.join(d, 'UI.conf'))
    except OSError as e:
        put('UI.conf.error', repr(e))
    put('uiconf_audio.json', json.dumps(dict(uiconf_audio(), mtime_local=time.strftime('%F %T', time.localtime(os.stat(UICONF).st_mtime)) if os.path.exists(UICONF) else None), indent=1))
    asound = []
    for f in ['/proc/asound/cards', '/proc/asound/pcm', '/proc/asound/devices'] + sorted(
            glob.glob('/proc/asound/card*/pcm*c/sub*/status') + glob.glob('/proc/asound/card*/pcm*c/sub*/hw_params')):
        asound.append('== %s\n%s' % (f, rd(f, '(unreadable)')))
    asound.append('== arecord -l (what Core runs at record_start)\n' + run(['arecord', '-l']))
    asound.append('== aplay -l\n' + run(['aplay', '-l']))
    asound.append('== lsusb -t\n' + run(['lsusb', '-t']))
    put('asound.txt', '\n'.join(asound))
    procs = []
    for unit in ('apertar-ui-direct', 'apertar-core'):
        try:
            pids = open('/sys/fs/cgroup/system.slice/%s.service/cgroup.procs' % unit).read().split()
        except OSError:
            pids = []
        for x in pids:
            comm = rd('/proc/%s/comm' % x, '?')
            kinds = collections.Counter()
            try:
                for f in os.listdir('/proc/%s/fd' % x):
                    try:
                        t = os.readlink('/proc/%s/fd/%s' % (x, f))
                    except OSError:
                        continue
                    kinds['dmabuf' if 'dmabuf' in t else re.sub(r'[:\[].*', '', t) if not t.startswith('/') else ('/dev/snd' if t.startswith('/dev/snd') else
                          '/dev/dri' if t.startswith('/dev/dri') else '/dev/dma_heap' if t.startswith('/dev/dma_heap') else
                          '/dev/video' if t.startswith('/dev/video') else '/dev/media' if t.startswith('/dev/media') else 'file')] += 1
            except OSError:
                pass
            st_ = ''.join(l for l in (rd('/proc/%s/status' % x, '') or '').splitlines(True)
                          if l.split(':')[0] in ('State', 'VmRSS', 'VmSize', 'Threads', 'FDSize'))
            lim = ''.join(l for l in (rd('/proc/%s/limits' % x, '') or '').splitlines(True) if 'open files' in l)
            procs.append('== %s pid %s %s (%s)\nfds by kind: %s\n%s%s' % (unit, x, comm, (rd('/proc/%s/cmdline' % x, '') or '').replace('\0', ' ')[:200],
                         dict(kinds), st_, lim))
    put('processes.txt', '\n'.join(procs))
    mem = ''.join(l for l in open('/proc/meminfo') if l.split(':')[0] in ('MemAvailable', 'MemFree', 'CmaTotal', 'CmaFree'))
    try:
        bufs = os.listdir('/sys/kernel/dmabuf/buffers')
        size = sum(int(rd('/sys/kernel/dmabuf/buffers/%s/size' % b, '0') or 0) for b in bufs)
        exp = collections.Counter(rd('/sys/kernel/dmabuf/buffers/%s/exporter_name' % b, '?') for b in bufs)
        mem += 'dmabuf buffers: %d, %.1f MiB, by exporter %s\n' % (len(bufs), size / 2**20, dict(exp))
    except OSError as e:
        mem += 'dmabuf sysfs: %r\n' % e
    put('memory.txt', mem)
    put('api_state.json', json.dumps(web_state(3.0), indent=1))
    since = ui_since or time.time() - 600
    try:
        ul = subprocess.run(['journalctl', '-u', 'apertar-ui-direct', '-u', 'apertar-core', '--since', '@%d' % int(since),
                             '-o', 'short-precise', '--no-pager'], capture_output=True, text=True, timeout=120).stdout.splitlines()
    except (OSError, subprocess.SubprocessError):
        ul = []
    keep = ul if len(ul) <= 20000 else ul[:10000] + ['... %d lines left out ...' % (len(ul) - 20000)] + ul[-10000:]
    put('journal-ui-core.log', '\n'.join(keep))
    mesa = [l for l in ul if 'MESA' in l]
    summary = 'tag %s at %s; journal since %s: %d lines, %d MESA, first MESA: %s' % (
        tag, time.strftime('%F %T'), time.strftime('%T', time.localtime(since)), len(ul), len(mesa), mesa[0][:160] if mesa else '-')
    put('summary.txt', summary)
    with open(os.path.join(out, 'audio-events.log'), 'a') as f:
        f.write(time.strftime('%F %T ') + summary + ' -> ' + os.path.basename(d) + '\n')
    return d


def audio_ready(ws):
    """(ready, why) from /api/state: Core will record audio when ui.record_audio_enabled is on and ui.audio_input_device is one
    of audio.input_devices (Core's own arecord -l, the list record_start resolves against; ApertarCoreApp.cpp:3157 e298d4a)."""
    if not ws:
        return None, 'no /api/state'
    ui, au = ws.get('ui') or {}, ws.get('audio') or {}
    ids = [d.get('id') for d in au.get('input_devices') or []]
    dev = ui.get('audio_input_device') or ''
    ok = bool(ui.get('record_audio_enabled')) and (dev in ids or (not dev and bool(ids)))
    return ok, 'record_audio_enabled=%s audio_input_device=%r input_devices=%s' % (ui.get('record_audio_enabled'), dev, ids)


class Sampler(threading.Thread):
    """1 Hz: temps, cpu, ram, drive fill, throttle flags, Core drop counter, Core's buffer level, the disk's own counters,
    dirty pages and the trim state. Keeps every sample for the take."""
    def __init__(self, t0, csv_path):
        super().__init__(daemon=True)
        self.t0, self.stop_ev, self.rows = t0, threading.Event(), []
        self.f = open(csv_path, 'w', newline='')
        self.w = csv.writer(self.f)
        self.w.writerow(list(SAMPLE_COLS))
        self.prev = self.cpu_times()
        self.core_pid = self.find_core()
        self.prev_core = None
        self.n = 0
        self.trim = (None, None)     # (media_trim_running, media_trim_last_unix) from /api/state, refreshed every 5th sample
        self.uih = {}                # ui_health() + audio_ready, refreshed every 5th sample (campaign)

    @staticmethod
    def find_core():
        for d in os.listdir('/proc'):
            if d.isdigit():
                try:
                    if b'apertar-core' in open('/proc/%s/cmdline' % d, 'rb').read() and b'--socket' in open('/proc/%s/cmdline' % d, 'rb').read():
                        return int(d)
                except OSError:
                    pass
        return None

    def core_cpu(self):
        """Core's CPU use, in % of one core, summed over its threads, and the busiest thread (name:%). None if unreadable."""
        if not self.core_pid:
            return None, ''
        now = time.monotonic()
        cur = {}
        try:
            for t in os.listdir('/proc/%d/task' % self.core_pid):
                try:
                    st = open('/proc/%d/task/%s/stat' % (self.core_pid, t)).read()
                    comm = st[st.index('(') + 1:st.rindex(')')]
                    f = st[st.rindex(')') + 2:].split()
                    cur[t] = (comm, int(f[11]) + int(f[12]))
                except (OSError, ValueError, IndexError):
                    pass
        except OSError:
            return None, ''
        prev, self.prev_core = self.prev_core, (now, cur)
        if not prev:
            return None, ''
        dt = max(now - prev[0], 0.05) * os.sysconf('SC_CLK_TCK')
        tot, top = 0.0, ('', 0.0)
        for t, (comm, ticks) in cur.items():
            d = (ticks - prev[1].get(t, (comm, ticks))[1]) / dt * 100
            tot += d
            if d > top[1]:
                top = (comm, d)
        return round(tot, 1), '%s:%.0f' % (top[0], top[1])

    @staticmethod
    def cpu_times():
        v = [int(x) for x in open('/proc/stat').readline().split()[1:]]
        return sum(v), v[3] + v[4]

    def sample(self):
        tot, idle = self.cpu_times()
        pt, pi_ = self.prev
        cpu = 100.0 * (1 - (idle - pi_) / max(1, tot - pt))
        self.prev = (tot, idle)
        mem, dirty, wb = 0, None, None
        for l in open('/proc/meminfo'):
            if l.startswith('MemAvailable'):
                mem = int(l.split()[1]) // 1024
            elif l.startswith('Dirty:'):
                dirty = int(l.split()[1])
            elif l.startswith('Writeback:'):
                wb = int(l.split()[1])
        try:
            sv = os.statvfs(MEDIA)
            total, free = sv.f_blocks * sv.f_frsize, sv.f_bavail * sv.f_frsize
        except OSError:
            total, free = 1, 0       # a dead medium: the take loop sees free 0 and the state, never a crashed sampler
            self.statvfs_error = True
        if self.n % 10 == 0 or not hasattr(self, 'thr'):    # H8: no vcgencmd subprocess every second
            try:
                self.thr = subprocess.run(['vcgencmd', 'get_throttled'], capture_output=True, text=True,
                                          timeout=5).stdout.strip().split('=')[-1]
            except (OSError, subprocess.SubprocessError):
                self.thr = '?'
        thr = self.thr
        st = state()
        ccpu, ctop = self.core_cpu()
        pi = int(rd(PI_TEMP, '0')) / 1000
        nv = int(rd(NVME_TEMP, '0')) / 1000 if NVME_TEMP else None
        used, cap, _unit = buffer_level()
        if self.n % 5 == 0:
            ws = web_state(0.5)
            if ws:
                self.trim = (ws.get('media_trim_running'), ws.get('media_trim_last_unix'))
            if CAMPAIGN['on']:
                self.uih = ui_health()
                ar = audio_ready(ws)[0]
                self.uih['audio_ready'] = None if ar is None else int(ar)
        self.n += 1
        w_ios, w_sect, w_ticks, inflight = dev_stat(DEV['disk'] or resolve_disk()) if (DEV['disk'] or os.path.ismount(MEDIA)) else (None, None, None, None)
        return {'t_s': round(time.monotonic() - self.t0, 1), 'pi_c': pi, 'nvme_c': nv, 'cpu_pct': round(cpu, 1),
                'load1': os.getloadavg()[0], 'mem_avail_mb': mem, 'fill_pct': round(100 * (1 - free / total), 1),
                'free_gb': round(free / 2**30, 1), 'throttled': thr, 'dropped': st.get('recording_dropped_frames', -1),
                'state': 'rec' if st.get('recording') else str(st.get('state')), '_st': st,
                'core_cpu_pct': ccpu, 'core_top_thread': ctop,
                'buffer_used': used, 'buffer_capacity': cap, 'dev_w_ios': w_ios, 'dev_w_sectors': w_sect,
                'dev_w_ticks': w_ticks, 'dev_inflight': inflight, 'dirty_kb': dirty, 'writeback_kb': wb,
                'trim_running': self.trim[0], 'trim_last_unix': self.trim[1], 't_unix': round(time.time(), 2),
                'clients': web_peers(loopback=True) if CAMPAIGN['on'] else None, 'merge_pending': st.get('clip_merge_pending'),
                **{k: self.uih.get(k) for k in UI_SAMPLE_COLS}}

    def run(self):
        # 1 Hz (H8). A failing sample is logged as an error row, never ends the thread (C2 F9): the take loop's stale-sample
        # guard (CAMPAIGN) stops a take whose samples stop arriving.
        while not self.stop_ev.is_set():
            t = time.monotonic()
            try:
                r = self.sample()
                self.rows.append(r)
                self.w.writerow([r.get(k) for k in SAMPLE_COLS])
                self.f.flush()
            except Exception as e:      # noqa: BLE001 - the sampler must survive anything
                self.errors = getattr(self, 'errors', 0) + 1
                self.last_error = repr(e)[:200]
            self.stop_ev.wait(max(0.05, (1.0 if CAMPAIGN['on'] else 0.5) - (time.monotonic() - t)))

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


def apply_cfg(c, fps, fmt='cdng'):
    # Clear HDR and the resolution first, then a bit-depth round trip so every take starts from a fresh camera config.
    # (set_clear_hdr takes `enabled`; set_resolution takes width and height.) fmt: 'cdng' (default) or 'mlv' (the one-file
    # control take of the storage-slowdown plan); the compression and Log commands are cDNG's.
    st = state()
    if st.get('recording_format') not in (None, fmt):
        core('set_record_format', value=fmt); time.sleep(3)
        # Core keeps settings per format (profile.<format>.*): the switch loads that profile's resolution and Clear HDR,
        # so the checks below need the state after it (smoke 2026-11-09: MLV came up 3840x2160, setup_mismatch).
        st = state()
    if bool(st.get('clear_hdr')) != c.hdr:
        core('set_clear_hdr', enabled=c.hdr); time.sleep(4)
    if st.get('resolution') != '%dx%d' % (c.w, c.h):
        core('set_resolution', width=c.w, height=c.h); time.sleep(4)
    other = {16: 12, 12: (16 if c.hdr else 10), 10: 12}[c.bits]
    core('set_raw_bit_depth', value=other); time.sleep(5)
    core('set_raw_bit_depth', value=c.bits); time.sleep(6)
    settle()
    if fmt == 'cdng':
        core('set_cdng_compression', value=c.comp)
        core('set_cdng_log', value='on' if c.log else 'off')
    core('set_preview_tdn', enabled=c.tdn)
    core('set_fps_phase_lock', enabled=c.lock)
    core('set_media_trim', enabled=c.trim)
    if getattr(c, 'split', None) is not None:
        core('set_frames_per_folder', value=int(c.split))
    core('set_fps', value=float(fps))
    time.sleep(4)
    return settle()


def verify(c, fps, st, fmt='cdng', expect=None):
    """Return '' if Core reports what we asked for, else the mismatch. expect = {state key: value} a stage demands besides."""
    bad = []
    for k, v in (expect or {}).items():
        if str(st.get(k)) != str(v): bad.append('%s=%s' % (k, st.get(k)))
    if st.get('raw_bit_depth') != c.bits: bad.append('bits=%s' % st.get('raw_bit_depth'))
    if 'recording_format' in st and st.get('recording_format') != fmt: bad.append('format=%s' % st.get('recording_format'))
    if fmt == 'cdng' and st.get('cdng_compression') != c.comp: bad.append('comp=%s' % st.get('cdng_compression'))
    if fmt == 'cdng' and bool(st.get('cdng_log_applied')) != c.log: bad.append('log_applied=%s' % st.get('cdng_log_applied'))
    if bool(st.get('preview_tdn')) != c.tdn: bad.append('tdn=%s' % st.get('preview_tdn'))
    if bool(st.get('fps_phase_lock')) != c.lock: bad.append('lock=%s' % st.get('fps_phase_lock'))
    if abs(float(st.get('fps', 0)) - fps) > 0.01: bad.append('fps=%s' % st.get('fps'))
    if st.get('resolution') != '%dx%d' % (c.w, c.h): bad.append('res=%s' % st.get('resolution'))
    if bool(st.get('clear_hdr')) != c.hdr: bad.append('clear_hdr=%s' % st.get('clear_hdr'))
    if getattr(c, 'split', None) is not None and str(st.get('frames_per_folder')) != str(int(c.split)):
        bad.append('frames_per_folder=%s' % st.get('frames_per_folder'))
    return ' '.join(bad)


def clip_dirs():
    try:
        return {d for d in os.listdir(MEDIA) if os.path.isdir(os.path.join(MEDIA, d)) and d.startswith(('cDNG', 'MLV'))}
    except OSError:
        return set()


PRESERVE = set()      # clip folders that were on the drive when the campaign started: never deleted
CLEAR_ALL = False


def dropped_none(row):
    return int(_num(row.get('dropped')) or 0) == 0


def own_clip_add(out, name):
    OWN['clips'].add(name)
    with open(out + '/own_clips.txt', 'a') as f:
        f.write(name + '\n')


def own_clips_load(out):
    """The clip folders this run made so far; a take the runner did not survive (power cut, SIGKILL) left its clip and the
    in-progress marker, so the clip that appeared after the marker's start is claimed as ours."""
    p = out + '/own_clips.txt'
    OWN['clips'] = {l.strip() for l in open(p) if l.strip()} if os.path.exists(p) else set()
    m = out + '/take_in_progress.json'
    if os.path.exists(m):
        try:
            info = json.load(open(m))
            for d in clip_dirs() - set(info.get('before', [])):
                try:
                    if os.path.getmtime(os.path.join(MEDIA, d)) >= float(info.get('started', 0)) - 60:
                        own_clip_add(out, d)
                        log(out, 'claimed %s: the clip of a take this runner did not survive' % d)
                except OSError:
                    pass
        except (ValueError, OSError):
            pass
        os.unlink(m)


def clear_media(out):
    """Remove leftover clip folders THIS RUN made (after a crash or a power cut) so the next take has the room. Clips other
    sessions made during the campaign, and those that were on the drive at the start, stay unless --clear-all was given
    (the 2026-11-07 drive holds 143 GB of older takes)."""
    present = clip_dirs()
    mine = present if CLEAR_ALL else (present & OWN['clips'])
    n = 0
    for d in sorted(mine):
        shutil.rmtree(os.path.join(MEDIA, d), ignore_errors=True)
        OWN['clips'].discard(d)
        n += 1
    foreign = present - mine - PRESERVE
    if foreign and SAID.get('foreign') != foreign:
        SAID['foreign'] = foreign
        log(out, 'leaving %d clip folder(s) another session made: %s' % (len(foreign), ', '.join(sorted(foreign))[:200]))
    if n:
        log(out, 'cleared %d clip folder(s) from %s; free now %.0f GiB' % (
            n, MEDIA, os.statvfs(MEDIA).f_bavail * os.statvfs(MEDIA).f_frsize / 2**30))
        time.sleep(8)   # Core's own trim (if on) runs after a big delete; we do not wait for cooling


WEB_REMOTE = False


def web_peers(loopback=False):
    """Clients holding a connection to Core's WebUI port; loopback ones count only with loopback=True (the NVMe campaign's
    Pi-local stand-in, 2026-11-10: the campaign runs without the Mac)."""
    try:
        r = subprocess.run(['ss', '-tnH', 'state', 'established', '( sport = :8000 )'], capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return -1
    n = 0
    for l in r.stdout.splitlines():
        f = l.split()
        if len(f) >= 4 and (loopback or not f[3].startswith(('127.', '[::1]', '::1'))):
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


def log_probe(out):
    """Core says Log is not applied: make a 4 s take and read what Core logs about CineMate Log (its reason, or the plan)."""
    before = clip_dirs()
    t_wall = time.time()
    r = core('record_start')
    if not r.get('ok'):
        return 'probe take failed: %s' % r.get('error')
    time.sleep(4)
    core('record_stop')
    for _ in range(60):
        s2 = state()
        if s2 and not s2.get('recording') and not s2.get('media_writes_pending'):
            break
        time.sleep(1)
    time.sleep(2)
    lines = [re.sub(r'^\S+ \S+ \S+: ', '', l) for l in journal(t_wall) if 'CineMate Log' in l]
    for d in clip_dirs() - before:
        shutil.rmtree(os.path.join(MEDIA, d), ignore_errors=True)
    return ' | '.join(lines)[:300] or 'probe take made, Core logged nothing about Log'


def journal(t_wall):
    r = subprocess.run(['journalctl', '-u', 'apertar-core', '--since', '@%d' % int(t_wall), '-o', 'short-unix',
                        '--no-pager'], capture_output=True, text=True)
    return r.stdout.splitlines()


STAT_KEYS = ('enqueued', 'dropped_queue_full', 'dropped_gap_estimate', 'peak_queue', 'queue_bytes_peak', 'queue_budget',
             'write_failures', 'fault', 'written', 'dropped_copy_slot', 'index_jumps', 'discarded_on_stop')


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
    if rec.get('outcome') == 'buffer_full' or 'buffer_full' in kinds:
        pk = stats.get('peak_queue', '?')
        why.append('probable: the drive fell behind - the write queue filled the RAM buffer to Core\'s 90 %% safety stop '
                   '(peak queue %s frames, stopped after %.0f s)' % (pk, float(rec.get('seconds') or 0)))
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
  buffer_flush_discarded TEXT, tune_readback TEXT, core_cpu_avg REAL, core_cpu_max REAL, core_top_thread TEXT,
  queue_budget_mib REAL, budget_seconds REAL, recorder_stop_s REAL, stall_msg INT, idle_gap_s REAL, core_cpu_slope REAL,
  trim_before TEXT, format TEXT, buffer_unit TEXT, capacity_fps REAL, capacity_how TEXT, drain_mbps REAL);
CREATE TABLE IF NOT EXISTS samples(take_id TEXT, t_s REAL, pi_c REAL, nvme_c REAL, cpu_pct REAL, load1 REAL,
  mem_avail_mb REAL, fill_pct REAL, free_gb REAL, throttled TEXT, dropped INT, state TEXT, core_cpu_pct REAL,
  core_top_thread TEXT, buffer_used REAL, buffer_capacity REAL, dev_w_ios INT, dev_w_sectors INT, dev_w_ticks INT,
  dev_inflight INT, dirty_kb INT, writeback_kb INT, trim_running TEXT, trim_last_unix INT);
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
        for table, col, typ in (('takes', 'core_cpu_avg', 'REAL'), ('takes', 'core_cpu_max', 'REAL'), ('takes', 'core_top_thread', 'TEXT'),
                                ('takes', 'queue_budget_mib', 'REAL'), ('takes', 'budget_seconds', 'REAL'), ('takes', 'recorder_stop_s', 'REAL'),
                                ('takes', 'stall_msg', 'INT'), ('takes', 'idle_gap_s', 'REAL'), ('takes', 'core_cpu_slope', 'REAL'),
                                ('takes', 'trim_before', 'TEXT'), ('takes', 'format', 'TEXT'), ('takes', 'buffer_unit', 'TEXT'),
                                ('takes', 'capacity_fps', 'REAL'), ('takes', 'capacity_how', 'TEXT'), ('takes', 'drain_mbps', 'REAL'),
                                ('samples', 'core_cpu_pct', 'REAL'), ('samples', 'core_top_thread', 'TEXT'),
                                ('samples', 'buffer_used', 'REAL'), ('samples', 'buffer_capacity', 'REAL'), ('samples', 'dev_w_ios', 'INT'),
                                ('samples', 'dev_w_sectors', 'INT'), ('samples', 'dev_w_ticks', 'INT'), ('samples', 'dev_inflight', 'INT'),
                                ('samples', 'dirty_kb', 'INT'), ('samples', 'writeback_kb', 'INT'), ('samples', 'trim_running', 'TEXT'),
                                ('samples', 'trim_last_unix', 'INT')):
            if col not in [c[1] for c in con.execute('PRAGMA table_info(%s)' % table)]:
                con.execute('ALTER TABLE %s ADD COLUMN %s %s' % (table, col, typ))
        have_s = [c[1] for c in con.execute('PRAGMA table_info(samples)')]
        for col in SAMPLE_COLS:          # columns added after the table was made (the NVMe campaign's t_unix, clients, ...)
            if col not in have_s:
                con.execute('ALTER TABLE samples ADD COLUMN %s %s' % (col, 'TEXT' if col in ('throttled', 'state', 'core_top_thread', 'trim_running') else 'REAL'))
        for t in ('takes', 'samples', 'drop_events', 'stats', 'journal'):
            con.execute('DELETE FROM %s WHERE take_id=?' % t, (tid,))
        r = row
        con.execute('INSERT INTO takes VALUES (%s)' % ','.join('?' * 59), (
            tid, r.get('cfg_id'), r.get('mode'), int(r.get('bits') or 0), r.get('comp'), _flag(r.get('log')), _flag(r.get('tdn')),
            _flag(r.get('lock')), _flag(r.get('trim')), _flag(r.get('web')), _num(r.get('fps')), r.get('outcome'),
            _num(r.get('seconds')), int(_num(r.get('dropped')) or 0), _num(r.get('first_drop_s')), r.get('drop_kinds'),
            r.get('cause_estimate'), _num(r.get('pi_c')), _num(r.get('nvme_c')), _num(r.get('pi_c_max')),
            _num(r.get('nvme_c_max')), _num(r.get('cpu_pct')), _num(r.get('load1')), _num(r.get('mem_avail_mb')),
            _num(r.get('fill_pct')), r.get('throttled'), int(_num(r.get('files')) or 0), int(_num(r.get('missing')) or 0),
            r.get('audio'), _num(r.get('gb_written')), int(_num(r.get('trim_events')) or 0), r.get('drive_full'),
            _num(r.get('drive_full_at_s')), _num(r.get('start_pi_c')), _num(r.get('start_nvme_c')), r.get('clip'),
            r.get('started'), r.get('mismatch'), r.get('variant'), r.get('media_class'), r.get('buffer_setting'),
            r.get('buffer_safety_stop'), r.get('buffer_flush_discarded'), r.get('tune_readback'),
            _num(r.get('core_cpu_avg')), _num(r.get('core_cpu_max')), r.get('core_top_thread'),
            _num(r.get('queue_budget_mib')), _num(r.get('budget_seconds')), _num(r.get('recorder_stop_s')),
            int(_num(r.get('stall_msg')) or 0), _num(r.get('idle_gap_s')), _num(r.get('core_cpu_slope')), r.get('trim_before'),
            r.get('format'), r.get('buffer_unit'), _num(r.get('capacity_fps')), r.get('capacity_how'), _num(r.get('drain_mbps'))))
        numeric = {'t_s', 'pi_c', 'nvme_c', 'cpu_pct', 'load1', 'mem_avail_mb', 'fill_pct', 'free_gb', 'dropped', 'core_cpu_pct',
                   'buffer_used', 'buffer_capacity', 'dev_w_ios', 'dev_w_sectors', 'dev_w_ticks', 'dev_inflight', 'dirty_kb',
                   'writeback_kb', 'trim_last_unix', 't_unix', 'clients', 'merge_pending'}
        con.executemany('INSERT INTO samples(take_id, %s) VALUES (?, %s)' % (','.join(SAMPLE_COLS), ','.join('?' * len(SAMPLE_COLS))), [
            (tid,) + tuple((_num(x.get(k)) if k in numeric else x.get(k)) if x.get(k) not in ('', None) else None for k in SAMPLE_COLS)
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
        if r.get('outcome') in ('exhausted', 'pruned') or not r.get('fps'):
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
          'buffer_safety_stop', 'buffer_flush_discarded', 'tune_readback', 'buffer_peak_pct', 'core_cpu_avg', 'core_cpu_max',
          'core_top_thread', 'queue_budget_mib', 'budget_seconds', 'recorder_stop_s', 'stall_msg', 'idle_gap_s', 'core_cpu_slope',
          'trim_before', 'format', 'buffer_unit', 'capacity_fps', 'capacity_how', 'drain_mbps']


def append_row(out, row):
    p = out + '/results.csv'
    if os.path.exists(p):
        with open(p, newline='') as f:
            head = next(csv.reader(f), None)
        if head and head != FIELDS:      # a run started by an older runner: grow the header, keep every row
            rows = load_rows(out)
            with open(p + '.tmp', 'w', newline='') as f:
                w = csv.DictWriter(f, FIELDS, extrasaction='ignore')
                w.writeheader()
                w.writerows(rows)
            os.replace(p + '.tmp', p)
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
               ('kerneltune', {'kernel_tune': 'on'})]
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


def run_take(out, c, fps, max_seconds, written, stop_on_drop=True, variant='', tune_note='', fmt='cdng', before_cmds=(), expect=None):
    tid = '%s_fps%s_%s' % (c.id, int(fps), time.strftime('%Y%m%d-%H%M%S'))     # H2: the date, so ids never repeat
    row = {'take_id': tid, 'cfg_id': c.id, 'mode': c.key, 'bits': c.bits, 'comp': c.comp, 'log': c.log, 'tdn': c.tdn, 'lock': c.lock,
           'trim': c.trim, 'web': c.web, 'fps': fps, 'started': time.strftime('%F %T'), 'variant': variant,
           'tune_readback': tune_note, 'format': fmt}
    # Unattended operation: wait for a quiet Pi, check the hardware, check the write budget (plan section 7.1). The free
    # space the gate asks for is the take's projected writes (GiB) plus 10, or what the whole drive can hold: a take the
    # drive cannot hold ends at drive-full (pass_drive_full), which is a result, not a reason to wait.
    proj = projected_gb(c, fps, max_seconds)
    proj_gib = proj / 1.073741824
    try:
        sv = os.statvfs(MEDIA)
        total_gib = sv.f_blocks * sv.f_frsize / 2**30
    except OSError:
        total_gib = 0
    need = min(proj_gib + 10, max(total_gib - 10, 1)) if total_gib else proj_gib + 10
    if total_gib and proj_gib + 10 > total_gib - 10 and not SAID.get(('fits', c.key, fps)):
        SAID[('fits', c.key, fps)] = True
        log(out, '%s: a %d s take at %s fps could write %.0f GB, more than the %.0f GiB drive holds: it will end at drive-full' % (
            c.id, max_seconds or 1800, fps, proj, total_gib))
    code = wait_for_quiet(out, need_free_gib=need)
    if code:
        row['outcome'] = {'needs_human': 'needs_human', 'gate_timeout': 'gate_timeout', 'signal': 'stopped_by_signal'}[code]
        row['cause_estimate'] = {'needs_human': 'a condition only a human can clear (see the gate lines in runner.log)',
                                 'gate_timeout': 'the Pi did not become quiet within the gate timeout',
                                 'signal': 'stopped by %s while waiting at the gate' % STOP['sig']}[code]
        return row
    hold_lock(variant or 'take', (max_seconds or 1800) + 120)   # from here on the other sessions see a take being set up
    ok, why = hardware_ok(out)
    if not ok:
        row['outcome'] = 'watchdog'
        row['cause_estimate'] = why
        HALT['why'] = why
        release_lock()
        return row
    if BUDGET['gb'] and BUDGET['used'] + proj > BUDGET['gb']:
        row['outcome'] = 'budget_exceeded'
        row['cause_estimate'] = 'this take could write %.0f GB; %.0f of the %.0f GB budget are used' % (proj, BUDGET['used'], BUDGET['gb'])
        HALT['why'] = row['cause_estimate']
        release_lock()
        return row
    row['idle_gap_s'] = round(time.time() - LAST_END['t'], 1) if LAST_END['t'] else ''
    st = apply_cfg(c, fps, fmt)
    for cmd, kw in before_cmds:
        r0 = core(cmd, **kw)
        if not r0.get('ok'):
            # A refused stage command would run the arm as its opposite (the knob A/B "on" arm as "off"): not a result.
            row['outcome'] = 'before_cmd_refused'
            row['cause_estimate'] = '%s %s refused: %s' % (cmd, kw, r0.get('error'))
            log(out, '%s fps=%s: %s' % (c.id, fps, row['cause_estimate']))
            release_lock()
            return row
    if before_cmds:
        st = settle()
    mism = verify(c, fps, st, fmt, expect)
    row['mismatch'] = mism
    # Did a trim finish between the previous take's end and this one's start? (Core trims after a delete made outside it
    # since cinemate-port f4a1393; the result is only in its web state (/api/state), never in get_state or a journal window.)
    ws = web_state()
    tl = _num(ws.get('media_trim_last_unix'))
    row['trim_before'] = ('%s %s' % (ws.get('media_trim_last_result') or '?',
                                     'since-last-take' if (tl and LAST_END['t'] and tl >= LAST_END['t'] - 1) else 'older')
                          if ws.get('media_trim_last_result') is not None else '')
    if mism:
        row['outcome'] = 'skipped_unavailable' if 'log_applied' in mism and c.log else 'setup_mismatch'
        if row['outcome'] == 'skipped_unavailable':
            row['cause_estimate'] = 'Core: ' + log_probe(out)
        log(out, '%s fps=%s: %s (%s) %s' % (c.id, fps, row['outcome'], mism, row.get('cause_estimate', '')))
        release_lock()
        return row
    if st.get('media_state') != 'mounted':
        row['outcome'] = 'media_not_mounted'
        release_lock()
        return row
    if CAMPAIGN['on'] and CAMPAIGN['pre']:
        # void / WAITING checks of the fixed state (plan section 7, H10): a void or a wait is not a result
        o = CAMPAIGN['pre'](out, c, fps, st, row, max_seconds)
        if o:
            row['outcome'] = o
            release_lock()
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
        if CAMPAIGN['on']:
            row['_web_pid'] = web.pid
            row['webclient_ticks0'] = proc_ticks(web.pid)
    join_ingest()      # the previous take's logs went into the database while this one was being set up
    os.makedirs(out + '/samples', exist_ok=True)
    hold_lock(variant or 'take', max_seconds or 1800)
    t_wall = time.time()
    # If the runner dies during the take (power cut, SIGKILL), the resume reads this marker and claims the clip it left.
    json.dump({'before': sorted(before), 'started': t_wall, 'take_id': tid}, open(out + '/take_in_progress.json', 'w'))
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
        try:
            free_now = os.statvfs(MEDIA).f_bavail * os.statvfs(MEDIA).f_frsize
        except OSError:
            free_now = None
        if STOP['sig']:
            outcome, ctx_drop = 'stopped_by_signal', dict(last)
        elif CAMPAIGN['on'] and (free_now is None or time.time() - (last.get('t_unix') or time.time()) > 5):
            # H7: a dead medium or a sampler that stopped answering: stop the take, never call it a pass
            outcome, ctx_drop = 'fault', dict(last)
            row['cause_estimate'] = 'medium not readable (statvfs failed)' if free_now is None else 'the 1 Hz sampler stopped (%s)' % getattr(sam, 'last_error', '?')
            HALT['why'] = HALT['why'] or row['cause_estimate']
        elif stop_on_drop and last['dropped'] and last['dropped'] > 0:
            outcome, ctx_drop = 'drop', dict(last)
        elif free_now is not None and free_now < CAPACITY_GUARD:
            outcome = 'pass_drive_full'
        elif el >= (max_seconds or 1800):
            outcome = 'pass_30min' if not max_seconds else 'pass_capped_%ds' % max_seconds
            if max_seconds in TIER_NAMES:
                outcome = 'pass_' + TIER_NAMES[max_seconds]
        elif last['state'] != 'rec' and el > 3:
            # Core stopped the take itself. The RAM write buffer reaching 90 % (buffer_safety_stop) means the drive fell
            # behind: that is a result (the drive cannot carry this fps), not an outside interference.
            safety = any(x.get('_st', {}).get('buffer_safety_stop') for x in sam.rows[-12:])
            if safety:
                outcome = 'buffer_full'
            elif last['free_gb'] < 1.5:
                outcome = 'drive_full'
            else:
                outcome = 'stopped_externally'
            ctx_drop = dict(last)
        elif (last['_st'].get('recording_error') or last['_st'].get('recording_fault')):
            outcome, ctx_drop = 'fault', dict(last)
    seconds = time.monotonic() - t_rec
    ctx_end = dict(sam.last())
    core('record_stop')
    if web and CAMPAIGN['on']:
        row['webclient_alive_at_end'] = 1 if web.poll() is None else 0
        row['webclient_ticks1'] = proc_ticks(web.pid)
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
    for d in new:
        own_clip_add(out, d)
    try:
        os.unlink(out + '/take_in_progress.json')
    except OSError:
        pass
    files = missing = 0
    audio, size = '', 0
    if clip and os.path.isdir(clip):
        nums, af, mlvs = [], [], []
        # A split clip ([storage] frames_per_folder) keeps its DNGs in part_NNN/ folders: count them recursively; the
        # WAV and the other sidecars stay in the clip root. An MLV clip is one .mlv file (audio inside it).
        for dp, _dirs, names in os.walk(clip):
            for n in names:
                fp = os.path.join(dp, n)
                m = re.search(r'_(\d{9})\.dng$', n)
                if m: nums.append(int(m.group(1)))
                elif n.lower().endswith('.mlv'): mlvs.append(n)
                elif not n.endswith('.dng') and dp == clip: af.append('%s:%d' % (n, os.path.getsize(fp)))
        nums.sort()
        files = len(nums)
        missing = (nums[-1] + 1 - len(nums)) if nums else 0
        if CAMPAIGN['on'] and nums:
            # R3: where the missing frame numbers are (ranges), for the boundary flag and the drop timeline
            gaps, prev = [], nums[0] - 1
            if nums[0] > 0:
                gaps.append((0, nums[0] - 1))
            for n_ in nums:
                if n_ > prev + 1:
                    gaps.append((prev + 1, n_ - 1))
                prev = n_
            row['_gaps'] = gaps
        audio = ' '.join(af) if af else ('in-mlv' if mlvs else 'NONE')
    jl = journal(t_wall)
    if CAMPAIGN['on']:
        try:
            ul = subprocess.run(['journalctl', '-u', 'apertar-ui-direct', '--since', '@%d' % int(t_wall), '-o', 'short-unix',
                                 '--no-pager'], capture_output=True, text=True, timeout=60).stdout.splitlines()
        except (OSError, subprocess.SubprocessError):
            ul = []
        row['ui_mesa_errors'] = sum(1 for l in ul if 'MESA' in l)
        row['ui_journal_lines'] = len(ul)
        os.makedirs(out + '/journal-ui', exist_ok=True)
        with open(out + '/journal-ui/%s.log' % tid, 'w') as uf:     # first and last 50 lines: the errors repeat
            uf.write('\n'.join(ul[:50] + (['... %d lines ...' % (len(ul) - 100)] if len(ul) > 100 else []) + ul[50:][-50:]) + '\n')
    os.makedirs(out + '/journal', exist_ok=True)
    with open(out + '/journal/%s.log' % tid, 'w') as jf:   # raw Core journal for the take, to re-check a cause later
        jf.write('\n'.join(jl) + '\n')
    kinds, first, stats, trims = parse_journal(jl, t_rec_wall)
    # Core's RAM-buffer safety stop (90 % of the queue budget): its flag falls as soon as the queue drains, but the stats
    # line at the stop shows the queue's peak bytes against its budget. That is a result: the drive fell behind.
    try:
        fill = float(stats.get('queue_bytes_peak', 0)) / float(stats.get('queue_budget', 0) or 1)
    except ValueError:
        fill = 0.0
    row['buffer_peak_pct'] = round(100 * fill, 1)
    if outcome == 'stopped_externally' and fill >= 0.88:
        outcome = 'buffer_full'
        kinds['buffer_full'] = 1
    release_lock()
    st_end = state()
    row['buffer_unit'] = buffer_level()[2] or ''
    row['buffer_setting'] = st_end.get('buffer_setting')
    row['buffer_safety_stop'] = st_end.get('buffer_safety_stop')
    row['buffer_flush_discarded'] = st_end.get('buffer_flush_discarded')
    for l in jl:
        m = re.search(r'recording clip: .*?media_class=([a-z-]+)', l)
        if m:
            row['media_class'] = m.group(1)
    dropped = max(int(st_end.get('recording_dropped_frames', 0) or 0), int(ctx.get('dropped', 0) or 0), missing)
    if CAMPAIGN['on']:
        # R2 (plan revision item 4): a numbering gap is not a dropped picture. missing == index_jumps, every Core counter 0
        # and no capture-gap line: the time index skipped a number after a late timestamp, no frame was lost.
        counters = max(int(st_end.get('recording_dropped_frames', 0) or 0), int(ctx.get('dropped', 0) or 0))
        try:
            ij = int(stats.get('index_jumps', 0) or 0)
        except ValueError:
            ij = 0
        core_cnt = sum(int(stats.get(k, 0) or 0) for k in ('dropped_queue_full', 'dropped_copy_slot', 'write_failures')
                       if str(stats.get(k, '0')).isdigit())
        row['index_jumps'] = ij if 'index_jumps' in stats else ''
        row['numbering_gap'] = 0
        if missing > 0 and missing == ij and counters == 0 and core_cnt == 0 and 'capture-gap' not in kinds:
            row['numbering_gap'] = missing
            dropped = 0
        # H11: Core ends a take on an audio error as "recording failure: ... ALSA capture: ...": its own outcome
        fl = [l for l in jl if 'recording failure:' in l]
        row['failure_line'] = fl[-1].split('ApertarCore ', 1)[-1][:300] if fl else ''
        if any('ALSA capture' in l for l in fl):
            outcome = 'audio_fault'
        row['audio_missing'] = 0 if any('audio capture:' in l for l in jl) else 1
    gb = 0
    if clip and os.path.isdir(clip) and files:
        names = []
        for root_dir, _dirs, fnames in os.walk(clip):
            names += [os.path.join(root_dir, n) for n in fnames if n.endswith('.dng')][:20 - len(names)]
            if len(names) >= 20: break
        if names:
            gb = files * (sum(os.path.getsize(n) for n in names) / len(names)) / 1e9
    elif clip and os.path.isdir(clip):      # MLV: one file per clip, count every byte in the folder
        gb = sum(os.path.getsize(os.path.join(r_, n)) for r_, _d, fn in os.walk(clip) for n in fn) / 1e9
    # The writers' capacity from the buffer level (fps minus the buffer's slope), and from the free-space drain.
    frame_b = (gb * 1e9 / files) if files else (mode_size_mb(c.mode) * 1e6)
    cap, how = capacity_from_samples(sam.rows, fps, frame_b, row.get('buffer_unit') or 'frames')
    if cap is None:
        # The buffer filled within seconds (a 4K meter take at the top fps): Core's stats line still says how many frames
        # the writers took in the take's seconds (enqueued minus the queue's peak, which is the queue at a safety stop).
        try:
            enq = int(stats.get('enqueued', 0))
            peak = int(str(stats.get('peak_queue', '0')).split('/')[0])
        except (ValueError, TypeError):
            enq = peak = 0
        if enq >= 60 and peak > 0 and seconds >= 2:
            cap, how = round(fps * max(enq - peak, 0) / enq, 2), 'stats'
    row['capacity_fps'] = cap if cap is not None else ''
    row['capacity_how'] = how
    rec = [x for x in sam.rows if x.get('state') == 'rec' and x.get('free_gb') is not None]
    row['drain_mbps'] = round((rec[0]['free_gb'] - rec[-1]['free_gb']) * 1073.741824 / max(rec[-1]['t_s'] - rec[0]['t_s'], 1), 1) if len(rec) > 5 else ''
    cc = [x['core_cpu_pct'] for x in sam.rows if x.get('core_cpu_pct') is not None]
    row['core_cpu_avg'] = round(sum(cc) / len(cc), 1) if cc else ''
    row['core_cpu_max'] = max(cc) if cc else ''
    tt = collections.Counter(x.get('core_top_thread', '').split(':')[0] for x in sam.rows if x.get('core_top_thread'))
    row['core_top_thread'] = tt.most_common(1)[0][0] if tt else ''
    # The RAM budget in seconds of input, the stop time, the stop-path stall message, and the slope of Core's CPU over
    # the take (fraction of one core per second; with 5 directory entries per frame file, c = slope / (fps^2 x 5)).
    budget_b = float(stats.get('queue_budget', 0) or 0)
    frame_b = (gb * 1e9 / files) if files else (mode_size_mb(c.mode) * 1e6 if fmt == 'mlv' else 0)
    row['queue_budget_mib'] = round(budget_b / 2**20, 1) if budget_b else ''
    row['budget_seconds'] = round(budget_b / (fps * frame_b), 1) if budget_b and frame_b else ''
    stop_s = ''
    for l in jl:
        m = re.search(r'recorder stop time: ([\d.]+)s', l)
        if m: stop_s = float(m.group(1))
    row['recorder_stop_s'] = stop_s
    row['stall_msg'] = 1 if any('no frame written' in l or 'stopped responding' in l for l in jl) else 0
    pts = [(x['t_s'], x['core_cpu_pct'] / 100.0) for x in sam.rows
           if x.get('core_cpu_pct') is not None and x.get('state') == 'rec' and x['t_s'] > 20]
    if len(pts) >= 60:
        mx = sum(p[0] for p in pts) / len(pts); my = sum(p[1] for p in pts) / len(pts)
        sxx = sum((p[0] - mx) ** 2 for p in pts)
        row['core_cpu_slope'] = '%.3e' % (sum((p[0] - mx) * (p[1] - my) for p in pts) / sxx) if sxx else ''
    else:
        row['core_cpu_slope'] = ''
    if not stop_on_drop and outcome.startswith('pass'):
        outcome = 'ab_clean' if dropped == 0 else 'ab_dropped'
    if outcome == 'stopped_by_signal':
        row['cause_estimate'] = 'stopped by %s after %.0f s: not a result' % (STOP['sig'], seconds)
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
    if outcome not in ('record_start_failed', 'stopped_by_signal'):
        if dropped > 0 or outcome in ('fault', 'recording_stopped_by_core', 'drive_full', 'stopped_externally', 'buffer_full'):
            written_total = written['gb'] + gb
            row['outcome'], row['seconds'] = outcome, round(seconds, 1)
            row['cause_estimate'] = estimate_cause(c, fps, row, ctx, kinds, stats, written_total)
            if outcome in ('fault', 'recording_stopped_by_core', 'drive_full', 'stopped_externally', 'buffer_full'):
                row['cause_estimate'] = '%s: %s %s | %s' % (outcome, st_end.get('recording_error'), st_end.get('recording_fault'), row['cause_estimate'])
        else:
            row['cause_estimate'] = ''
    # delete only what this take made, then count what was written since the last trim
    if CAMPAIGN['on']:
        pass        # H5 / R5 (plan): clips stay until the fill gate needs the space; deleted only through Core's media route
    elif clip and os.path.isdir(clip) and clip.startswith((MEDIA + '/cDNG', MEDIA + '/MLV')):
        shutil.rmtree(clip, ignore_errors=True)
    BUDGET['used'] += gb
    ok, why = hardware_ok(out)
    if not ok:
        HALT['why'] = why
    written['gb'] = 0 if (trims or (c.trim and gb > 1)) else written['gb'] + gb
    if c.trim and gb > 1:
        time.sleep(8)   # Core's delete-batch trim runs on its own; we do not wait for cooling
    log(out, '%s fps=%s -> %s after %.0fs dropped=%s kinds=%s pi=%.0fC nvme=%s' % (
        c.id, fps, outcome, seconds, dropped, row['drop_kinds'], ctx.get('pi_c', 0), ctx.get('nvme_c')))
    row['_payload'] = {'samples': [{k: v for k, v in x.items() if k != '_st'} for x in sam.rows], 'journal': jl,
                       't_rec_wall': t_rec_wall}
    if CAMPAIGN['on'] and CAMPAIGN['post']:
        t0_, t1_ = row.get('webclient_ticks0'), row.get('webclient_ticks1')
        row['webclient_cpu_s'] = round((t1_ - t0_) / os.sysconf('SC_CLK_TCK'), 1) if (t0_ is not None and t1_ is not None) else ''
        row['rec_offset_s'] = round(t_rec - t0, 2)
        try:
            CAMPAIGN['post'](out, row, c, fps, sam.rows, jl, clip, stats, kinds)
        except Exception as e:      # noqa: BLE001 - the statistics must never lose the take
            log(out, 'WARNING: campaign post-take step failed for %s: %r' % (tid, e))
    LAST_END['t'] = time.time()
    return row


# ==== NVMe 4K campaign (--stages N --night ...): plan working/drop-frames/nvme-campaign/plan.md with its "Revision 2026-11-10",
# build list nvme-campaign/build-list.md sections H and R. Everything below runs on the Pi alone (User, 2026-11-10: "the campaign
# has to be able to run without the computer"): the WebUI stand-in is Pi-local, every night writes its own report, and the Pi is
# powered off by poweroff-after-night.sh when the night is over. Additions of 2026-11-10 (User): after every take of a tier of
# 15 min or more the merge is switched on and the runner waits for it (merge statistics); every split take records its part
# boundaries (the 8ec2f1a check) and its index jumps (the e298d4a check); flat controls run past their first drop so the flat
# folder's cost curve per 4K mode says when the split is needed.
HELPER = '/usr/local/libexec/apertar-campaign-helper'
YAML_SRC = '/home/pi/Tuning-Files/pipeline/pisp-depth4.yaml'
YAML_RUN = '/run/apertar-media/pisp-pipeline.yaml'
YAML_MD5 = '88929ca34bc8e4e8d4ab5ffaac1e2b64'        # num_cfe_config_queue 4 (R2 section 2g; read on the Pi 2026-11-10)
SPLIT_DEFAULT = 5000                                  # R1: every scored take is split, as Patrik shoots
BOUNDARY_WINDOW = 64                                  # R3: a drop within 64 frames after a part boundary is a boundary drop
FILL_HEADROOM = 0.10     # of the card kept free after every take (see ctake)
MERGE_AFTER_S = 900                                   # User 2026-11-10: merge after every take of a tier >= 15 min
EARLY_S = 600                                         # plan section 7: a long-tier drop before minute 10 is early
WALK_C_PROBE_NS = 63.3                                # probe 2026-11-08: ns per directory entry, the walk alone
FRAME_MB = {('4kHDR16', 'none', False): 16.59, ('4kHDR16', 'none', True): 12.45,   # plan section 3 (measured)
            ('4kSDR12', 'lossless_jpeg', False): 5.98}
BRACKET_TOP = {'4kHDR16': 30, '4kHDR12': 30}          # the record's brackets (plan section 5): 30 is the mode max
NIGHT_STAGES = ('SMOKE', 'S1', 'S2', 'S4', 'S5', 'S6', 'PARTB', 'END', 'ARMS')
GO_STAGES = ('S4', 'S5', 'S6', 'PARTB')
TIMERS = ('fstrim.timer', 'apt-daily.timer', 'apt-daily-upgrade.timer', 'man-db.timer', 'logrotate.timer')
CS = {'out': '', 'night': '', 'args': None, 'voids': 0, 'audio_faults': 0, 'arm_audio': {}, 'stop': '', 'core_pid': None,
      'serial': '', 'boot': '', 'tuning': None, 'seq': collections.Counter(), 'status_head': '', 'current': None,
      'audio_expected': True, 'decisions': [], 'night_t0': None, 'gb_night': 0.0, 'smart0': None, 'smart_last': None,
      'cold_wait_s': 0}

CAMPAIGN_SCHEMA = '''
CREATE TABLE IF NOT EXISTS clips(serial TEXT, clip TEXT, take_id TEXT, created REAL, mtime REAL, files INT, parts INT, bytes REAL,
  boot_id TEXT, merged INT DEFAULT 0, deleted REAL, delete_s REAL, delete_result TEXT, PRIMARY KEY(serial, clip, created));
CREATE TABLE IF NOT EXISTS merges(take_id TEXT, clip TEXT, files_before INT, parts_before INT, files_after INT, parts_left INT,
  marker_left INT, merge_s REAL, ms_per_file REAL, eta_first_s REAL, eta_first_at_s REAL, eta_err_pct REAL, samples INT, ok INT,
  readback_off INT, note TEXT);
CREATE TABLE IF NOT EXISTS merge_samples(take_id TEXT, t_s REAL, pending INT, active TEXT, paused TEXT, clip_done INT,
  clip_total INT, all_done INT, all_total INT, eta_s REAL);
CREATE TABLE IF NOT EXISTS boundaries(take_id TEXT, k INT, frame INT, t_s REAL, buf_max_pct REAL, buf_median_pct REAL,
  core_cpu_min REAL, core_cpu_median REAL, drops_in_window INT);
CREATE TABLE IF NOT EXISTS index_jumps(take_id TEXT, frame INT, count INT, skipped INT, dt_us INT, since_first_us INT);
CREATE TABLE IF NOT EXISTS minute_bins(take_id TEXT, minute INT, core_cpu REAL, buf_pct REAL, ticks_per_write REAL, nvme_c REAL,
  dirty_kb REAL, files_est INT);
CREATE TABLE IF NOT EXISTS take_extra(take_id TEXT, k TEXT, v TEXT);
CREATE TABLE IF NOT EXISTS smart(t REAL, night TEXT, take_id TEXT, data_units_written INT, temperature_c REAL, critical_warning INT,
  percent_used INT, thm1_count INT, thm2_count INT, raw TEXT);
CREATE TABLE IF NOT EXISTS s1_samples(run TEXT, t_s REAL, bytes INT, mbps REAL, nvme_c REAL, dev_w_ticks INT, dev_w_ios INT);
CREATE TABLE IF NOT EXISTS deletes(t REAL, clip TEXT, files INT, parts INT, cold INT, budget_s REAL, delete_s REAL, result TEXT);
CREATE TABLE IF NOT EXISTS cooldowns(t REAL, night TEXT, k INT, t_s REAL, nvme_c REAL, pi_c REAL);
'''
CAMPAIGN_FIELDS = ['night', 'stage', 'ckey', 'split', 'tier_s', 'planned_gb', 'fit_limited', 'void_reason', 'outcome_raw',
                   'numbering_gap', 'index_jumps', 'drop_frames', 'boundaries_crossed', 'boundary_drops', 'copy_slot_drops',
                   'boundary_buf_bump_pct', 'walk_ns_per_entry', 'walk_share_end_pct', 'signature', 'failure_line',
                   'audio_missing', 'audio_peak_backlog_kb', 'audio_discontinuities', 'audio_ring', 'webclient_cpu_s',
                   'webclient_alive_at_end', 'clients_min', 'merge_s', 'merge_ms_per_file', 'merge_ok', 'merge_eta_err_pct',
                   'hot_flag', 'throttled_hist', 'core_pid', 'uptime_s', 'memfree_mb', 'buddy_order8', 'takes_since_restart',
                   'smart_temp_c', 'smart_duw', 'rec_offset_s', 'verdict',
                   'audio_pre', 'audio_pre_wait_s', 'ui_pre', 'ui_mesa_errors', 'ui_journal_lines', 'ui_fds_max', 'ui_dmabuf_max',
                   'arec_fds_max', 'core_fds_max', 'cma_free_min_kb', 'audio_ready_min', 'audio_forensics', 'uiconf_rec_min',
                   'uiconf_dev_changed']
for _f in CAMPAIGN_FIELDS:
    if _f not in FIELDS:
        FIELDS.append(_f)


def proc_ticks(pid, dead_ok=False):
    """utime + stime of a process in clock ticks; None when it is gone."""
    try:
        st = open('/proc/%d/stat' % int(pid)).read()
        f = st[st.rindex(')') + 2:].split()
        return int(f[11]) + int(f[12])
    except (OSError, ValueError, IndexError, TypeError):
        return None


def boot_id():
    return rd('/proc/sys/kernel/random/boot_id', '') or ''


def unit_pid(unit):
    try:
        v = subprocess.run(['systemctl', 'show', '-p', 'MainPID', '--value', unit], capture_output=True, text=True,
                           timeout=10).stdout.strip()
        return int(v) if v.isdigit() and int(v) > 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


def proc_environ(pid):
    try:
        raw = open('/proc/%d/environ' % pid, 'rb').read().split(b'\0')
        return dict(x.decode(errors='replace').split('=', 1) for x in raw if b'=' in x)
    except (OSError, TypeError):
        return {}


def fe_depth4(env):
    """FE Config depth 4 in Core's environment: LIBCAMERA_RPI_CONFIG_FILE names a file with the depth-4 md5. Since 2026-11-06
    /home/pi/start-apertar-core.sh exports the Tuning-Files copy itself (survives every boot; found 2026-11-10), so the /run copy of
    the campaign drop-in is one of two accepted paths, not the only one."""
    p = env.get('LIBCAMERA_RPI_CONFIG_FILE')
    if not p:
        return False, 'LIBCAMERA_RPI_CONFIG_FILE is not in Core\'s environment (sudo %s arm)' % HELPER
    m = md5_of(p)
    if m != YAML_MD5:
        return False, '%s has md5 %s, not the depth-4 file %s' % (p, m or 'unreadable', YAML_MD5[:8])
    return True, p


def md5_of(path):
    import hashlib
    try:
        return hashlib.md5(open(path, 'rb').read()).hexdigest()
    except OSError:
        return ''


def card_facts():
    """The recording card: model, serial, firmware from sysfs (H6), size and free bytes of the mount."""
    d = {k: (rd('/sys/class/nvme/nvme0/%s' % k, '') or '').strip() for k in ('model', 'serial', 'firmware_rev')}
    try:
        sv = os.statvfs(MEDIA)
        d['size_b'], d['free_b'] = sv.f_blocks * sv.f_frsize, sv.f_bavail * sv.f_frsize
    except OSError:
        d['size_b'] = d['free_b'] = 0
    try:
        d['mount'] = subprocess.run(['findmnt', '-no', 'SOURCE,FSTYPE,OPTIONS', MEDIA], capture_output=True, text=True,
                                    timeout=10).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        d['mount'] = ''
    return d


def helper(word, timeout=300):
    """The campaign root helper's unattended words (sudo -n: fails closed when sudoers does not allow the word)."""
    if not os.path.exists(HELPER):
        return 127, 'helper not installed (%s)' % HELPER
    try:
        r = subprocess.run(['sudo', '-n', HELPER, word], capture_output=True, text=True, timeout=timeout)
        return r.returncode, (r.stdout + r.stderr).strip()
    except (OSError, subprocess.SubprocessError) as e:
        return 1, repr(e)


def smartlog():
    """smart-log through the helper (A18/H14): {} when the helper is absent or the output is not readable."""
    rc, txt = helper('smartlog', 60)
    if rc != 0:
        return {'error': txt[:200]}
    i = txt.find('{')
    try:
        j = json.loads(txt[i:txt.rindex('}') + 1]) if i >= 0 else {}
    except ValueError:
        j = {}
    if not j:       # plain text: "key : value" lines
        for l in txt.splitlines():
            if ':' in l:
                k, v = l.split(':', 1)
                j[k.strip().lower().replace(' ', '_')] = v.strip()
    def n(*keys):
        for k in keys:
            v = j.get(k)
            if v is None:
                continue
            try:
                return int(str(v).replace(',', '').split()[0])
            except ValueError:
                continue
        return None
    t = n('temperature')
    if t is not None and t > 200:
        t -= 273      # nvme-cli json gives Kelvin
    return {'data_units_written': n('data_units_written'), 'temperature_c': t, 'critical_warning': n('critical_warning'),
            'percent_used': n('percent_used', 'percentage_used'), 'thm1': n('thm_temp1_trans_count', 'thermal_management_t1_trans_count'),
            'thm2': n('thm_temp2_trans_count', 'thermal_management_t2_trans_count'), 'raw': txt[:2000]}


def smart_record(out, take_id=''):
    s = smartlog()
    CS['smart_last'] = s
    if 'error' in s:
        return s
    con = sqlite3.connect(out + '/longtakes.db', timeout=60)
    try:
        con.execute('INSERT INTO smart VALUES (?,?,?,?,?,?,?,?,?,?)', (time.time(), CS['night'], take_id, s['data_units_written'],
                    s['temperature_c'], s['critical_warning'], s['percent_used'], s['thm1'], s['thm2'], s['raw']))
        con.commit()
    finally:
        con.close()
    return s


def busy_sessions():
    """H10: pty login sessions with a running child process other than their shell (an idle ssh shell is exempt)."""
    busy = []
    try:
        for l in subprocess.run(['who'], capture_output=True, text=True, timeout=10).stdout.splitlines():
            f = l.split()
            if len(f) < 2 or not f[1].startswith('pts/'):
                continue
            ps = subprocess.run(['ps', '-t', f[1], '-o', 'stat=,comm='], capture_output=True, text=True, timeout=10).stdout.split('\n')
            procs = [p.split(None, 1) for p in ps if p.strip()]
            run = [c for s_, c in (p for p in procs if len(p) == 2) if c not in ('bash', 'sh', 'zsh', 'sshd', '-bash', 'tmux')]
            if run:
                busy.append('%s: %s' % (f[1], ','.join(run)[:60]))
    except (OSError, subprocess.SubprocessError):
        pass
    return busy


def ui_drawing(window=5.0):
    """H10: the touch UI service active AND drawing (its CPU time advancing); a SIGSTOPped UI stays 'active'. Summed over the
    service's cgroup: its MainPID is the run_pi_direct.sh wrapper, the Qt UI is a child (found in the smoke test, 2026-11-10)."""
    cg = '/sys/fs/cgroup/system.slice/apertar-ui-direct.service/cgroup.procs'

    def ticks():
        try:
            pids = [int(x) for x in open(cg).read().split()]
        except (OSError, ValueError):
            pids = [p for p in [unit_pid('apertar-ui-direct')] if p]
        return sum(proc_ticks(p) or 0 for p in pids), len(pids)
    a0, n = ticks()
    if not n:
        return False, 'apertar-ui-direct has no process'
    time.sleep(window)
    a1, _n = ticks()
    return (a1 > a0), 'ui ticks +%d in %.0f s (%d processes)' % (a1 - a0, window, n)


def decide(out, text):
    line = time.strftime('%F %T ') + '[%s] ' % CS['night'] + text
    CS['decisions'].append(line)
    with open(out + '/decisions.log', 'a') as f:
        f.write(line + '\n')
    log(out, 'DECISION ' + text)


def cdb(out):
    con = sqlite3.connect(out + '/longtakes.db', timeout=60)
    con.executescript(CAMPAIGN_SCHEMA)
    return con


def write_atomic(path, text):
    with open(path + '.tmp', 'w') as f:
        f.write(text)
    os.replace(path + '.tmp', path)


# ---- the clip ledger (H5): every campaign clip keyed by card serial, clip name, creation time and take id --------------------
def clip_count(path):
    """(dng files, part folders, .parts marker) of a clip folder, recursive."""
    files = parts = 0
    for dp, dirs, names in os.walk(path):
        if dp == path:
            parts = sum(1 for d in dirs if d.startswith('part_'))
        files += sum(1 for n in names if n.endswith('.dng'))
    return files, parts, os.path.exists(os.path.join(path, '.parts'))


def ledger_add(out, row, clip):
    if not clip or not os.path.isdir(clip):
        return
    files, parts, _m = clip_count(clip)
    con = cdb(out)
    try:
        con.execute('INSERT OR REPLACE INTO clips(serial, clip, take_id, created, mtime, files, parts, bytes, boot_id) VALUES (?,?,?,?,?,?,?,?,?)',
                    (CS['serial'], os.path.basename(clip), row.get('take_id'), time.time(), os.path.getmtime(clip), files, parts,
                     float(row.get('gb_written') or 0) * 1e9, boot_id()))
        con.commit()
    finally:
        con.close()


def ledger_update(out, name, **kw):
    con = cdb(out)
    try:
        sets = ', '.join('%s=?' % k for k in kw)
        con.execute('UPDATE clips SET %s WHERE serial=? AND clip=? AND deleted IS NULL' % sets, list(kw.values()) + [CS['serial'], name])
        con.commit()
    finally:
        con.close()


def ledger_live(out):
    con = cdb(out)
    try:
        return [dict(zip(('clip', 'take_id', 'created', 'mtime', 'files', 'parts', 'bytes', 'boot_id', 'merged'), r)) for r in con.execute(
            'SELECT clip, take_id, created, mtime, files, parts, bytes, boot_id, merged FROM clips WHERE serial=? AND deleted IS NULL '
            'ORDER BY created', (CS['serial'],))]
    finally:
        con.close()


def foreign_folders(out):
    """Clip folders on the card the database did not create (plan section 7: WAITING, never deleted)."""
    known = {c['clip'] for c in ledger_live(out)} | set(CS.get('preserve') or ())
    return sorted(clip_dirs() - known)


def cold_budget_s(files, parts):
    """Probe step 4: a delete after a reboot costs 13.6 s x (files / 10,000)^2 per folder (cold unlink, linear per entry)."""
    if parts:
        per = files / max(parts, 1)
        return parts * 13.6 * (per / 1e4) ** 2
    return 13.6 * (files / 1e4) ** 2


def media_delete(out, name):
    """Core's media route by exact name (A3''; pauses a merge, deletes, trims): (ok, message, seconds). Never rm, never a glob."""
    import urllib.request, urllib.parse
    for _ in range(120):
        st = state()
        if st and not st.get('recording') and not st.get('media_writes_pending'):
            break
        time.sleep(1)
    t = time.monotonic()
    try:
        req = urllib.request.Request('http://127.0.0.1:8000/api/media/delete?kind=folder&id=%s' % urllib.parse.quote(name),
                                     data=b'', method='POST')
        body = urllib.request.urlopen(req, timeout=1800).read().decode(errors='replace')
        ok = '"ok":true' in body.replace(' ', '')
    except Exception as e:      # noqa: BLE001
        body, ok = getattr(e, 'read', lambda: b'')().decode(errors='replace') if hasattr(e, 'read') else repr(e), False
    return ok and not os.path.exists(os.path.join(MEDIA, name)), body[:300], round(time.monotonic() - t, 2)


def delete_clip(out, c):
    """Re-stat against the ledger, then the media route. Returns '' or a WAITING reason."""
    path = os.path.join(MEDIA, c['clip'])
    if not os.path.isdir(path):
        ledger_update(out, c['clip'], deleted=time.time(), delete_result='gone before delete')
        return ''
    files, parts, _m = clip_count(path)
    if files != int(c['files'] or 0):
        return 'WAITING: foreign folder (%s has %d frames, the ledger %s)' % (c['clip'], files, c['files'])
    cold = (c.get('boot_id') or '') != boot_id()
    budget = cold_budget_s(files, parts) if cold else files * 5e-6
    log(out, 'fill gate: deleting %s (%d frames, %d parts, %s, budget %.0f s) through the media route' % (
        c['clip'], files, parts, 'cold: written before this boot' if cold else 'warm', budget))
    ok, msg, secs = media_delete(out, c['clip'])
    con = cdb(out)
    try:
        con.execute('INSERT INTO deletes VALUES (?,?,?,?,?,?,?,?)', (time.time(), c['clip'], files, parts, int(cold), budget, secs, msg[:200]))
        con.commit()
    finally:
        con.close()
    if not ok:
        return 'WAITING: delete failed for %s (%s)' % (c['clip'], msg[:120])
    ledger_update(out, c['clip'], deleted=time.time(), delete_s=secs, delete_result='ok')
    decide(out, 'deleted %s: %d frames in %.1f s (%s, budget %.0f s)' % (c['clip'], files, secs, 'cold' if cold else 'warm', budget))
    if cold:
        CS['cold_wait_s'] = max(CS['cold_wait_s'], getattr(CS.get('args'), 'cold_wait', 600))
    return ''


def wait_trim(t_before, cap=60):
    t = time.monotonic()
    while time.monotonic() - t < cap:
        ws = web_state()
        tl = _num(ws.get('media_trim_last_unix'))
        if tl and tl >= t_before and not ws.get('media_trim_running'):
            return True
        time.sleep(3)
    return False


def fill_gate(out, need_b):
    """Plan section 6: free >= need, else delete the OLDEST campaign clips until it fits. '' when it fits, else why not."""
    try:
        sv = os.statvfs(MEDIA)
        free = sv.f_bavail * sv.f_frsize
    except OSError:
        return 'medium not readable'
    if free >= need_b:
        return ''
    t0 = time.time()
    for c in ledger_live(out):
        if free >= need_b:
            break
        w = delete_clip(out, c)
        if w:
            return w
        sv = os.statvfs(MEDIA)
        free = sv.f_bavail * sv.f_frsize
    if time.time() > t0 + 1 and not wait_trim(t0):
        log(out, 'fill gate: Core\'s trim did not report within 60 s of the deletes; asking the helper for fstrim')
        helper('fstrim', 900)
    if CS['cold_wait_s']:
        decide(out, 'cold deletes after a reboot: %d s idle before the next take (plan: never within budget + 10 min)' % CS['cold_wait_s'])
        idle(out, CS['cold_wait_s'], 'drive idle after cold deletes')
        CS['cold_wait_s'] = 0
    return '' if free >= need_b else 'only %.0f GB free after deleting every campaign clip' % (free / 1e9)


def cooldown(out):
    """The hourly break (User 2026-11-10: "allow cooldown of nvme approx each hour"): before a take, when --cooldown-every seconds
    have passed since the night start or the last break, idle --cooldown-s seconds with the camera standing by, and log the NVMe and
    Pi temperatures every 10 s (table cooldowns) for the cooling curve. Never inside a take or a merge wait."""
    a = CS['args']
    every = getattr(a, 'cooldown_every', 0)
    if not every or STOP['sig'] or CS['stop']:
        return
    t_last = CS.get('cool_t') or CS['night_t0'] or time.time()
    if time.time() - t_last < every:
        return
    k = CS.get('cool_k', 0) + 1
    CS['cool_k'] = k
    secs = a.cooldown_s
    temp = lambda path: round(float(rd(path, 0) or 0) / 1000, 1) if path else None
    status(out, 'COOLDOWN %d until %s (the hourly break, %d s): safe to read' % (
        k, time.strftime('%H:%M', time.localtime(time.time() + secs)), secs))
    n0, p0 = temp(NVME_TEMP), temp(PI_TEMP)
    con = cdb(out)
    t0 = time.monotonic()
    try:
        while not STOP['sig']:
            el = time.monotonic() - t0
            con.execute('INSERT INTO cooldowns VALUES (?,?,?,?,?,?)', (time.time(), CS['night'], k, round(el, 1), temp(NVME_TEMP), temp(PI_TEMP)))
            con.commit()
            if el >= secs:
                break
            time.sleep(10)
    finally:
        con.close()
    decide(out, 'cooldown %d: %d s; NVMe %s -> %s C, Pi %s -> %s C' % (k, round(time.monotonic() - t0), n0, temp(NVME_TEMP), p0, temp(PI_TEMP)))
    CS['cool_t'] = time.time()


def idle(out, seconds, why):
    status(out, 'IDLE until %s (%s): safe to read' % (time.strftime('%H:%M', time.localtime(time.time() + seconds)), why))
    t = time.monotonic()
    while time.monotonic() - t < seconds and not STOP['sig']:
        time.sleep(5)


# ---- the merge after a long take (User 2026-11-10: "the system waits for the merge after each long take") -------------------
def merge_and_wait(out, row, clip, cap_s=5400):
    tid = row['take_id']
    files0, parts0, mark0 = clip_count(clip)
    if not parts0 and not mark0:
        return
    status(out, 'MERGING %s (%d frames in %d parts): safe to read' % (os.path.basename(clip), files0, parts0))
    os.makedirs(out + '/merge', exist_ok=True)
    t_wall, t0 = time.time(), time.monotonic()
    core('set_clip_merge', enabled=True)
    samples, seen_active = [], False
    with open(out + '/merge/%s.csv' % tid, 'w') as f:
        f.write('t_s,pending,active,paused,clip_done,clip_total,all_done,all_total,eta_s\n')
        while time.monotonic() - t0 < cap_s and not STOP['sig']:
            st = state()
            el = round(time.monotonic() - t0, 1)
            smp = (el, st.get('clip_merge_pending'), st.get('clip_merge_active') or '', st.get('clip_merge_paused') or '',
                   st.get('clip_merge_clip_done'), st.get('clip_merge_clip_total'), st.get('clip_merge_all_done'),
                   st.get('clip_merge_all_total'), st.get('clip_merge_eta_s'))
            samples.append(smp)
            f.write(','.join(str(x) for x in smp) + '\n'); f.flush()
            seen_active = seen_active or bool(smp[2])
            _f, p_left, m_left = clip_count(clip) if el > 120 or not smp[2] else (0, 1, True)
            fs_done = not p_left and not m_left
            if not smp[2] and not smp[1] and (seen_active or fs_done or el > 30):
                break
            time.sleep(1 if el < 20 else 10)
    merge_s = round(time.monotonic() - t0, 1)
    r_off = core('set_clip_merge', enabled=False)
    st = state()
    files1, parts1, mark1 = clip_count(clip)
    eta = [(s_[0], float(s_[8])) for s_ in samples if s_[8] not in (None, '', 0, 0.0) and s_[2]]
    eta_first_at, eta_first = (eta[0] if eta else (None, None))
    err = round(100 * ((eta_first_at + eta_first) - merge_s) / merge_s, 1) if eta and merge_s else None
    ok = int(files1 == files0 and parts1 == 0 and not mark1)
    jl = [l for l in journal(t_wall - 2) if 'clip merge' in l]
    note = ' | '.join(l.split('ApertarCore ', 1)[-1] for l in jl[-3:])[:400]
    # Core's own timing of the merge ("clip merge: done <clip> files=N seconds=S per_file_ms=M"); the poll time is the fallback
    done = [re.search(r'clip merge: done %s files=(\d+) seconds=([\d.]+)' % re.escape(os.path.basename(clip)), l) for l in jl]
    done = [d for d in done if d]
    poll_s = merge_s
    if done:
        merge_s = float(done[-1].group(2))
    note = ('poll %.1f s; ' % poll_s) + note
    con = cdb(out)
    try:
        con.execute('INSERT INTO merges VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)', (
            tid, os.path.basename(clip), files0, parts0, files1, parts1, int(mark1), merge_s, round(1000 * merge_s / max(files0, 1), 3),
            eta_first, eta_first_at, err, len(samples), ok, int(st.get('clip_merge_enabled') is False and bool(r_off.get('ok'))), note))
        con.executemany('INSERT INTO merge_samples VALUES (?,?,?,?,?,?,?,?,?,?)', [(tid,) + s_ for s_ in samples])
        con.commit()
    finally:
        con.close()
    row.update({'merge_s': merge_s, 'merge_ms_per_file': round(1000 * merge_s / max(files0, 1), 3), 'merge_ok': ok,
                'merge_eta_err_pct': err if err is not None else ''})
    ledger_update(out, os.path.basename(clip), merged=1, mtime=os.path.getmtime(clip), files=files1, parts=parts1)
    decide(out, 'merge of %s: %d frames, %d parts, %.0f s (%.2f ms per frame), first ETA error %s %%, %s; merge off again: %s' % (
        os.path.basename(clip), files0, parts0, merge_s, 1000 * merge_s / max(files0, 1), err, 'intact' if ok else
        'NOT INTACT (%d frames after, %d parts left, marker %s)' % (files1, parts1, mark1), st.get('clip_merge_enabled') is False))
    if not ok:
        CS['stop'] = CS['stop'] or 'merge left %s not intact' % os.path.basename(clip)


# ---- per-take statistics (R2, R3, the fix checks, the split-need curve, the attribution signatures) --------------------------
def _median(v):
    v = sorted(x for x in v if x is not None)
    return v[len(v) // 2] if v else None


def campaign_post(out, row, c, fps, samples, jl, clip, stats, kinds):
    tid = row['take_id']
    row['tier_s'] = CS.get('tier_s') or row.get('tier_s')     # set by ctake() before run_take(): the merge-after rule reads it
    devs = set(x.get('uiconf_dev') for x in samples if x.get('uiconf_dev') is not None)
    row['uiconf_dev_changed'] = ' | '.join(sorted(map(repr, devs))) if len(devs) > 1 else ''
    for k, f in (('ui_fds', max), ('ui_dmabuf', max), ('arec_fds', max), ('core_fds', max), ('cma_free_kb', min), ('audio_ready', min),
                 ('uiconf_rec', min)):
        v = [x.get(k) for x in samples if x.get(k) is not None]
        row[{'cma_free_kb': 'cma_free_min_kb', 'audio_ready': 'audio_ready_min', 'uiconf_rec': 'uiconf_rec_min'}.get(k, k + '_max')] = f(v) if v else ''
    off = float(row.get('rec_offset_s') or 0)
    rec = [x for x in samples if x.get('state') == 'rec']
    fpf = int(c.split or 0)
    # first drop from the 1 Hz samples (H11), not from rate-limited journal lines
    fd = next((x for x in samples if (x.get('dropped') or 0) > 0), None)
    if fd is not None:
        row['first_drop_s'] = round(float(fd['t_s']) - off, 1)
    # where the missing frames are (R3) and the boundary flag
    gaps = row.pop('_gaps', [])
    frames = []
    for a_, b_ in gaps:
        frames.extend(range(a_, min(b_, a_ + 500) + 1))
    for l in jl:
        m = re.search(r'drop\[(queue-full|copy-slot)\]: frame=(\d+)', l)
        if m:
            frames.append(int(m.group(2)))
    frames = sorted(set(frames))
    row['drop_frames'] = ' '.join('%d-%d' % g if g[1] > g[0] else '%d' % g[0] for g in gaps[:30])
    row['boundary_drops'] = sum(1 for f in frames if fpf and f >= fpf and f % fpf < BOUNDARY_WINDOW) if fpf else ''
    row['copy_slot_drops'] = stats.get('dropped_copy_slot', '')
    files = int(row.get('files') or 0)
    row['boundaries_crossed'] = (files - 1) // fpf if (fpf and files) else 0
    # the 8ec2f1a check: the buffer and Core's CPU around every part boundary against the take's median
    used = [(float(x['t_s']) - off, 100.0 * float(x['buffer_used']) / float(x['buffer_capacity']))
            for x in rec if x.get('buffer_used') not in (None, '') and x.get('buffer_capacity')]
    med_buf = _median([u for _t, u in used])
    med_cpu = _median([x.get('core_cpu_pct') for x in rec])
    bl, bump = [], 0.0
    if fpf and files:
        for k in range(1, row['boundaries_crossed'] + 1):
            tb = k * fpf / float(fps)
            win = [u for t_, u in used if tb - 1 <= t_ <= tb + 3]
            cpu = [x.get('core_cpu_pct') for x in rec if tb - 1 <= float(x['t_s']) - off <= tb + 3 and x.get('core_cpu_pct') is not None]
            dw = sum(1 for f in frames if k * fpf <= f < k * fpf + BOUNDARY_WINDOW)
            bmax = max(win) if win else None
            if bmax is not None and med_buf is not None:
                bump = max(bump, bmax - med_buf)
            bl.append((tid, k, k * fpf, round(tb, 1), bmax, med_buf, min(cpu) if cpu else None, med_cpu, dw))
    row['boundary_buf_bump_pct'] = round(bump, 2) if bl else ''
    # the e298d4a check: every "frame index jump" line
    ij = []
    for l in jl:
        m = re.search(r'frame index jump: frame=(\d+) count=(\d+) skipped=(\d+) dt_us=(-?\d+) since_first_us=(\d+)', l)
        if m:
            ij.append((tid,) + tuple(int(g) for g in m.groups()))
    # minute bins (the split-need curve): Core CPU, buffer, device ticks per write, temperature, dirty pages
    bins = []
    for mnt in range(0, int((float(row.get('seconds') or 0)) // 60) + 1):
        w = [x for x in rec if mnt * 60 <= float(x['t_s']) - off < (mnt + 1) * 60]
        if len(w) < 10:
            continue
        cpu = [x['core_cpu_pct'] for x in w if x.get('core_cpu_pct') is not None]
        bu = [100.0 * float(x['buffer_used']) / float(x['buffer_capacity']) for x in w if x.get('buffer_used') not in (None, '') and x.get('buffer_capacity')]
        tk = None
        if w[0].get('dev_w_ios') is not None and w[-1].get('dev_w_ios') is not None and w[-1]['dev_w_ios'] > w[0]['dev_w_ios']:
            tk = round((w[-1]['dev_w_ticks'] - w[0]['dev_w_ticks']) / float(w[-1]['dev_w_ios'] - w[0]['dev_w_ios']), 3)
        nv = [x['nvme_c'] for x in w if x.get('nvme_c')]
        dk = [x['dirty_kb'] for x in w if x.get('dirty_kb') is not None]
        n_est = int(fps * (mnt + 0.5) * 60)
        bins.append((tid, mnt, round(sum(cpu) / len(cpu), 1) if cpu else None, round(sum(bu) / len(bu), 2) if bu else None, tk,
                     max(nv) if nv else None, round(sum(dk) / len(dk)) if dk else None, (n_est % fpf) if fpf else n_est))
    # the walk cost from Core's CPU slope: slope (cores per s) = 5 entries x c x fps^2 in a flat folder
    sl = _num(row.get('core_cpu_slope'))
    if sl is not None and not fpf and fps:
        row['walk_ns_per_entry'] = round(1e9 * sl / (5 * fps * fps), 1)
    n_end = (files % fpf if fpf else files) or files
    c_ns = _num(row.get('walk_ns_per_entry')) or WALK_C_PROBE_NS
    row['walk_share_end_pct'] = round(100 * c_ns * 1e-9 * 5 * (fpf if fpf else n_end) * fps, 1) if files else ''
    # attribution signature of a late drop (plan section 7, H22): directory / drive state / heat / page cache / capture side
    row['signature'] = signature(row, bins, sl, fpf) if row.get('first_drop_s') not in ('', None) and float(row.get('seconds') or 0) >= 600 else ''
    # audio (5a / H11)
    m = [re.search(r'peak_backlog_kb=(\d+)', l) for l in jl]
    row['audio_peak_backlog_kb'] = max([int(x.group(1)) for x in m if x] or [0]) if any(m) else ''
    row['audio_discontinuities'] = sum(1 for l in jl if 'audio discontinuity' in l)
    ring = next((re.search(r'buffer_frames=(\d+) period_frames=(\d+)', l) for l in jl if 'buffer_frames=' in l), None)
    row['audio_ring'] = '%s/%s' % ring.groups() if ring else ''
    # liveness of the client, heat, power, drift columns
    cl = [x.get('clients') for x in rec if x.get('clients') is not None]
    row['clients_min'] = min(cl) if cl else ''
    row['hot_flag'] = 1 if (_num(row.get('nvme_c_max')) or 0) > 75 else 0
    try:
        row['throttled_hist'] = subprocess.run(['vcgencmd', 'get_throttled'], capture_output=True, text=True, timeout=5).stdout.strip().split('=')[-1]
    except (OSError, subprocess.SubprocessError):
        row['throttled_hist'] = ''
    row['core_pid'] = CS['core_pid']
    row['uptime_s'] = int(float((rd('/proc/uptime', '0') or '0').split()[0]))
    mf = [l for l in open('/proc/meminfo') if l.startswith('MemFree')] if os.path.exists('/proc/meminfo') else []
    row['memfree_mb'] = int(mf[0].split()[1]) // 1024 if mf else ''
    bd = [l.split() for l in open('/proc/buddyinfo')] if os.path.exists('/proc/buddyinfo') else []
    row['buddy_order8'] = sum(int(f[4 + 8]) for f in bd if len(f) > 12)
    # voids found after the take (plan section 7)
    if row.get('outcome') not in ('void',) and c.web and row.get('webclient_alive_at_end') == 0:
        void(row, 'the Pi-local WebUI client died during the take')
    elif c.web and cl and min(cl) < 1:
        void(row, 'the WebUI client was not connected for part of the take')
    if CS['audio_expected'] and row.get('audio_missing') == 0:
        CS['audio_ok_t'] = time.time()
    elif CS['audio_expected'] and row.get('audio_missing') == 1:
        CS['audio_lost'] = CS.get('audio_lost', 0) + 1
        # the full UI + Core journal from the end of the last take with audio, the first time; the last 10 min after that
        row['audio_forensics'] = os.path.basename(audio_forensics(
            out, 'take-%s' % tid, CS.get('audio_ok_t') if CS['audio_lost'] == 1 else None))
    if row.get('outcome') in ('void',):
        pass
    elif CS['audio_expected'] and row.get('audio_missing') == 1 and row.get('outcome') not in ('record_start_failed',) \
            and getattr(CS['args'], 'audio_optional', False):
        # User 2026-11-10: "have the tests continue even without sound": the picture result counts, the row keeps audio_missing=1
        decide(out, 'no audio in %s (pre-check: %s; UI MESA errors in the take: %s): counted anyway (--audio-optional)' % (
            tid, row.get('audio_pre', '-'), row.get('ui_mesa_errors', '-')))
    elif CS['audio_expected'] and row.get('audio_missing') == 1 and row.get('outcome') not in ('record_start_failed',):
        void(row, 'audio_missing: no "audio capture" line in the take window (pre-check: %s; UI MESA errors in the take: %s)' % (
            row.get('audio_pre', '-'), row.get('ui_mesa_errors', '-')))
    con = cdb(out)
    try:
        con.executemany('INSERT INTO boundaries VALUES (?,?,?,?,?,?,?,?,?)', bl)
        con.executemany('INSERT INTO index_jumps VALUES (?,?,?,?,?,?)', ij)
        con.executemany('INSERT INTO minute_bins VALUES (?,?,?,?,?,?,?,?)', bins)
        con.commit()
    finally:
        con.close()
    ledger_add(out, row, clip)
    # the merge after a long take (User 2026-11-10), before anything else touches the card
    if clip and os.path.isdir(clip) and fpf and int(row.get('tier_s') or 0) >= MERGE_AFTER_S and row.get('outcome') not in ('void',):
        merge_and_wait(out, row, clip)


def signature(row, bins, slope, fpf):
    """Plan section 7's pre-registered reading of a late drop, in its order; thresholds are pre-registered choices."""
    if len(bins) < 6:
        return 'too short to read'
    n = len(bins)
    third = max(1, n // 3)
    tk1 = [b[4] for b in bins[:third] if b[4]]; tk3 = [b[4] for b in bins[-third:] if b[4]]
    t1 = sum(tk1) / len(tk1) if tk1 else None; t3 = sum(tk3) / len(tk3) if tk3 else None
    bu = [b[3] for b in bins]
    last5 = [x for x in bu[-5:] if x is not None]; before = [x for x in bu[:-5] if x is not None]
    nv = [b[5] for b in bins]; dk = [b[6] for b in bins]
    c_ns = (1e9 * slope / (5 * float(row['fps']) ** 2)) if (slope is not None and not fpf) else None
    if c_ns is not None and 63 <= c_ns <= 133 and t1 and t3 and abs(t3 - t1) / t1 <= 0.15 and len(last5) >= 2 and \
            (last5[-1] - last5[0]) > 5 * (max(before[-1] - before[0], 0) if len(before) >= 2 else 0):
        return 'directory (c=%.0f ns/entry, device latency flat)' % c_ns
    if t1 and t3 and t3 > 1.3 * t1:
        return 'drive state (ticks per write %.2f -> %.2f)' % (t1, t3)
    pairs = [(a_, b_[4]) for a_, b_ in zip(nv, bins) if a_ and b_[4]]
    if len(pairs) >= 6:
        mx = sum(p[0] for p in pairs) / len(pairs); my = sum(p[1] for p in pairs) / len(pairs)
        sxx = sum((p[0] - mx) ** 2 for p in pairs); syy = sum((p[1] - my) ** 2 for p in pairs)
        r = sum((p[0] - mx) * (p[1] - my) for p in pairs) / (sxx * syy) ** 0.5 if sxx and syy else 0
        if r > 0.7:
            return 'heat (r=%.2f temperature vs latency)' % r
    d1 = [x for x in dk[:third] if x is not None]; d3 = [x for x in dk[-third:] if x is not None]
    if d1 and d3 and sum(d3) / len(d3) > 2 * max(sum(d1) / len(d1), 1):
        return 'page cache (dirty x%.1f)' % ((sum(d3) / len(d3)) / max(sum(d1) / len(d1), 1))
    return 'capture side (no storage signature)'


def void(row, why):
    if row.get('outcome') != 'void':
        row['outcome_raw'] = row.get('outcome')
    row['outcome'] = 'void'
    row['void_reason'] = (row.get('void_reason') + '; ' if row.get('void_reason') else '') + why


def campaign_pre(out, c, fps, st, row, max_seconds):
    """Before record_start: WAITING conditions (hold and retry every 2 min, end the night after 30 min) and the void list of
    plan section 7 / H10. Returns '' (go), 'void' or 'waiting_timeout' / 'stop'."""
    t0 = time.monotonic()
    while True:
        wait = []
        ff = foreign_folders(out)
        if ff:
            wait.append('a folder on the card the database did not create: %s (Patrik moves it; it is never deleted)' % ', '.join(ff)[:200])
        st2 = state()
        if st2.get('clip_merge_active'):
            wait.append('a merge is running (%s)' % st2.get('clip_merge_active'))
        if not wait:
            break
        if time.monotonic() - t0 > 1800:
            CS['stop'] = 'WAITING for 30 min: ' + '; '.join(wait)
            return 'waiting_timeout'
        status(out, 'WAITING: ' + '; '.join(wait))
        log(out, 'WAITING: ' + '; '.join(wait))
        for _ in range(24):
            if STOP['sig']:
                return 'waiting_timeout'
            time.sleep(5)
    bad = []
    pid = unit_pid('apertar-core')
    if CS['core_pid'] and pid != CS['core_pid']:
        bad.append('Core restarted (pid %s -> %s)' % (CS['core_pid'], pid))
        CS['core_pid'] = pid
        core('set_clip_merge', enabled=False)       # plan section 7: re-sent after any Core restart, read back by the next check
        CS['need_warmup'] = True
    env = proc_environ(pid) if pid else {}
    if not CS['args'].no_dropin_check:
        ok_, why_ = fe_depth4(env)
        if not ok_:
            CS['stop'] = 'WAITING: re-arm (%s)' % why_
            return 'stop'
    if CS['args'].audio_ms and env.get('APERTAR_AUDIO_BUFFER_MS') != str(CS['args'].audio_ms):
        bad.append('APERTAR_AUDIO_BUFFER_MS=%s, the night wants %s' % (env.get('APERTAR_AUDIO_BUFFER_MS'), CS['args'].audio_ms))
    row['tune_readback'] = 'env:%s audio_ms:%s' % (env.get('LIBCAMERA_RPI_CONFIG_FILE', '-'), env.get('APERTAR_AUDIO_BUFFER_MS', '-'))
    cf = card_facts()
    if CS['serial'] and cf.get('serial') != CS['serial']:
        CS['stop'] = 'card serial %s, the night started on %s' % (cf.get('serial'), CS['serial'])
        return 'stop'
    if ' rw' not in ' ' + cf.get('mount', '').replace(',', ' ') :
        CS['stop'] = 'the card is not mounted read-write (%s)' % cf.get('mount')
        return 'stop'
    for k, want in (('fps_speed_ramp', False), ('ladder_enabled', False), ('storage_preroll_auto', True)):
        if bool(st.get(k)) != want:
            bad.append('%s=%s' % (k, st.get(k)))
    if bool(st.get('clip_merge_enabled')) != bool(getattr(c, 'merge_on', False)):
        bad.append('clip_merge_enabled=%s' % st.get('clip_merge_enabled'))
    if CS['tuning'] is not None and st.get('tuning_file') != CS['tuning']:
        bad.append('tuning_file=%s' % st.get('tuning_file'))
    ok, why = ui_drawing()
    if not ok:
        bad.append('touch UI not drawing (%s)' % why)
    if CS['audio_expected']:
        # night 1 (2026-11-10): Core recorded two takes without audio and said nothing; see what it sees before every take
        ta = time.monotonic()
        while True:
            ar, awhy = audio_ready(web_state(2.0))
            if ar or time.monotonic() - ta >= 60 or STOP['sig']:
                break
            time.sleep(5)
        row['audio_pre'] = ('ready' if ar else 'NOT READY: ' + awhy)[:300]
        row['audio_pre_wait_s'] = round(time.monotonic() - ta, 1)
        uh = ui_health()
        row['ui_pre'] = ' '.join('%s=%s' % kv for kv in uh.items())
        if not ar:
            row['audio_forensics'] = os.path.basename(audio_forensics(out, 'precheck-notready', CS.get('audio_ok_t')))
            decide(out, 'audio pre-check: Core does not see the mic after %.0f s (%s; %s); the take runs, the void decides' % (
                row['audio_pre_wait_s'], awhy, row['ui_pre']))
        elif row['audio_pre_wait_s'] >= 5:
            decide(out, 'audio pre-check: the mic came back after %.0f s (%s)' % (row['audio_pre_wait_s'], row['ui_pre']))
    bs = busy_sessions()
    if bs:
        bad.append('login session busy: %s' % '; '.join(bs))
    if bad:
        void(row, '; '.join(bad))
        return 'void'
    return ''


# ---- status, reports -----------------------------------------------------------------------------------------------------------
def status(out, head, decision=''):
    if not CS['out']:
        return
    rows = load_rows(out)
    night_rows = [r for r in rows if r.get('night') == CS['night']]
    hb = rd(out + '/heartbeat', '0') or '0'
    try:
        hb_age = int(time.time() - float(hb))
    except ValueError:
        hb_age = -1
    gb_all = sum(float(r.get('gb_written') or 0) for r in rows)
    arms = load_arms(out)
    cur = CS.get('current') or {}
    sm = CS.get('smart_last') or {}
    L = [head, decision or (CS['decisions'][-1].split('] ', 1)[-1] if CS['decisions'] else ''),
         'liveness: heartbeat %d s old; runner pid %d; night %s started %s' % (hb_age, os.getpid(), CS['night'],
                                                                            time.strftime('%H:%M', time.localtime(CS['night_t0'] or time.time()))),
         'take: %s' % (json.dumps(cur) if cur else '-'),
         'progress: %d takes this night (%d in the campaign), %.0f GB this night, %.0f GB in all of a %.0f GB budget' % (
             len(night_rows), len(rows), sum(float(r.get('gb_written') or 0) for r in night_rows), gb_all, BUDGET['gb'] or 0),
         'card: %s %s; free %.0f GB; smart temp %s C, written %s units, critical_warning %s' % (
             CS['serial'], '', card_facts().get('free_b', 0) / 1e9, sm.get('temperature_c'), sm.get('data_units_written'), sm.get('critical_warning')),
         'voids %d, audio faults %d this night%s' % (CS['voids'], CS['audio_faults'], ('; STOP: ' + CS['stop']) if CS['stop'] else ''),
         '', '## Arms', '']
    for m_, a_ in arms.items():
        L.append('- %s: %s' % (m_, ', '.join('%s=%s' % (k, v) for k, v in a_.items() if k != 'cells')
                               + ('; cells ' + ' '.join('%s:%s' % kv for kv in sorted(a_.get('cells', {}).items())) if a_.get('cells') else '')))
    L += ['', '## Last 10 takes', '', '| take | stage | fps | tier | outcome | s | dropped | first drop | gap | boundary | merge s | verdict |',
          '|---|---|---|---|---|---|---|---|---|---|---|---|']
    for r in rows[-10:]:
        L.append('| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |' % (
            r.get('take_id', '')[-28:], r.get('stage'), r.get('fps'), r.get('tier_s'), r.get('outcome'), r.get('seconds'), r.get('dropped'),
            r.get('first_drop_s'), r.get('numbering_gap'), r.get('boundary_drops'), r.get('merge_s'), r.get('verdict')))
    L += ['', '## Decisions (tail)', ''] + ['    ' + d for d in CS['decisions'][-12:]]
    write_atomic(out + '/status.md', '\n'.join(L) + '\n')
    write_atomic(out + '/status.json', json.dumps({'head': head, 'decision': decision, 'night': CS['night'], 'current': cur,
                                                   'take_in_progress': cur.get('take_running', False), 'stop': CS['stop'],
                                                   'heartbeat_age_s': hb_age, 't': time.time()}, indent=1))


def heartbeat(out):
    def beat():
        while CS.get('alive'):
            write_atomic(out + '/heartbeat', '%d\n' % time.time())
            for _ in range(60):
                if not CS.get('alive'):
                    return
                time.sleep(1)
    open(out + '/ACTIVE', 'w').write('pid=%d night=%s started=%s\n' % (os.getpid(), CS['night'], time.strftime('%F %T')))
    CS['alive'] = True
    threading.Thread(target=beat, daemon=True).start()


def load_arms(out):
    p = out + '/arms.json'
    try:
        return json.load(open(p))
    except (OSError, ValueError):
        return {}


def save_arms(out, arms):
    write_atomic(out + '/arms.json', json.dumps(arms, indent=1, sort_keys=True))


def q(sql, out, args=()):
    con = cdb(out)
    try:
        return list(con.execute(sql, args))
    finally:
        con.close()


def report(out, nights):
    """The night's own report (no computer needed): the takes, the fix checks, the merges, the split-need curve."""
    rows = load_rows(out)
    nr = [r for r in rows if r.get('night') in nights]
    L = ['# NVMe campaign report: %s (%s)' % (', '.join(nights), time.strftime('%F %T')), '',
         'Labels: every number here is measured by the runner on this night unless it says derived. Card %s.' % CS['serial'], '',
         '## Takes', '', '| take | stage | arm | fps | tier s | outcome | s | dropped | first drop s | numbering gap | boundary drops | '
         'Core CPU avg | buffer peak % | nvme max C | GB | merge s | verdict |', '|' + '---|' * 17]
    for r in nr:
        L.append('| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |' % (
            r.get('take_id', '')[-24:], r.get('stage'), r.get('cfg_id'), r.get('fps'), r.get('tier_s'), r.get('outcome'), r.get('seconds'),
            r.get('dropped'), r.get('first_drop_s'), r.get('numbering_gap'), r.get('boundary_drops'), r.get('core_cpu_avg'),
            r.get('buffer_peak_pct'), r.get('nvme_c_max'), r.get('gb_written'), r.get('merge_s'), r.get('verdict')))
    # fix checks: 8ec2f1a (part folder on the writer) and e298d4a (index jumps), over the whole campaign so far
    sp = [r for r in rows if str(r.get('split') or '') not in ('', '0', 'None') and r.get('outcome') not in ('void',) and r.get('files')]
    tb = sum(int(_num(r.get('boundaries_crossed')) or 0) for r in sp)
    bd = sum(int(_num(r.get('boundary_drops')) or 0) for r in sp)
    cs_ = sum(int(_num(r.get('copy_slot_drops')) or 0) for r in sp)
    ijs = sum(int(_num(r.get('index_jumps')) or 0) for r in rows if r.get('index_jumps') not in ('', None))
    ng = sum(int(_num(r.get('numbering_gap')) or 0) for r in rows)
    unexpl = [r for r in rows if int(_num(r.get('missing')) or 0) > 0 and int(_num(r.get('numbering_gap')) or 0) == 0]
    bumps = q('SELECT MAX(buf_max_pct - buf_median_pct), AVG(buf_max_pct - buf_median_pct), COUNT(*) FROM boundaries', out)[0]
    frames = sum(int(_num(r.get('files')) or 0) for r in sp)
    L += ['', '## Fix checks (whole campaign so far)', '',
          '- **8ec2f1a, part folder made on the writer**: %d part boundaries crossed in %d split takes (%d frames); %d drops within %d '
          'frames after a boundary; %d copy-slot drops in all. The buffer around a boundary (1 s before to 3 s after) rose at most %s '
          'points above its take median (mean %s, %d boundaries). Expectation if the fix holds: 0 boundary drops, 0 copy-slot drops '
          '(night 2 on the old binary: 3 copy-slot drops at 1 of ~40 boundaries).' % (
              tb, len(sp), frames, bd, BOUNDARY_WINDOW, cs_, None if bumps[0] is None else round(bumps[0], 1),
              None if bumps[1] is None else round(bumps[1], 2), bumps[2] or 0),
          '- **e298d4a, frame index jump logged and counted**: %d index jumps in Core\'s stats over the campaign; %d takes had a numbering '
          'gap explained by them (%d frames, no picture lost); %d takes had missing frames NOT explained by index jumps (each is a drop).' % (
              ijs, sum(1 for r in rows if int(_num(r.get('numbering_gap')) or 0) > 0), ng, len(unexpl))]
    for r in unexpl[:10]:
        L.append('  - %s: missing %s, index_jumps %s, frames %s' % (r.get('take_id'), r.get('missing'), r.get('index_jumps'), r.get('drop_frames')))
    jumps = q('SELECT take_id, frame, skipped, dt_us FROM index_jumps ORDER BY rowid DESC LIMIT 10', out)
    for j in jumps:
        L.append('  - jump in %s at frame %d: skipped %d, dt %d us' % j)
    # merges
    mg = q('SELECT take_id, clip, files_before, parts_before, merge_s, ms_per_file, eta_err_pct, ok FROM merges ORDER BY rowid', out)
    L += ['', '## Merges after the long takes (User, 2026-11-10)', '', '| take | clip | frames | parts | merge s | ms per frame | first ETA error % | intact |',
          '|---|---|---|---|---|---|---|---|']
    for m_ in mg:
        L.append('| %s | %s | %s | %s | %s | %s | %s | %s |' % ((m_[0][-24:],) + tuple(m_[1:])))
    if mg:
        L.append('')
        L.append('Model (T7 night 2, derived): 0.1 ms + 0.32 us x files already in the main folder per frame; 45,001 frames in 342 s.')
    # the split-need curve: flat against split at the same mode and fps
    L += ['', '## When does 4K need the split (flat vs split, same mode and fps)', '',
          'Directory walk share of the frame period, derived: s(t) = 5 x c x fps^2 x t (c in s per entry; flat folder); a split at N '
          'caps it at 5 x c x N x fps. The flat control runs past its first drop (to Core\'s safety stop or the tier length).', '',
          '| mode | fps | variant | take | outcome | s | first drop s | c ns/entry (CPU slope) | Core CPU min 1 -> last | buffer % last 5 min |',
          '|---|---|---|---|---|---|---|---|---|---|']
    long_ = [r for r in rows if int(_num(r.get('tier_s')) or 0) >= 900 and r.get('outcome') not in ('void',)]
    for r in long_:
        b = q('SELECT minute, core_cpu, buf_pct FROM minute_bins WHERE take_id=? ORDER BY minute', out, (r['take_id'],))
        cpu1 = b[1][1] if len(b) > 1 else None
        cpuN = b[-1][1] if b else None
        bl5 = [x[2] for x in b[-5:] if x[2] is not None]
        L.append('| %s | %s | %s | %s | %s | %s | %s | %s | %s -> %s | %s |' % (
            r.get('mode'), r.get('fps'), 'flat' if str(r.get('split')) == '0' else 'split %s' % r.get('split'), r['take_id'][-24:],
            r.get('outcome'), r.get('seconds'), r.get('first_drop_s'), r.get('walk_ns_per_entry'), cpu1, cpuN,
            round(max(bl5), 1) if bl5 else ''))
    preds = []
    for r in long_:
        c_ns = _num(r.get('walk_ns_per_entry'))
        if str(r.get('split')) == '0' and c_ns and c_ns > 0:
            for f in (25, 28, 30, 33, 42):
                preds.append((r.get('mode'), f, round(0.6 / (5 * c_ns * 1e-9 * f * f) / 60, 1)))
    if preds:
        L += ['', 'Flat lifetime t* at the 60 % share, from each flat control\'s measured c (derived; the T7 HDR modes failed nearer '
              '35-40 %, so read these as upper bounds for Clear HDR):', '']
        for p_ in preds:
            L.append('- %s at %d fps: %.1f min' % p_)
    dl = q('SELECT clip, files, parts, cold, budget_s, delete_s FROM deletes ORDER BY rowid DESC LIMIT 10', out)
    if dl:
        L += ['', '## Deletes (media route)', ''] + ['- %s: %d frames, %d parts, %s, budget %.0f s, took %.1f s' % (
            d[0], d[1], d[2], 'cold' if d[3] else 'warm', d[4], d[5]) for d in dl]
    L += ['', '## Decisions', ''] + ['    ' + d for d in CS['decisions']]
    path = out + '/report-%s.md' % '-'.join(nights)
    write_atomic(path, '\n'.join(L) + '\n')
    return path


# ---- the take wrapper of the campaign ------------------------------------------------------------------------------------------
def planned_bytes(out, c, fps, seconds):
    """Model bytes per frame (plan section 3), replaced by the arm's measured mean after its first take."""
    rows = [r for r in load_rows(out) if r.get('mode') == c.key and r.get('comp') == c.comp and str(r.get('log')) == str(c.log)
            and int(_num(r.get('files')) or 0) > 100 and _num(r.get('gb_written'))]
    if rows:
        bpf = sum(float(r['gb_written']) * 1e9 for r in rows) / sum(int(float(r['files'])) for r in rows)
    else:
        bpf = FRAME_MB.get((c.key, c.comp, bool(c.log)), mode_size_mb(c.mode) * (0.48 if c.comp != 'none' else 1.0)) * 1e6
    return bpf * fps * seconds, bpf


def arm_cfg(mkey, comp='none', log_=False, tdn=False, web=True, split=SPLIT_DEFAULT):
    m = [x for x in MODES if x[0] == mkey][0]
    c = Cfg(m, comp, log_, tdn, False, True, web, split)
    return c


def ctake(out, c, fps, tier_s, stage, variant, stop_on_drop=True, merge_on=False):
    """One campaign take: resume-safe (a result already recorded under the same key is returned, not re-recorded), the fill gate,
    the fit limit, the budget, the void/audio repeat rules and the night-stop rules. Returns the row; row['verdict'] is clean, drop,
    audio, void, stop or skip."""
    a = CS['args']
    key0 = '%s|%s|%s|%s|%s' % (stage, c.id, variant, fps, tier_s)
    CS['seq'][key0] += 1
    key = '%s|%d' % (key0, CS['seq'][key0])
    for r in load_rows(out):
        if r.get('ckey') == key and r.get('verdict') in ('clean', 'drop', 'audio', 'skip'):
            return r
    if CS['stop'] or STOP['sig'] or HALT['why']:
        return {'verdict': 'stop'}
    secs = tier_s
    if a.max_seconds:
        secs = min(secs, a.max_seconds)
    need, bpf = planned_bytes(out, c, fps, secs)
    total_b = card_facts().get('free_b', 0) + sum(float(x.get('bytes') or 0) for x in ledger_live(out))
    fit = 0
    # headroom: never let a take run the card past 90 % (2026-11-10: at 96-97 % full the MP600 Mini's writes fell from
    # ~470 to 16-120 MB/s for seconds, twice in four takes that got there, and Core called the medium gone)
    try:
        sv_ = os.statvfs(MEDIA)
        headroom = max(10e9, FILL_HEADROOM * sv_.f_blocks * sv_.f_frsize)
    except OSError:
        headroom = 10e9
    if need * 1.03 + headroom > total_b:
        secs2 = int((total_b - headroom) / (1.03 * bpf * fps))
        decide(out, '%s %s at %s fps: %d s plans %.0f GB, more than the card can hold: fit-limited to %d s' % (stage, c.id, fps, secs, need / 1e9, secs2))
        secs, fit = max(secs2, 0), 1
        need = bpf * fps * secs
    if fit and secs < 30:
        return {'verdict': 'skip', 'ckey': key}
    w = fill_gate(out, need * 1.03 + headroom)
    if w:
        CS['stop'] = w
        return {'verdict': 'stop'}
    if variant != 'warmup':
        cooldown(out)
    for attempt in (1, 2):
        sm = smart_record(out)
        if sm.get('critical_warning'):
            CS['stop'] = 'smart critical_warning=%s' % sm.get('critical_warning')
            return {'verdict': 'stop'}
        if CS['smart0'] and sm.get('data_units_written') and BUDGET['gb'] and \
                (sm['data_units_written'] - CS['smart0']) * 512000 / 1e9 + need / 1e9 > BUDGET['gb']:
            CS['stop'] = 'write budget (smart-log) reached'
            return {'verdict': 'stop'}
        if CS.get('need_warmup') and variant != 'warmup':
            CS['need_warmup'] = False
            warmup(out, c, fps, stage)
        c.merge_on = merge_on
        CS['tier_s'] = tier_s
        CS['current'] = {'stage': stage, 'arm': c.id, 'fps': fps, 'tier_s': secs, 'planned_gb': round(need / 1e9), 'take_running': True,
                         'expected_end': time.strftime('%H:%M', time.localtime(time.time() + secs + 90))}
        status(out, 'TAKE RUNNING until about %s: do not touch the Pi (one cat of this file is fine)' % CS['current']['expected_end'])
        row = run_take(out, c, float(fps), secs, {'gb': 0}, stop_on_drop=stop_on_drop, variant=variant)
        CS['current'] = {}
        payload = row.pop('_payload', None)
        row.update({'night': CS['night'], 'stage': stage, 'ckey': key, 'split': c.split, 'tier_s': tier_s, 'planned_gb': round(need / 1e9, 1),
                    'fit_limited': fit, 'smart_temp_c': (CS['smart_last'] or {}).get('temperature_c'),
                    'smart_duw': (CS['smart_last'] or {}).get('data_units_written'),
                    'takes_since_restart': sum(1 for r in load_rows(out) if r.get('core_pid') == str(CS['core_pid']))})
        o = row.get('outcome', '')
        clean = o.startswith('pass') and int(_num(row.get('dropped')) or 0) == 0
        if o == 'void':
            CS['voids'] += 1
            row['verdict'] = 'void'
        elif o == 'audio_fault':
            CS['audio_faults'] += 1
            CS['arm_audio'][c.id] = CS['arm_audio'].get(c.id, 0) + 1
            row['verdict'] = 'audio'
        elif clean:
            row['verdict'] = 'clean'
        elif o in ('drop', 'buffer_full') or (o.startswith('pass') or o.startswith('ab_')):
            row['verdict'] = 'drop'
        elif o in ('waiting_timeout', 'stop'):
            row['verdict'] = 'stop'
        else:
            row['verdict'] = 'stop'
            CS['stop'] = CS['stop'] or '%s: %s' % (o, row.get('cause_estimate') or row.get('mismatch') or row.get('void_reason'))
        append_row(out, row)
        start_ingest(out, row, payload)
        decide(out, '%s %s %s at %s fps, %s s: %s (%s s, dropped %s, first drop %s, gap %s, boundary %s)%s' % (
            stage, variant, c.id, fps, secs, o, row.get('seconds'), row.get('dropped'), row.get('first_drop_s'), row.get('numbering_gap'),
            row.get('boundary_drops'), (' void: ' + row.get('void_reason', '')) if o == 'void' else ''))
        if HALT['why']:
            CS['stop'] = CS['stop'] or 'watchdog: ' + HALT['why']
        if row['verdict'] == 'void':
            if CS['voids'] >= 2:
                CS['stop'] = CS['stop'] or 'a second void this night (%s)' % row.get('void_reason')
                return row
            continue        # a void is repeated once
        if row['verdict'] == 'audio':
            if CS['audio_faults'] >= 2 and not getattr(a, 'audio_optional', False):
                CS['stop'] = CS['stop'] or 'a second audio fault this night'
                return row
            if CS['arm_audio'].get(c.id, 0) >= 2 and getattr(a, 'audio_optional', False):
                return row  # --audio-optional: this arm faulted twice; the cell gets 'audio', the night goes on
            if tier_s >= 900:
                return row  # a faulted long take is never repeated automatically
            continue        # repeated once; never steps the fps down
        return row
    return row


def warmup(out, c, fps, stage):
    """Plan section 7: an unscored 60-s warm-up after every Core restart, reboot and mode switch."""
    w = Cfg(c.mode, c.comp, c.log, c.tdn, c.lock, c.trim, c.web, c.split)
    ctake(out, w, fps, 60, stage, 'warmup', stop_on_drop=False)


def cell(out, c, fps, stage):
    """S2/S3 rule for one cell: 3-min clean + 5-min clean = carried; two concordant 3-min drops = out; 1-1 = a third 3-min take
    decides; a 5-min drop after a clean 3-min = a third 3-min take, then (clean) a second 5-min take. Returns carried/out/stop and
    the capacity hint of a buffer_full."""
    def t(tier):
        r = ctake(out, c, fps, tier, stage, 'walk')
        return r.get('verdict'), _num(r.get('capacity_fps')) if r.get('outcome') == 'buffer_full' else None
    seq = []
    v1, cap = t(180); seq.append(v1)
    if v1 in ('stop', 'void', 'audio', 'skip'):
        return 'stop' if v1 != 'skip' else 'out', cap
    if v1 == 'clean':
        v5, cap5 = t(300)
        if v5 == 'clean':
            return 'carried', None
        if v5 != 'drop':
            return 'stop', None
        v3, cap = t(180)
        if v3 != 'clean':
            return ('out' if v3 == 'drop' else 'stop'), cap or cap5
        v5b, cap = t(300)
        return ('carried' if v5b == 'clean' else 'out' if v5b == 'drop' else 'stop'), cap
    v2, cap2 = t(180)
    if v2 == 'drop':
        return 'out', cap2 or cap
    if v2 != 'clean':
        return 'stop', None
    v3, cap3 = t(180)
    if v3 != 'clean':
        return ('out' if v3 == 'drop' else 'stop'), cap3
    v5, cap5 = t(300)
    return ('carried' if v5 == 'clean' else 'out' if v5 == 'drop' else 'stop'), cap5


def walk(out, c, edge, top, floor, stage, arms, akey):
    """Step 1 from the edge: up while carried, down while out; best = the highest carried fps."""
    a_ = arms.setdefault(akey, {})
    cells = a_.setdefault('cells', {})
    f, direction, best = int(edge), None, a_.get('best')
    while floor <= f <= top:
        if CS['stop'] or STOP['sig']:
            return best
        v, cap = cell(out, c, f, stage)
        if v == 'stop':
            return best
        cells[str(f)] = v
        save_arms(out, arms)
        if v == 'carried':
            best = max(best or 0, f)
            a_['best'] = best
            save_arms(out, arms)
            if direction == 'down' or f + 1 > top:
                break
            direction, f = 'up', f + 1
        else:
            if direction == 'up':
                break
            direction = 'down'
            nf = f - 1
            if cap and int(cap) < nf:
                decide(out, '%s: buffer_full twice at %d fps, writers carried %.1f fps: next cell %d' % (akey, f, cap, int(cap)))
                nf = int(cap)
            f = nf
    decide(out, '%s: walk ends, best carried fps %s (cells %s)' % (akey, best, ' '.join('%s:%s' % kv for kv in sorted(cells.items()))))
    return best


def mode_top(c):
    apply_cfg(c, 25)
    st = state()
    top = int(float(st.get('fps_take_max') or st.get('fps_max') or 30))
    MODE_MAX[c.key] = top
    return min(top, BRACKET_TOP.get(c.key, top))


def parse_kv(text):
    d = {}
    for part in (text or '').split(','):
        if '=' in part:
            k, v = part.split('=', 1)
            d[k.strip()] = v.strip()
    return d


def meter(out, c, top, stage, arms):
    """SDR12 (plan section 7): a meter take 5-10 % above the record's clean 42 fps (44, then 46, then 50 while the buffer never
    filled); capacity from the buffer's slope; the walk's edge = capacity - 1."""
    for f in (44, 46, 50):
        f = min(f, top)
        r = ctake(out, c, f, 60, stage, 'meter', stop_on_drop=False)
        if r.get('verdict') in ('stop', 'void'):
            return None
        cap, how = _num(r.get('capacity_fps')), r.get('capacity_how')
        decide(out, '%s meter at %d fps: capacity %s (%s), budget %s s of input' % (c.key, f, cap, how, r.get('budget_seconds')))
        if how != 'at least' or f >= top:
            break
    edge = min(top, int(cap) - 1) if cap else 42
    arms.setdefault(c.key, {})['meter_capacity'] = cap
    return edge


def preroll_capacity(c, fps):
    """The manual pre-roll (storage_preroll) at the arm's settings: Core's measured fps, the encoder's capacity reading."""
    apply_cfg(c, fps)
    r = core('storage_preroll', seconds=5)
    if not r.get('ok'):
        return None, str(r.get('error'))
    for _ in range(120):
        time.sleep(2)
        if not state().get('storage_preroll_active'):
            break
    last = state().get('storage_preroll_last') or ''
    m = re.search(r'measured ([\d.]+)', last)
    return (float(m.group(1)) if m else None), last


def s2_night(out, arms):
    a = CS['args']
    start = parse_kv(a.start_fps)
    for mkey in [m for m in a.modes.split(',') if m]:
        if CS['stop'] or STOP['sig']:
            return
        c = arm_cfg(mkey)
        if mkey in CROPS:
            win = (arms.get('4kSDR12') or {}).get('best')
            if not win:
                decide(out, '%s: no SDR12 winner yet: crop skipped' % mkey)
                continue
            top = mode_top(c)
            f = min(top, win + 1)
            warmup(out, c, f, 'S2')
            v, _cap = cell(out, c, f, 'S2')
            arms.setdefault(mkey, {}).update({'cells': {str(f): v}, 'best': f if v == 'carried' else None, 'note': 'confirmation at the SDR12 winner + 1'})
            save_arms(out, arms)
            continue
        top = mode_top(c)
        a_ = arms.setdefault(mkey, {})
        if start.get(mkey) == 'meter':
            warmup(out, c, min(42, top), 'S2')
            edge = a_.get('edge') or meter(out, c, top, 'S2', arms)
            if edge is None:
                return
        else:
            edge = int(float(start.get(mkey) or top))
            if edge > top:
                # Core's ceiling for the mode is below the planned start (2026-11-10: 4K HDR12 read 25 with the IMX283's
                # probe in; the start of 30 came back as 25, a setup_mismatch, and the night stopped): start at the top.
                decide(out, '%s: planned start %d fps is above the mode top %d: starting at %d' % (mkey, edge, top, top))
                edge = top
            warmup(out, c, edge, 'S2')
        a_['edge'], a_['top'] = edge, top
        save_arms(out, arms)
        walk(out, c, edge, top, 25, 'S2', arms, mkey)
        if mkey == '4kHDR16' and not a.no_levers:
            order = parse_kv(a.abba)
            for lever in ('log', 'web'):
                lc = arm_cfg(mkey, log_=(lever == 'log'), web=(lever != 'web'))
                seqs = 'ABBA' if order.get(lever, 'AB') == 'AB' else 'BAAB'
                for i, x in enumerate(seqs):
                    if CS['stop'] or STOP['sig']:
                        return
                    ctake(out, c if x == 'A' else lc, edge, 180, 'S2', 'abba-%s-%s%d' % (lever, x, i + 1))
            ctake(out, arm_cfg(mkey, log_=True), min(30, top), 180, 'S2', 'log30')
            ctake(out, arm_cfg(mkey, tdn=True), 25, 180, 'S2', 'tdn25')
        for spec in [x for x in a.comp_arms.split(',') if x.split(':')[0] == mkey]:
            # plan section 5: SDR12 lossless walks if its pre-roll capacity beats the uncompressed edge; HDR16 lossless + Log only
            # if its pre-roll says > 25 fps (HDR16 lossless alone measured 17.6-18.5 fps: out; Log + lossless made larger files
            # than lossless alone on the SSD, so SDR12 gets no Log + lossless arm)
            f_ = (spec.split(':') + ['', '', ''])[:4]
            comp_, log_, thr = f_[1] or 'lossless_jpeg', f_[2] == 'log', f_[3] or 'edge'
            lc = arm_cfg(mkey, comp=comp_, log_=log_)
            cap, txt = preroll_capacity(lc, top)
            ak = '%s/%s%s' % (mkey, 'lossless' if comp_ == 'lossless_jpeg' else comp_, '+log' if log_ else '')
            arms.setdefault(ak, {})['preroll'] = txt
            limit = edge if thr == 'edge' else float(thr)
            if cap and cap > limit:
                decide(out, '%s: pre-roll %s, above %s: walked' % (ak, txt, limit))
                walk(out, lc, min(top, int(cap) - 1), top, 25, 'S2', arms, ak)
            else:
                decide(out, '%s: pre-roll %s, not above %s: no walk' % (ak, txt, limit))
            save_arms(out, arms)
        ctake(out, c, edge, 180, 'S2', 'ctrl-end')
        save_arms(out, arms)


def long_stage(out, arms, stage, tier, order, src_key, dst_key, steps=2, early_only=False):
    """S4 (15 min) and S5 (30 min): one take per mode at the source fps; a drop steps down 1 fps and repeats the tier (S5: only an
    early drop, before minute 10; a late one is recorded, its signature attributed)."""
    for mkey in order:
        if CS['stop'] or STOP['sig']:
            return
        a_ = arms.get(mkey) or {}
        fps = a_.get(src_key)
        if not fps:
            decide(out, '%s %s: no fps from %s: skipped' % (stage, mkey, src_key))
            continue
        c = arm_cfg(mkey)
        warmup(out, c, fps, stage)
        for i in range(steps + 1):
            r = ctake(out, c, fps, tier, stage, 'long%d' % (tier // 60))
            v = r.get('verdict')
            a_.setdefault(stage, {})[str(fps)] = v if v != 'drop' else 'drop at %s s (%s)' % (r.get('first_drop_s'), r.get('signature') or '')
            if v == 'clean':
                a_[dst_key] = fps
                break
            if v != 'drop':
                break
            early = float(_num(r.get('first_drop_s')) or _num(r.get('seconds')) or 0) < EARLY_S
            if early_only and not early:
                decide(out, '%s %s at %s fps: late drop (%s s, %s): recorded, not repeated' % (stage, mkey, fps, r.get('first_drop_s'), r.get('signature')))
                break
            fps -= 1
            if fps < 25:
                break
            decide(out, '%s %s: drop at %s s: the cell %d fps repeats the tier' % (stage, mkey, r.get('first_drop_s'), fps))
        arms[mkey] = a_
        save_arms(out, arms)


def go_wait(out, stage):
    """A20 / H12: wait for GO-<stage> (one line: unconditional | if all_passed <stage> | if passed <mode> <stage>), up to 8 h."""
    p = out + '/GO-' + stage
    t0 = time.monotonic()
    while time.monotonic() - t0 < 8 * 3600 and not STOP['sig']:
        if os.path.exists(p):
            cond = (open(p).read().strip().splitlines() or [''])[0].strip()
            ok, why = go_condition(out, cond)
            if ok:
                decide(out, 'GO-%s found (%s): %s' % (stage, cond, why))
                return True
            status(out, 'WAITING for GO-%s: its condition "%s" is %s' % (stage, cond, why))
        else:
            status(out, 'WAITING for GO-%s (place %s with one line: unconditional | if all_passed <stage> | if passed <mode> <stage>)' % (stage, p))
        time.sleep(60)
    CS['stop'] = CS['stop'] or 'no GO-%s within 8 h' % stage
    return False


def go_condition(out, cond):
    arms = load_arms(out)
    if cond == 'unconditional':
        return True, 'unconditional'
    m = re.match(r'if all_passed (S\d)$', cond)
    if m:
        st_ = m.group(1)
        dst = {'S4': 's4_pass', 'S5': 's5_pass'}.get(st_)
        modes = [k for k in arms if '/' not in k and k not in CROPS]
        bad = [k for k in modes if not arms[k].get(dst)] if dst else ['?']
        return (not bad), ('true' if not bad else 'false (%s did not pass %s)' % (', '.join(bad), st_))
    m = re.match(r'if passed (\S+) (S\d)$', cond)
    if m:
        dst = {'S4': 's4_pass', 'S5': 's5_pass', 'S2': 'best'}.get(m.group(2))
        ok = bool((arms.get(m.group(1)) or {}).get(dst))
        return ok, 'true' if ok else 'false'
    return False, 'unparseable'


def s6_night(out, arms):
    """Revision item 1 + R5: one FLAT 30-min control per primary mode at its winning fps, after its split take; run past the first
    drop (User 2026-11-10: the flat curve says when 4K needs the split). Optional: the merge-ON check (H25)."""
    a = CS['args']
    order = [m for m in (a.order or a.modes).split(',') if m and m not in CROPS]
    fc = parse_kv(a.flat_control)
    for mkey in order:
        if CS['stop'] or STOP['sig']:
            return
        fps = int(float(fc[mkey])) if mkey in fc else (arms.get(mkey) or {}).get('s5_pass')
        if not fps:
            decide(out, 'S6 %s: no 30-min split pass and no --flat-control: no flat control' % mkey)
            continue
        c = arm_cfg(mkey, split=0)
        warmup(out, c, fps, 'S6')
        r = ctake(out, c, fps, 1800, 'S6', 'flat30', stop_on_drop=False)
        arms.setdefault(mkey, {})['s6_flat'] = '%s at %s fps: %s, first drop %s s, c %s ns/entry' % (
            r.get('verdict'), fps, r.get('outcome'), r.get('first_drop_s'), r.get('walk_ns_per_entry'))
        save_arms(out, arms)
    if a.merge_check:
        mk, f = list(parse_kv(a.merge_check).items())[0]
        c = arm_cfg(mk)
        r = ctake(out, c, int(float(f)), 1800, 'S6', 'merge-src', stop_on_drop=True)
        decide(out, 'S6 merge check: the 30-min split source clip %s is merged automatically after it; the 3-min take during the merge '
               'is not built yet (H25)' % r.get('clip'))


def s1_direct(out, gb, max_s=0, label='direct'):
    """H24: one single-stream direct write (dd oflag=direct bs=16M) with progress and temperature at 1 Hz; the file is a database
    deletable removed right after (the one os.unlink exception of the plan)."""
    path = os.path.join(MEDIA, 's1_%s_%s.bin' % (label, time.strftime('%Y%m%d-%H%M%S')))
    n = int(gb * 1e9 / (16 * 2**20))
    t0 = time.monotonic()
    p = subprocess.Popen(['dd', 'if=/dev/zero', 'of=' + path, 'bs=16M', 'count=%d' % n, 'oflag=direct', 'status=progress'],
                         stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    last = {'b': 0}

    def reader():
        buf = b''
        while True:
            ch = p.stderr.read(64)
            if not ch:
                return
            buf += ch
            for part in re.split(rb'[\r\n]', buf)[:-1]:
                m = re.match(rb'\s*(\d+) bytes', part)
                if m:
                    last['b'] = int(m.group(1))
            buf = re.split(rb'[\r\n]', buf)[-1]
    threading.Thread(target=reader, daemon=True).start()
    rows, prev = [], (0.0, 0)
    while p.poll() is None:
        time.sleep(1)
        el = time.monotonic() - t0
        b = last['b']
        mbps = (b - prev[1]) / max(el - prev[0], 0.1) / 1e6
        prev = (el, b)
        w_ios, _s, w_ticks, _i = dev_stat(DEV['disk'])
        rows.append((label, round(el, 1), b, round(mbps, 1), int(rd(NVME_TEMP, '0')) / 1000 if NVME_TEMP else None, w_ticks, w_ios))
        if max_s and el >= max_s:
            p.terminate()
    el = time.monotonic() - t0
    size = os.path.getsize(path) if os.path.exists(path) else 0
    try:
        os.unlink(path)
    except OSError:
        pass
    con = cdb(out)
    try:
        con.executemany('INSERT INTO s1_samples VALUES (?,?,?,?,?,?,?)', rows)
        con.commit()
    finally:
        con.close()
    rate = size / el / 1e6 if el else 0
    tmax = max([r_[4] for r_ in rows if r_[4]] or [0])
    decide(out, 'S1 %s write: %.1f GB in %.0f s = %.0f MB/s (min 10-s window %.0f MB/s), NVMe max %.0f C; file deleted' % (
        label, size / 1e9, el, rate, min([sum(r_[3] for r_ in rows[i:i + 10]) / 10 for i in range(0, max(len(rows) - 10, 1))] or [0]), tmax))
    return rate


def s1_night(out):
    a = CS['args']
    if not fill_gate(out, 120e9) == '':
        return
    rate = s1_direct(out, 60, 0, 'direct60')
    probe = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'exfat_write_probe.py')
    for extra in ([], ['--workers', '1'], ['--prealloc'], ['--fsync', 'none'], ['--direct'], ['--subdir', '5000']):
        if CS['stop'] or STOP['sig']:
            return
        r = subprocess.run([sys.executable, '-I', probe, '--size-mb', '16.6', '--files', '300', '--out', out + '/s1'] + extra,
                           capture_output=True, text=True)
        tail = [l for l in r.stdout.splitlines() if l.strip()][-1:] or ['(no output)']
        decide(out, 'S1 matrix %s: %s' % (' '.join(extra) or 'default', tail[0][:200]))
    if a.paced:
        for extra in ([], ['--subdir', '5000']):
            r = subprocess.run([sys.executable, '-I', probe, '--size-mb', '1', '--fps', '42', '--seconds', '1800', '--budget-mb', '800',
                                '--out', out + '/s1'] + extra, capture_output=True, text=True)
            tail = [l for l in r.stdout.splitlines() if l.strip()][-1:] or ['(no output)']
            decide(out, 'S1 paced 42 files/s %s: %s' % (' '.join(extra) or 'flat', tail[0][:200]))
    s1_direct(out, 50, 60, 'state60')
    sess = json.load(open(out + '/session.json'))
    sess['s1_direct_mbps'] = round(rate)
    json.dump(sess, open(out + '/session.json', 'w'), indent=1)


def end_night(out):
    """The end of a part: every campaign clip deleted through the media route, one fstrim, the folders the database did not make
    left as they are and listed."""
    for c in ledger_live(out):
        w = delete_clip(out, c)
        if w:
            decide(out, 'END: %s' % w)
    rc, txt = helper('fstrim', 1800)
    decide(out, 'END: fstrim rc=%s %s' % (rc, txt.splitlines()[-1][:160] if txt else ''))
    ff = foreign_folders(out)
    if ff:
        decide(out, 'END: left as found (not the campaign\'s): %s' % ', '.join(ff))


def arms_night(out, arms):
    """Extra arms at a fixed fps (User 2026-11-10: "add HDR16 lossless without log and HDR16 uncompressed + Log at 25 fps"):
    one cell each (3 min + 5 min, the S2 cell rule) at the arm's fps, no walk. --arms mode:comp:log|nolog:fps,..."""
    a = CS['args']
    for spec in [x for x in a.arms.split(',') if x]:
        f_ = (spec.split(':') + ['', '', '', ''])[:4]
        mkey, comp_, log_, fps = f_[0], f_[1] or 'none', f_[2] == 'log', int(f_[3] or 25)
        if CS['stop'] or STOP['sig'] or HALT['why']:
            break
        c = arm_cfg(mkey, comp=comp_, log_=log_)
        ak = '%s/%s%s@%d' % (mkey, 'unc' if comp_ == 'none' else 'lossless', '+log' if log_ else '', fps)
        v, _cap = cell(out, c, fps, 'ARMS')
        arms.setdefault(ak, {})['cells'] = {str(fps): v}
        save_arms(out, arms)
        decide(out, 'ARMS %s at %d fps: %s' % (ak, fps, v))


def smoke_night(out):
    a = CS['args']
    mkey = [m for m in a.modes.split(',') if m][0]
    c = arm_cfg(mkey, split=a.smoke_split)
    fps = int(float(parse_kv(a.start_fps).get(mkey) or 25)) if parse_kv(a.start_fps).get(mkey) != 'meter' else 25
    r = ctake(out, c, fps, MERGE_AFTER_S, 'SMOKE', 'smoke')     # tier 900 so the merge-after path runs; --max-seconds caps it
    decide(out, 'SMOKE: %s, %s frames, buffer peak %s %%, index_jumps %s, boundaries %s, merge %s s ok=%s' % (
        r.get('outcome'), r.get('files'), r.get('buffer_peak_pct'), r.get('index_jumps'), r.get('boundaries_crossed'),
        r.get('merge_s'), r.get('merge_ok')))
    if a.smoke_delete:
        for cl in ledger_live(out):
            if cl['take_id'] == r.get('take_id'):
                decide(out, 'SMOKE: delete of its clip: %s' % (delete_clip(out, cl) or 'ok'))


CROPS = set()


def campaign_main(a, out):
    """--stages N: the nights of the NVMe campaign. Returns the reason the night ended."""
    CAMPAIGN.update({'on': True, 'pre': campaign_pre, 'post': campaign_post})
    CS.update({'out': out, 'night': a.night, 'args': a, 'night_t0': time.time(), 'boot': boot_id(), 'preserve': set(a.preserve.split(',')) - {''}})
    con = cdb(out); con.close()
    heartbeat(out)
    nights = [n for n in a.night.split(',') if n]
    cf = card_facts()
    CS['serial'] = cf.get('serial', '')
    CS['core_pid'] = unit_pid('apertar-core')
    st0 = state()
    CS['tuning'] = st0.get('tuning_file')
    aud = ui_audio()
    CS['audio_expected'] = aud.get('record_audio_enabled') is not False
    found = {k: st0.get(k) for k in ('fps', 'raw_bit_depth', 'cdng_compression', 'cdng_log', 'preview_tdn', 'fps_phase_lock',
                                     'fps_speed_ramp', 'clear_hdr', 'resolution', 'recording_format', 'ladder_enabled',
                                     'frames_per_folder', 'clip_merge_enabled', 'tuning_file')}
    np_ = out + '/night-%s.json' % '-'.join(nights)
    if not os.path.exists(np_):
        json.dump({'found': found, 'audio': aud, 'card': cf, 'boot_id': CS['boot'], 'core_pid': CS['core_pid'],
                   'core_exe_mtime': os.path.getmtime('/proc/%d/exe' % CS['core_pid']) if CS['core_pid'] else None,
                   'core_commit': subprocess.run(['git', '-C', os.path.expanduser('~/ApertarCore'), 'log', '--oneline', '-1'],
                                                 capture_output=True, text=True).stdout.strip(),
                   'cpu_serial': next((l.split(':')[1].strip() for l in open('/proc/cpuinfo') if l.startswith('Serial')), ''),
                   'kernel': os.uname().release, 'cmdline': rd('/proc/cmdline', ''), 'started': time.strftime('%F %T')},
                  open(np_, 'w'), indent=1)
    found = json.load(open(np_))['found']
    sess = json.load(open(out + '/session.json'))
    if a.expect_serial and CS['serial'] != a.expect_serial:
        return 'STOP: card serial %s, expected %s (a T7 or any other medium = stop)' % (CS['serial'], a.expect_serial)
    if 'MP600' not in cf.get('model', '').upper().replace(' ', '') and 'MP600' not in cf.get('model', '').upper():
        return 'STOP: the medium is %r, not a Corsair MP600 Mini' % cf.get('model')
    rel = tuple(int(x) for x in re.findall(r'\d+', os.uname().release)[:2])
    if rel >= (6, 18) and 'nvme.sgl_threshold=0' not in (rd('/proc/cmdline', '') or ''):
        return 'STOP: kernel %s without nvme.sgl_threshold=0 (the 6.18.y NVMe corruption bug)' % os.uname().release
    if not a.no_dropin_check:
        ok_, why_ = fe_depth4(proc_environ(CS['core_pid']) if CS['core_pid'] else {})
        if not ok_:
            return 'WAITING: re-arm: %s' % why_
    sm = smart_record(out)
    if 'smart0' not in sess and sm.get('data_units_written'):
        sess['smart0'] = {'serial': CS['serial'], 'data_units_written': sm['data_units_written'], 't': time.strftime('%F %T')}
        json.dump(sess, open(out + '/session.json', 'w'), indent=1)
    if (sess.get('smart0') or {}).get('serial') == CS['serial']:
        CS['smart0'] = sess['smart0']['data_units_written']
    rc, txt = helper('timers-mask', 120)
    decide(out, 'night %s start: card %s %s fw %s, free %.0f GB; Core pid %s; drop-in %s; timers-mask rc=%s; smart %s' % (
        a.night, cf.get('model'), CS['serial'], cf.get('firmware_rev'), cf.get('free_b', 0) / 1e9, CS['core_pid'],
        'checked' if not a.no_dropin_check else 'NOT checked (--no-dropin-check)', rc,
        'temp %s C' % sm.get('temperature_c') if 'error' not in sm else sm['error'][:80]))
    core('set_mode_ladder', enabled=False)
    core('set_clip_merge', enabled=False)
    core('set_fps_speed_ramp', enabled=False)
    st1 = state()
    decide(out, 'fixed state: ladder %s, merge %s, frames_per_folder %s, speed ramp %s, pre-roll %s (%s)' % (
        st1.get('ladder_enabled'), st1.get('clip_merge_enabled'), st1.get('frames_per_folder'), st1.get('fps_speed_ramp'),
        st1.get('storage_preroll_auto'), st1.get('storage_preroll_last')))
    if CS['audio_expected']:
        decide(out, 'audio baseline: %s -> %s' % (audio_ready(web_state(3.0))[1], audio_forensics(out, 'baseline-' + a.night)))
    arms = load_arms(out)
    CS['need_warmup'] = False
    try:
        for i, n in enumerate(nights):
            if CS['stop'] or STOP['sig'] or HALT['why']:
                break
            if os.path.exists(out + '/DONE-' + n):
                decide(out, 'stage %s already done: skipped' % n)
                continue
            if i and a.idle_between:
                idle(out, a.idle_between, 'drive recovery between runs')
            if n in GO_STAGES and not a.no_go and not go_wait(out, n):
                break
            status(out, 'STAGE %s starting' % n)
            if n == 'SMOKE':
                smoke_night(out)
            elif n == 'S1':
                s1_night(out)
            elif n == 'S2':
                s2_night(out, arms)
            elif n == 'S4':
                long_stage(out, arms, 'S4', 900, [m for m in ('4kHDR16', '4kSDR12', '4kHDR12') if m in a.modes.split(',')],
                           'best', 's4_pass', steps=2)
            elif n == 'S5':
                long_stage(out, arms, 'S5', 1800, [m for m in (a.order or a.modes).split(',') if m and m not in CROPS],
                           's4_pass', 's5_pass', steps=1, early_only=True)
            elif n == 'S6':
                s6_night(out, arms)
            elif n == 'PARTB':
                s1_direct(out, 60, 0, 'knee60')
                long_stage(out, arms, 'PARTB', 1800, ['4kHDR16'], 's5_pass', 'partb_pass_' + CS['serial'], steps=0)
                long_stage(out, arms, 'PARTB', 900, ['4kSDR12'], 's4_pass', 'partb15_pass_' + CS['serial'], steps=0)
            elif n == 'END':
                end_night(out)
            elif n == 'ARMS':
                arms_night(out, arms)
            if not (CS['stop'] or STOP['sig'] or HALT['why']):
                write_atomic(out + '/DONE-' + n, time.strftime('%F %T') + ' done\n')
                decide(out, 'stage %s done' % n)
    finally:
        why = CS['stop'] or (('stopped by ' + STOP['sig']) if STOP['sig'] else '') or HALT['why'] or 'all stages of the night done'
        if CS['stop'] or HALT['why']:
            try:
                k = subprocess.run(['journalctl', '-k', '-b', '-n', '300', '--no-pager', '-o', 'short-iso'], capture_output=True,
                                   text=True, timeout=60).stdout
                write_atomic(out + '/kernel-%s.log' % '-'.join(nights), k)
            except (OSError, subprocess.SubprocessError):
                pass
        restore_night(out, found, nights, why)
        p = report(out, nights)
        CS['alive'] = False
        try:
            os.unlink(out + '/ACTIVE')
        except OSError:
            pass
        status(out, 'NIGHT OVER (%s): safe to read; report %s' % (why, os.path.basename(p)))
    return why


def restore_night(out, found, nights, why):
    """The restore list (plan section 7 with revision item 7), read back and written to restore-<night>.txt; the power-off watcher
    powers the Pi off only when the file says RESTORE OK."""
    ow, oh = (found.get('resolution') or '3840x2160').split('x')
    core('set_record_format', value=found.get('recording_format') or 'cdng')
    for cmd, kw in (('set_clear_hdr', {'enabled': bool(found.get('clear_hdr', True))}),
                    ('set_resolution', {'width': int(ow), 'height': int(oh)}),
                    ('set_raw_bit_depth', {'value': 12 if found.get('raw_bit_depth') == 16 else 16}),
                    ('set_raw_bit_depth', {'value': found.get('raw_bit_depth') or 16}),
                    ('set_cdng_compression', {'value': found.get('cdng_compression') or 'none'}),
                    ('set_cdng_log', {'value': found.get('cdng_log') or 'off'}),
                    ('set_preview_tdn', {'enabled': bool(found.get('preview_tdn'))}),
                    ('set_fps_phase_lock', {'enabled': bool(found.get('fps_phase_lock'))}),
                    ('set_media_trim', {'enabled': True}),
                    ('set_fps_speed_ramp', {'enabled': bool(found.get('fps_speed_ramp'))}),
                    ('set_fps', {'value': float(found.get('fps') or 25)}),
                    ('set_frames_per_folder', {'value': SPLIT_DEFAULT}),
                    ('set_clip_merge', {'enabled': True}),
                    ('set_mode_ladder', {'enabled': bool(found.get('ladder_enabled'))})):
        core(cmd, **kw)
        time.sleep(4 if cmd in ('set_clear_hdr', 'set_resolution', 'set_raw_bit_depth') else 0.3)
    settle()
    st = state()
    want = dict(found)
    want.update({'frames_per_folder': SPLIT_DEFAULT, 'clip_merge_enabled': True})
    bad = ['%s=%s (want %s)' % (k, st.get(k), v) for k, v in want.items() if k != 'tuning_file' and str(st.get(k)) != str(v)]
    rc, txt = helper('timers-unmask', 120)
    lines = ['night %s ended: %s' % (','.join(nights), why), time.strftime('%F %T'),
             'read back: ' + ', '.join('%s=%s' % (k, st.get(k)) for k in want),
             'timers-unmask rc=%s' % rc, 'merge pending %s' % st.get('clip_merge_pending'),
             'RESTORE OK' if not bad else 'RESTORE INCOMPLETE: ' + '; '.join(bad)]
    write_atomic(out + '/restore-%s.txt' % '-'.join(nights), '\n'.join(lines) + '\n')
    decide(out, lines[-1])


def plan_only(a):
    """--dry-run with --stages N (B6 / H21): the planned takes per stage with bytes and minutes, from the model sizes. Runs on the Mac."""
    print('NVMe campaign plan (model sizes, plan section 3; the runner replaces them with each arm\'s measured mean after its first take)')
    card = 990e9
    print('card usable ~%.0f GB; fill gate: free >= planned x 1.03 + 10 GB; split %d frames per folder; merge after tiers >= %d s' % (
        card / 1e9, SPLIT_DEFAULT, MERGE_AFTER_S))
    start = parse_kv(a.start_fps)
    for mkey in [m for m in a.modes.split(',') if m]:
        m = [x for x in MODES if x[0] == mkey][0]
        bpf = FRAME_MB.get((mkey, 'none', False), mode_size_mb(m))
        f = start.get(mkey, '?')
        ff = 44 if f == 'meter' else int(float(f)) if f not in ('?', '') else 25
        print('%-9s %5.2f MB/frame; start %s; at %d fps: 3 min %4.0f GB, 5 min %4.0f GB, 15 min %4.0f GB, 30 min %4.0f GB '
              '(30 min needs %4.0f GB with the margin%s); flat walk share at 30 min (c=%.1f ns) %.0f %%, split %.1f %%' % (
                  mkey, bpf, f, ff, bpf * ff * 180 / 1e3, bpf * ff * 300 / 1e3, bpf * ff * 900 / 1e3, bpf * ff * 1800 / 1e3,
                  bpf * ff * 1800 / 1e3 * 1.03 + 10, '; fit-limited' if bpf * ff * 1800 * 1.03e6 + 10e9 > card else '',
                  WALK_C_PROBE_NS, 100 * 5 * WALK_C_PROBE_NS * 1e-9 * ff * ff * 1800, 100 * 5 * WALK_C_PROBE_NS * 1e-9 * SPLIT_DEFAULT * ff))
    print('nights: %s; GO sentinels before %s; idle %d s between stages; budget %.0f GB' % (
        a.night, ', '.join(x for x in a.night.split(',') if x in GO_STAGES) or '-', a.idle_between, a.budget_gb))


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
    ap.add_argument('--stages', default='1d2rc', help='1 = baseline of every mode, d = configs one factor away, 2 = storage A/B on the best configs, '
                    'r = the rest, c = 10/20/30-min tiers, F = Log follow-up; unattended ladder: m = capacity meter, s = split test, '
                    'L = long take, M = MLV control, k = frames_per_folder A/B, S = soak')
    ap.add_argument('--ab-seconds', type=int, default=120, help='length of one A/B take')
    ap.add_argument('--start-at-mode-max', action='store_true', help='start every walk at the mode\'s own maximum fps, not at what the storage can carry')
    ap.add_argument('--tier1-seconds', type=int, default=SCREEN['s'], help='round 0: length of the take of every config (default 300 = 5 min)')
    ap.add_argument('--tier10-seconds', type=int, default=600)
    ap.add_argument('--tier2-seconds', type=int, default=1200)
    ap.add_argument('--tier3-seconds', type=int, default=0, help='0 = 30 min (or until the drive is full)')
    ap.add_argument('--tier-top', default='3,2,1', help='at most this many survivors per mode try 10, 20 and 30 min')
    ap.add_argument('--no-prune', action='store_true', help='test every config, even those that cannot have an effect')
    ap.add_argument('--ab-variants', default='', help='comma list of A/B variants to run (default: all)')
    ap.add_argument('--ab-reps', type=int, default=3, help='repeats of every A/B variant (interleaved)')
    # unattended ladder (storage-slowdown plan, 2026-11-08): stages m (meter), s (split test), L (long takes), M (MLV control),
    # k (frames_per_folder A/B, skipped when the knob is absent), S (soak)
    ap.add_argument('--budget-gb', type=float, default=0, help='stop before a take that would exceed this many GB written in this run (0 = off)')
    ap.add_argument('--no-gate', action='store_true', help='do not wait for a quiet Pi before each take (smoke tests only)')
    ap.add_argument('--gate-timeout-h', type=float, default=6, help='give up after waiting this long for a quiet Pi')
    ap.add_argument('--fix-budget', action='store_true', help="set [storage] buffer_ram_fraction=0.9, buffer_ram_floor_mb=256 in apertar-hardware.conf for the run (backup restored at the end)")
    ap.add_argument('--meter-seconds', type=int, default=90, help='length of a capacity meter take (stage m)')
    ap.add_argument('--meter-fps', type=float, default=0, help='fps of the meter takes (0 = the mode maximum)')
    ap.add_argument('--meter-log', action='store_true', help='stage m also meters the Log twins')
    ap.add_argument('--split-fps', type=float, default=0, help='fps of the split test, MLV control and knob A/B (0 = 0.95 x the metered capacity)')
    ap.add_argument('--long-comp', default='none', choices=('none', 'lossless_jpeg'),
                    help='compression of the split, long and soak takes (default none = the uncompressed baseline; the meter and MLV ignore it)')
    ap.add_argument('--split-frames', type=int, default=5000, help='frames_per_folder value for the knob A/B (stage k)')
    ap.add_argument('--long-fps', type=float, default=0, help='fps of the long instrumented take (0 = 0.9 x the metered capacity)')
    ap.add_argument('--long-seconds', type=int, default=1800, help='length of the long, split, MLV, knob and soak takes')
    # NVMe 4K campaign (--stages N; plan nvme-campaign/plan.md, revision 2026-11-10)
    ap.add_argument('--night', default='', help='N: the stages of this night, comma list of %s (e.g. S2, or S4,S5, or S6,END)' % ','.join(NIGHT_STAGES))
    ap.add_argument('--start-fps', default='4kHDR16=28,4kSDR12=meter,4kHDR12=30', help='N: walk start per mode (fps or meter)')
    ap.add_argument('--tiers', default='180,300,900,1800', help='N: the tier ladder (fixed by the plan; recorded only)')
    ap.add_argument('--abba', default='log=AB,web=AB', help='N: per lever AB = baseline first (ABBA), BA = lever first (the die roll)')
    ap.add_argument('--comp-arms', default='4kSDR12:lossless_jpeg::edge,4kHDR16:lossless_jpeg:log:25',
                    help='N, S2 (plan section 5): mode:compression:log:threshold; the arm is read with the manual pre-roll and walked only '
                         'if Core measured more than the threshold (edge = the uncompressed edge of the mode)')
    ap.add_argument('--crop-modes', default='', help='N: crop modes key=WxH:bits[:hdr], e.g. 4kC185=3840x2076:12,4kC239=3840x1608:12 (S0 probe)')
    ap.add_argument('--order', default='', help='N: mode order of S5/S6/Part B (the pre-registered die roll); default --modes')
    ap.add_argument('--flat-control', default='', help='N, S6 (R5): mode=fps of the flat 30-min controls; default each mode\'s S5 pass')
    ap.add_argument('--merge-check', default='', help='N, S6 (H25): mode=fps for the merge-on real-use check')
    ap.add_argument('--no-levers', action='store_true', help='N, S2: skip the HDR16 lever block (ABBA Log and WebUI, Log 30, TDN 25)')
    ap.add_argument('--no-go', action='store_true', help='N: do not wait for GO-<stage> sentinels (smoke tests only)')
    ap.add_argument('--no-dropin-check', action='store_true', help='N: do not require FE depth 4 in Core\'s environment (smoke tests only)')
    ap.add_argument('--expect-serial', default='A936B442006AC2', help='N: the campaign card (any other medium = stop)')
    ap.add_argument('--preserve', default='', help='N, SMOKE only: comma list of clip folders on the card that are Patrik\'s (never touched)')
    ap.add_argument('--smoke-split', type=int, default=200, help='N, SMOKE: frames_per_folder of the smoke take (so a 20 s take has parts to merge)')
    ap.add_argument('--smoke-delete', action='store_true', help='N, SMOKE: delete the smoke clip through the media route at the end')
    ap.add_argument('--idle-between', type=int, default=600, help='N: idle seconds between the stages of a night (drive recovery)')
    ap.add_argument('--arms', default='4kHDR16:lossless_jpeg:nolog:25,4kHDR16:none:log:25',
                    help='N, ARMS: extra arms at a fixed fps, mode:comp:log|nolog:fps, one cell each')
    ap.add_argument('--audio-optional', action='store_true', help='a take without audio counts (flagged audio_missing); audio faults never end the night')
    ap.add_argument('--cooldown-every', type=int, default=0, help='N: an idle break of --cooldown-s before the first take after every N s (0 = none)')
    ap.add_argument('--cooldown-s', type=int, default=600, help='N: length of the hourly break, temperatures logged every 10 s')
    ap.add_argument('--cold-wait', type=int, default=600, help='N: idle seconds after a cold delete before the next take (0 = shoot on)')
    ap.add_argument('--audio-ms', type=int, default=0, help='N: the APERTAR_AUDIO_BUFFER_MS the night expects in Core\'s environment (0 = not set)')
    ap.add_argument('--paced', action='store_true', help='N, S1: the paced small-file probe pair (1 MB files at 42 files/s, 30 min, flat and split)')
    a = ap.parse_args()
    for spec in [x for x in a.crop_modes.split(',') if x]:
        k, v = spec.split('=', 1)
        geo, bits = v.split(':')[:2]
        w_, h_ = geo.split('x')
        MODES.append((k, int(w_), int(h_), int(bits), v.endswith(':hdr')))
        CROPS.add(k)
    if 'N' in a.stages:
        if a.preserve and 'SMOKE' not in a.night.split(','):
            sys.exit('--preserve is for the SMOKE night only: Patrik offloads his footage before S0 (plan section 6)')
        bad = [n for n in a.night.split(',') if n and n not in NIGHT_STAGES]
        if not a.night or bad:
            sys.exit('--stages N needs --night with stages from %s (got %r)' % (','.join(NIGHT_STAGES), a.night))
        if not a.modes:
            sys.exit('--stages N needs --modes (A2), e.g. 4kHDR16,4kSDR12,4kHDR12')
    GATE['on'] = not a.no_gate
    GATE['timeout_s'] = int(a.gate_timeout_h * 3600)
    BUDGET['gb'] = a.budget_gb
    out = os.path.expanduser(a.out)
    if a.ab_variants:
        AB_VARIANTS = [v for v in AB_VARIANTS if v[0] in a.ab_variants.split(',')]
    WEB_REMOTE, CLEAR_ALL, DISK_MBPS = a.web_remote, a.clear_all, a.disk_mbps
    SCREEN['s'] = a.tier1_seconds
    MODE_FILTER = [m for m in a.modes.split(',') if m] or None
    os.makedirs(out + '/webui', exist_ok=True)
    cfgs = all_configs()
    inc = included_modes()
    excl = [m for m in MODES if m not in inc]
    n_base = len(inc)
    n_d1 = sum(1 for c in cfgs if c.distance() == 1)
    if a.dry_run and 'N' in a.stages:
        plan_only(a)
        return
    if a.dry_run:
        for m in MODES:
            print('%-8s %5.2f MB/frame  %4.0f MB/s at %d fps (%3.0f%% of %.0f)  storage cap %d fps  %s' % (
                m[0], mode_size_mb(m), mode_size_mb(m) * FPS_FLOOR, FPS_FLOOR, 100 * mode_size_mb(m) * FPS_FLOOR / DISK_MBPS,
                DISK_MBPS, mode_cap_fps(m), 'RUN' if m in inc else 'excluded: storage too slow'))
        print('upper bounds, before pruning - stage 1: %d baseline configs; d: %d single-factor configs; 2: storage A/B only where the '
              'baseline hit the storage limit; r: %d combinations (only of factors that helped); c: 10, 20 then 30 min for the survivors only (round 0 is 5 min)' % (
                  n_base, n_d1, len(cfgs) - n_base - n_d1))
        print('A/B variants:', ', '.join(v for v, _ in AB_VARIANTS))
        return
    if os.path.exists(out + '/DONE') and 'N' not in a.stages:
        sys.exit('this campaign already ended (%s): remove %s/DONE to run it again' % (open(out + '/DONE').read().strip()[:200], out))
    inst = open(out + '/.instance.lock', 'a+')      # one runner per --out: the crontab resume must not start a second one
    try:
        fcntl.flock(inst, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        inst.seek(0)
        sys.exit('another runner already uses %s (%s): not starting a second one' % (out, inst.read().strip()[:80] or 'pid unknown'))
    inst.seek(0); inst.truncate(); inst.write('pid=%d started=%s\n' % (os.getpid(), time.strftime('%F %T'))); inst.flush()
    WATCH['since'] = time.time()                     # the watchdog's first window starts here, not in the boot messages
    # After a reboot (the crontab resume) Core and the mount come up late: wait up to 15 min for both.
    t_wait = time.monotonic()
    st0 = state()
    while not (st0 and os.path.ismount(MEDIA)):
        if time.monotonic() - t_wait > 900:
            sys.exit('after 15 min: Core %s, %s %s' % ('answers' if st0 else 'not answering on ' + SOCK, MEDIA,
                                                       'mounted' if os.path.ismount(MEDIA) else 'not mounted'))
        if not SAID.get('startwait'):
            SAID['startwait'] = True
            log(out, 'waiting for Core (%s) and the mount (%s)' % ('up' if st0 else 'down', 'up' if os.path.ismount(MEDIA) else 'down'))
        time.sleep(10)
        st0 = state()
    resolve_disk()
    parent = DEV.get('parent') or KT['dev']
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
                                                               'preview_tdn', 'fps_phase_lock', 'fps_speed_ramp', 'clear_hdr', 'resolution',
                                                               'recording_format')},
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
    own_clips_load(out)
    BUDGET['used'] = sum(float(r.get('gb_written') or 0) for r in load_rows(out))
    if BUDGET['gb']:
        log(out, 'write budget %.0f GB, %.0f GB used so far in this run' % (BUDGET['gb'], BUDGET['used']))
    log(out, 'preserving %d pre-existing clip folder(s)%s; %d clip folder(s) of this run on the drive' % (
        len(PRESERVE), ' (--clear-all: they WILL be deleted)' if CLEAR_ALL else '', len(OWN['clips'] & clip_dirs())))
    log(out, 'campaign start: modes %s; excluded (storage too slow at %d fps): %s; %d configs; drive %.0f MB/s; out=%s' % (
        [m[0] for m in inc], FPS_FLOOR, [m[0] for m in excl], len(cfgs), DISK_MBPS, out))
    core('set_fps_speed_ramp', enabled=False)
    aud = ui_audio()
    sess = json.load(open(out + '/session.json'))
    sess.setdefault('audio_original', aud)
    json.dump(sess, open(out + '/session.json', 'w'), indent=1)
    stop = {'now': False, 'why': ''}

    def on_signal(signum, _frame):
        name = {signal.SIGTERM: 'SIGTERM', signal.SIGINT: 'SIGINT'}.get(signum, str(signum))
        if STOP['sig'] and signum == signal.SIGINT:
            raise KeyboardInterrupt          # a second Ctrl-C: leave at once (the finally block still restores the settings)
        STOP['sig'] = name
        stop['now'] = True
    signal.signal(signal.SIGTERM, on_signal)
    signal.signal(signal.SIGINT, on_signal)
    written = {'gb': 0}
    ext_stops = {}
    counter = {'n': 0}

    def take(c, fps, **kw):
        ms = kw.pop('max_seconds', a.max_seconds)
        if a.max_seconds and ms:
            ms = min(ms, a.max_seconds)      # --max-seconds caps every stage's takes (smoke tests)
        row = run_take(out, c, fps, ms, written, **kw)
        payload = row.pop('_payload', None)
        append_row(out, row)
        start_ingest(out, row, payload)     # runs while the next take is set up
        if row.get('media_class'):
            KT['class'] = row['media_class']
        o = row.get('outcome', '')
        if o in ('record_start_failed', 'setup_mismatch', 'media_not_mounted', 'gate_timeout', 'needs_human', 'watchdog', 'budget_exceeded'):
            stop['why'] = '%s: %s' % (o, row.get('cause_estimate') or row.get('mismatch'))
            log(out, 'setup problem (%s): %s - campaign needs a human' % (o, row.get('cause_estimate') or row.get('mismatch')))
            stop['now'] = True
        elif o == 'stopped_by_signal':
            stop['now'] = True
        elif o == 'before_cmd_refused':
            log(out, 'Core refused a stage command (%s): the rest of this stage is skipped' % row.get('cause_estimate'))
        if HALT['why']:
            stop['why'] = stop['why'] or 'watchdog: ' + HALT['why']
            log(out, 'watchdog: %s - campaign stopped, needs a human' % HALT['why'])
            stop['now'] = True
        return row

    def pre_take():
        """Before a camera mode switch or a clip clean-up: the Pi must be quiet (another session's take must not be disturbed),
        then this run's leftover clips go. False = stop the campaign (the reason is logged)."""
        if stop['now']:
            return False
        code = wait_for_quiet(out, need_free_gib=0)
        if code:
            stop['why'] = {'needs_human': 'needs_human: see the gate lines', 'gate_timeout': 'gate_timeout', 'signal': ''}[code]
            stop['now'] = True
            return False
        clear_media(out)
        return True

    def baseline_of(m):
        return [x for x in cfgs if x.mode == m][0]

    def long_cfg_of(m):
        """The config of the long, split and soak takes: the mode's baseline, or with --long-comp its baseline in that
        compression (everything else as the baseline). The meter keeps baseline_of."""
        b = baseline_of(m)
        if a.long_comp == b.comp:
            return b
        sel = [x for x in cfgs if x.mode == m and x.comp == a.long_comp and (x.log, x.tdn, x.lock, x.trim, x.web) == (b.log, b.tdn, b.lock, b.trim, b.web)]
        return sel[0] if sel else b

    def mode_max_fps(c):
        """The fps the mode itself allows (Core's fps_take_max after the mode is applied); a camera switch, so only under the gate."""
        if c.key in MODE_MAX:
            return float(MODE_MAX[c.key])
        apply_cfg(c, 25)
        fmax = float(state().get('fps_take_max') or state().get('fps_max') or 30)
        MODE_MAX[c.key] = int(fmax)
        return fmax

    def metered_capacity(m, comp='none'):
        """The metered capacity (fps) of a mode's variant from stage m rows: a buffer-slope fit first, then 'at least' (the
        buffer never filled at that fps), then the estimate from Core's stats line; None without a meter row."""
        rows = [r for r in load_rows(out) if r['mode'] == m[0] and r.get('variant') == 'meter' and r.get('comp') == comp
                and r.get('capacity_fps') not in ('', None) and r.get('log') in ('False', '0', False)]
        for how in ('fit', 'at least', 'stats'):
            sel = [float(r['capacity_fps']) for r in rows if r.get('capacity_how') == how]
            if sel:
                return max(sel)
        return None

    def pick_fps(m, given, factor, comp='none'):
        """The fps of a long take: the given one, else factor x the metered capacity; None (skip the mode) when that falls
        below the 25 fps floor (a 4K mode the drive carries at 12 fps is metered, never run for 30 min at 25)."""
        if given:
            return float(given)
        cap = metered_capacity(m, comp)
        if cap is None:
            log(out, '%s: no metered capacity (run stage m first or give the fps): skipped' % m[0])
            return None
        f = int(cap * factor)
        if f < FPS_FLOOR:
            if not SAID.get(('floor', m[0], factor)):
                SAID[('floor', m[0], factor)] = True
                log(out, '%s: metered capacity %.1f fps x %.2f = %d fps is below the %d fps floor: metered only, no long takes' % (
                    m[0], cap, factor, f, FPS_FLOOR))
            return None
        return float(f)

    def meter_stage():
        """One short take per mode and variant, no stop at the first drop: the buffer's slope is the writers' deficit, so
        capacity = fps - slope (capacity_fps, how 'fit'). The fps is the mode's maximum or 1.25 x the storage cap, whichever is
        lower, so the buffer lasts long enough to fit; when it still fills within seconds the capacity comes from Core's stats
        line ('stats') and a second meter take runs at 1.3 x that estimate. Replaces the fps ladder."""
        for m in inc:
            if stop['now']: return
            base = baseline_of(m)
            variants = [Cfg(m, 'none', False, base.tdn, base.lock, base.trim, base.web),
                        Cfg(m, 'lossless_jpeg', False, base.tdn, base.lock, base.trim, base.web)]
            if a.meter_log:
                variants += [Cfg(m, 'none', True, base.tdn, base.lock, base.trim, base.web),
                             Cfg(m, 'lossless_jpeg', True, base.tdn, base.lock, base.trim, base.web)]
            for c in variants:
                if stop['now']: return
                done = [r for r in load_rows(out) if r['cfg_id'] == c.id and r.get('variant') == 'meter' and is_result(r.get('outcome'))]
                if any(r.get('capacity_how') in ('fit', 'at least') for r in done) or len(done) >= 2:
                    continue
                if not pre_take(): return
                if not done:
                    fps = a.meter_fps or min(mode_max_fps(c), float(max(5, int(1.25 * mode_cap_fps(m)))))
                else:
                    est = _num(done[0].get('capacity_fps'))
                    if not est or est * 1.3 >= float(done[0]['fps']) - 1:
                        continue
                    fps = float(max(5, int(est * 1.3)))
                row = take(c, float(fps), max_seconds=a.meter_seconds, stop_on_drop=False, variant='meter')
                log(out, 'meter %s at %s fps: capacity %s fps (%s), drain %s MB/s, %s' % (
                    c.id, fps, row.get('capacity_fps'), row.get('capacity_how'), row.get('drain_mbps'), row.get('outcome')))
                est = _num(row.get('capacity_fps'))
                if not stop['now'] and row.get('capacity_how') == 'stats' and est and est * 1.3 < fps - 1:
                    fps2 = float(max(5, int(est * 1.3)))
                    if not pre_take(): return
                    row = take(c, fps2, max_seconds=a.meter_seconds, stop_on_drop=False, variant='meter')
                    log(out, 'meter %s again at %s fps: capacity %s fps (%s), drain %s MB/s, %s' % (
                        c.id, fps2, row.get('capacity_fps'), row.get('capacity_how'), row.get('drain_mbps'), row.get('outcome')))
        L = ['# Capacity meter', '', '| mode | comp | log | fps run | capacity fps | how | drain MB/s | outcome | s |', '|---|---|---|---|---|---|---|---|---|']
        for r in load_rows(out):
            if r.get('variant') == 'meter' and r.get('fps'):
                L.append('| %s | %s | %s | %s | %s | %s | %s | %s | %s |' % (r['mode'], r['comp'], r['log'], r['fps'], r.get('capacity_fps'),
                                                                        r.get('capacity_how'), r.get('drain_mbps'), r['outcome'], r['seconds']))
        open(out + '/capacity.md', 'w').write('\n'.join(L) + '\n')

    def long_runs(label, fmt='cdng', before=(), fps_arg=0, factor=0.95, repeats=1, seconds=None, expect=None):
        """One (or more) long takes per mode at the chosen fps, no stop at the first drop (Core's safety stop ends a failing take).
        A take that ended in a gate, watchdog, budget or setup stop is not a result and runs again on a resume."""
        for m in inc:
            if stop['now']: return
            c = long_cfg_of(m)
            fps = pick_fps(m, fps_arg, factor, c.comp)
            if fps is None:
                continue
            for i in range(repeats):
                if stop['now']: return
                lab = label if repeats == 1 else '%s%d' % (label, i + 1)
                if any(r['cfg_id'] == c.id and r.get('variant') == lab and float(r.get('fps') or 0) == fps and r.get('format', 'cdng') == fmt
                       and is_result(r.get('outcome')) for r in load_rows(out) if r.get('fps')):
                    continue
                if not pre_take(): return
                row = take(c, fps, max_seconds=(seconds or a.long_seconds), stop_on_drop=False, variant=lab, fmt=fmt, before_cmds=before,
                           expect=expect)
                log(out, '%s %s at %s fps: %s after %ss, capacity %s, files %s' % (lab, c.id, fps, row.get('outcome'), row.get('seconds'),
                                                                                 row.get('capacity_fps'), row.get('files')))
                if row.get('outcome') == 'before_cmd_refused':
                    return

    def split_stage():
        """3 x 10 min back to back against 1 x 30 min at the same fps: a per-folder cost passes the short takes and fails the
        long one; a drive or memory state carried across takes fails both (plan section 4.3, item 1)."""
        long_runs('split30', fps_arg=a.split_fps, factor=0.95, seconds=a.long_seconds)
        long_runs('split10', fps_arg=a.split_fps, factor=0.95, repeats=3, seconds=a.long_seconds // 3)

    def restore_knobs():
        """Put frames_per_folder and the merge worker back as they were before stage k (kept in knob_orig.json, so a resume
        after a power cut still knows the originals)."""
        kp = out + '/knob_orig.json'
        if not os.path.exists(kp):
            return
        o = json.load(open(kp))
        r1 = core('set_frames_per_folder', value=o.get('frames_per_folder') if o.get('frames_per_folder') is not None else 0)
        r2 = core('set_clip_merge', enabled=bool(o['clip_merge_enabled'])) if o.get('clip_merge_enabled') is not None else {'ok': True}
        if r1.get('ok') and r2.get('ok'):
            os.unlink(kp)
            log(out, 'restored frames_per_folder=%s and clip_merge=%s' % (o.get('frames_per_folder'), o.get('clip_merge_enabled')))
        else:
            log(out, 'WARNING: could not restore the knobs (%s %s); knob_orig.json kept' % (r1.get('error'), r2.get('error')))

    def knob_stage():
        """frames_per_folder on and off at the split fps, the merge worker off for the run; skipped when Core lacks the knob.
        Core persists both through its store ([storage] in apertar-hardware.conf), so the originals are kept in knob_orig.json
        and put back at the end, also on a resume."""
        st0 = state()
        if 'frames_per_folder' not in st0:
            log(out, 'stage k: Core has no frames_per_folder knob (clip-split branch not running): skipped')
            return
        kp = out + '/knob_orig.json'
        if not os.path.exists(kp):
            json.dump({'frames_per_folder': st0.get('frames_per_folder'), 'clip_merge_enabled': st0.get('clip_merge_enabled')}, open(kp, 'w'))
        merge_off = (('set_clip_merge', {'enabled': False}),) if st0.get('clip_merge_enabled') is not None else ()
        try:
            long_runs('knob%d' % a.split_frames, before=merge_off + (('set_frames_per_folder', {'value': a.split_frames}),),
                      fps_arg=a.split_fps, factor=0.95, expect={'frames_per_folder': a.split_frames})
            long_runs('knob0', before=merge_off + (('set_frames_per_folder', {'value': 0}),), fps_arg=a.split_fps, factor=0.95,
                      expect={'frames_per_folder': 0})
        finally:
            restore_knobs()

    def soak_stage():
        """The best clean 30-min result per mode (split30, long30 or a knob arm; a take with no stop at the first drop ends in
        ab_clean), twice (repeatability and drift); without one, 0.85 x the metered capacity."""
        for m in inc:
            if stop['now']: return
            passes = [float(r['fps']) for r in load_rows(out)
                      if r['mode'] == m[0] and r.get('fps') and r.get('format', 'cdng') == 'cdng' and is_clean(r.get('outcome'))
                      and (r.get('variant', '') in ('split30', 'long30') or r.get('variant', '').startswith('knob'))]
            fps = max(passes) if passes else pick_fps(m, 0, 0.85, long_cfg_of(m).comp)
            if fps is None:
                continue
            c = long_cfg_of(m)
            for i in (1, 2):
                if stop['now']: return
                if any(r['cfg_id'] == c.id and r.get('variant') == 'soak%d' % i and is_result(r.get('outcome')) for r in load_rows(out)):
                    continue
                if not pre_take(): return
                row = take(c, float(fps), max_seconds=a.long_seconds, stop_on_drop=False, variant='soak%d' % i)
                log(out, 'soak%d %s at %s fps: %s after %ss' % (i, c.id, fps, row.get('outcome'), row.get('seconds')))

    def walk_config(c, force=False, start=None):
        """Step fps down from the mode's storage cap until a take passes (30 min or drive full)."""
        rows = [r for r in load_rows(out) if r['cfg_id'] == c.id and not r.get('variant')]
        if force:
            rows = [r for r in rows if r['outcome'] != 'pruned']
        if any(r['outcome'].startswith('pass') or r['outcome'] in ('skipped_unavailable', 'exhausted', 'pruned') for r in rows):
            return
        mode_cfgs = [x for x in cfgs if x.mode == c.mode]
        why = prune_reason(c, load_rows(out), mode_cfgs) if not (a.no_prune or force) else None
        if why:
            log(out, '-- pruned %s: %s' % (c.id, why))
            append_row(out, {'cfg_id': c.id, 'mode': c.key, 'bits': c.bits, 'comp': c.comp, 'log': c.log, 'tdn': c.tdn,
                             'lock': c.lock, 'trim': c.trim, 'web': c.web, 'outcome': 'pruned', 'cause_estimate': why,
                             'started': time.strftime('%F %T')})
            return
        if a.only and counter['n'] >= a.only:
            stop['now'] = True
            return
        counter['n'] += 1
        if not pre_take():
            return
        apply_cfg(c, 25)
        fmax = float(state().get('fps_take_max') or state().get('fps_max') or 30)
        MODE_MAX[c.key] = int(fmax)
        # User, 2026-11-07: options that cannot survive 5 min even in theory are ruled out; only 25 fps and above count.
        # Theory = the drive's measured sustained speed; --start-at-mode-max tries the mode's own maximum anyway.
        fps = float(int(fmax if a.start_at_mode_max else min(fmax, mode_cap_fps(c.mode))))
        if start: fps = min(fps, float(start))
        if a.fps_start: fps = a.fps_start
        rows = [r for r in rows if r['outcome'] != 'stopped_externally']
        if rows:
            fps = min(fps, min(float(r['fps']) for r in rows) - 1)
        fr = None if (a.no_prune or force or c.comp != 'none' or c.log) else storage_frontier(load_rows(out), mode_size_mb(c.mode))
        if fr is not None:
            allowed = int(fr * DISK_MARGIN / mode_size_mb(c.mode) - 1e-9)     # rates below the frontier only
            if allowed < fps:
                log(out, '-- %s: starting at %d fps instead of %d (the drive already filled its buffer at %.0f MB/s)' % (
                    c.id, allowed, fps, fr))
                fps = float(allowed)
            if fps < FPS_FLOOR:
                append_row(out, {'cfg_id': c.id, 'mode': c.key, 'bits': c.bits, 'comp': c.comp, 'log': c.log, 'tdn': c.tdn,
                                 'lock': c.lock, 'trim': c.trim, 'web': c.web, 'outcome': 'pruned',
                                 'cause_estimate': 'data rate at %d fps (%.0f MB/s) is at or above %.0f MB/s, where the drive '
                                                   'already filled its RAM buffer' % (FPS_FLOOR, mode_size_mb(c.mode) * FPS_FLOOR, fr),
                                 'started': time.strftime('%F %T')})
                log(out, '-- pruned %s: the drive cannot carry this data rate (frontier %.0f MB/s)' % (c.id, fr))
                return
        ruled_out = False
        log(out, '== config %s: stepping down from %s fps (mode max %.0f; the storage should carry %d)' % (c.id, fps, fmax, mode_cap_fps(c.mode)))
        while fps >= FPS_FLOOR and not stop['now']:
            if not pre_take(): break
            if os.statvfs(MEDIA).f_bavail * os.statvfs(MEDIA).f_frsize < 20 * 2**30:
                log(out, 'drive still nearly full after clearing the clips: stopping')
                stop['now'] = True; break
            row = take(c, fps, max_seconds=(a.max_seconds or SCREEN['s']))
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
            if o == 'buffer_full' and not a.no_prune and not force:
                jump = smart_next_fps(row, fps)
                if jump and jump[1] < FPS_FLOOR * 0.8:
                    est = jump[1]
                    why = ('ruled out in theory: in that take the drive wrote the equivalent of %.1f fps, well below the %d fps '
                           'floor, so no take of this config can survive 5 min' % (est, FPS_FLOOR))
                    log(out, '-- %s %s' % (c.id, why))
                    append_row(out, {'cfg_id': c.id, 'mode': c.key, 'bits': c.bits, 'comp': c.comp, 'log': c.log, 'tdn': c.tdn,
                                     'lock': c.lock, 'trim': c.trim, 'web': c.web, 'outcome': 'pruned', 'cause_estimate': why,
                                     'started': time.strftime('%F %T')})
                    ruled_out = True
                    break
                if jump:
                    nxt, est = jump
                    if nxt < fps - 1:
                        log(out, '-- smart step: the drive wrote the equivalent of %.1f fps in that take; trying %d fps next (instead of %d)' % (
                            est, nxt, fps - 1))
                    fps = float(nxt)
                    continue
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
            lim = limiter_of([r for r in rows_all if r['cfg_id'] == mine[0].id], mode_top_fps(m))
            if 'storage' not in lim and not a.no_prune:
                log(out, 'A/B %s: skipped, the baseline was not limited by the storage (%s)' % (
                    m[0], '/'.join(sorted(lim)) or 'clean at the highest fps'))
                continue
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
                cap = mode_top_fps(m)
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
                        if not pre_take(): return
                        note = set_variant(out, vname, settings)
                        for attempt in range(3):      # a take stopped by someone else is not a result: run it again
                            row = take(c, ab_fps, max_seconds=a.ab_seconds, stop_on_drop=False, variant=vname, tune_note=note)
                            if stop['now'] or not (row.get('outcome') == 'stopped_externally' and dropped_none(row)):
                                break
                            log(out, 'A/B take stopped by someone else (%ss): repeating (%d/2)' % (row.get('seconds'), attempt + 1))
                            if not pre_take(): return
                        log(out, 'A/B %s rep %d %s: %s dropped=%s' % (c.id, rep + 1, vname, row.get('outcome'), row.get('dropped')))
                set_variant(out, 'base', {})

    def bracket(c, f0, secs, label, rows_all):
        prior = [(float(r['fps']), r['outcome']) for r in rows_all
                 if r['cfg_id'] == c.id and r.get('variant') == label and r['outcome'] not in ('stopped_externally', 'pruned')]
        ext = {'n': 0}

        def attempt(f):
            while True:
                if not pre_take():
                    return None
                row = take(c, float(f), max_seconds=secs, variant=label)
                if stop['now']:
                    return None
                if row.get('outcome') == 'stopped_externally' and dropped_none(row) and ext['n'] < 2:
                    ext['n'] += 1
                    continue
                return row.get('outcome', '').startswith('pass')
        lo, hi = bracket_search(f0, prior, attempt)
        if lo is None:
            log(out, '-- %s %s: no pass down to %d fps at this length' % (label, c.id, FPS_FLOOR))
        else:
            log(out, '== %s %s: clean at %d fps%s' % (label, c.id, lo, '' if hi is None else ' (fails at %d)' % hi))

    def follow_log_stage():
        """Log wherever a smaller file can matter (User, 2026-11-07: "try it on all relevant settings, where a 25 % decrease in
        file size might actually make a difference", and "log also applies to SDR modes"). Core decides per mode whether Log
        applies (16 -> 12 bit, 12 -> 10 bit); where it says no, a 4 s probe take keeps Core's reason.
        Parents = every config of the mode that hit the storage limit (a take ended in buffer full or a full queue) plus the
        winner (highest fps that passed 30 min, simplest on a tie). Each parent gets a Log twin (same switches, Log on): a 5 min
        walk starting at 1.4 x the parent's 5 min fps (25 % fewer bytes cannot give more than ~1.33 x), then 10, 20, 30 min if
        the twin gained at 5 min or is the winner's twin. With no parent at all (a mode ruled out before it ran): lossless,
        lossless + Log and Log."""
        rows_all = load_rows(out)
        bad = ('exhausted', 'pruned', 'stopped_externally', 'skipped_unavailable')
        first = {'4kHDR12': 0, '4kSDR10': 1, '4kSDR12': 2}      # the 4K question (can Log make 4K work?) goes first
        for m in sorted(inc, key=lambda x: first.get(x[0], 3)):
            mine = [c for c in cfgs if c.mode == m]
            by_id = {c.id: c for c in mine}
            rows_m = [r for r in rows_all if r['mode'] == m[0] and not r.get('variant')]
            best30 = {}
            for r in rows_all:
                if r['mode'] == m[0] and r.get('variant') == 'tier30' and r['outcome'].startswith('pass'):
                    best30[r['cfg_id']] = max(best30.get(r['cfg_id'], 0), float(r['fps']))
            win = by_id[sorted(best30, key=lambda k: (-best30[k], len(factors_of(by_id[k])), k))[0]] if best30 else None
            f5 = {}
            for c in mine:
                if c.log:
                    continue
                rs = [r for r in rows_m if r['cfg_id'] == c.id and r['outcome'] not in bad]
                if not rs:
                    continue
                storage = any(r['outcome'] == 'buffer_full' or 'queue-full' in (r.get('drop_kinds') or '') for r in rows_all
                              if r['cfg_id'] == c.id)
                if storage or c is win:
                    ps = [float(r['fps']) for r in rs if r['outcome'].startswith('pass')]
                    f5[c.id] = max(ps) if ps else 0.0
            parents = sorted(f5, key=lambda k: (by_id[k] is not win, -f5[k], k))

            def twin(p):
                for x in mine:
                    if (x.comp, x.log, x.tdn, x.lock, x.trim, x.web) == (p.comp, True, p.tdn, p.lock, p.trim, p.web):
                        return x
            todo = [(by_id[k], twin(by_id[k])) for k in parents]
            if not todo:
                base0 = mine[0]
                for comp, lg in (('lossless_jpeg', False), ('lossless_jpeg', True), ('none', True)):
                    for x in mine:
                        if (x.comp, x.log, x.tdn, x.lock, x.trim, x.web) == (comp, lg, base0.tdn, base0.lock, base0.trim, base0.web):
                            todo.append((None, x))
            log(out, '== follow-up Log %s: winner %s; %d Log twin(s): %s' % (
                m[0], win.id if win else 'none', len(todo), [t.id.split('_', 1)[1][:24] for _, t in todo]))
            for par, c in todo:
                if stop['now']: return
                pf5 = f5.get(par.id, 0.0) if par else 0.0
                start = min(int(pf5 * 1.4) + 1, 200) if pf5 else None
                walk_config(c, force=True, start=start)
                prow = [r for r in load_rows(out) if r['cfg_id'] == c.id and not r.get('variant') and r['outcome'].startswith('pass')]
                if not prow:
                    log(out, '-- follow-up Log %s: no pass in the 5-minute walk, stops here' % c.id)
                    continue
                f0 = max(float(r['fps']) for r in prow)
                if par is not None and par is not win and f0 <= pf5:
                    log(out, '-- follow-up Log %s: %d fps, no gain over its parent (%d fps) at 5 min: no long ladder' % (c.id, f0, pf5))
                    continue
                for label, secs in (('logt10', a.tier10_seconds), ('logt20', a.tier2_seconds), ('logt30', a.tier3_seconds)):
                    if stop['now']: return
                    bracket(c, f0, secs, label, load_rows(out))
                    ps = [float(r['fps']) for r in load_rows(out)
                          if r['cfg_id'] == c.id and r.get('variant') == label and r['outcome'].startswith('pass')]
                    if not ps:
                        break
                    f0 = max(ps)

    def tier_stage():
        """Successive elimination by duration (User, 2026-11-07). Round 0 is the walk above (5 min per take, every config
        that survives pruning). Then 10, 20 and 30 min (30 = until the drive is full): per mode only the configs at the
        best clean fps of the previous round try the next, longer take. A switch that makes no difference (a simpler
        config reached the same fps) is dropped: only the config with the fewest switches stands in for the tie. A
        config that fails a round steps down one fps at that round's length."""
        tops = [int(x) for x in a.tier_top.split(',')]
        rounds = [('tier10', a.tier10_seconds, tops[0], ''), ('tier20', a.tier2_seconds, tops[1], 'tier10'),
                  ('tier30', a.tier3_seconds, tops[2], 'tier20')]
        for label, secs, topn, prev in rounds:
            for m in inc:
                if stop['now']: return
                rows_all = load_rows(out)
                mine = [c for c in cfgs if c.mode == m]
                cand = []
                for c in mine:
                    if prev:
                        ps = [r for r in rows_all if r['cfg_id'] == c.id and r.get('variant') == prev and r['outcome'].startswith('pass')]
                        if ps:
                            cand.append((max(float(r['fps']) for r in ps), c))
                    else:
                        sc = config_score([r for r in rows_all if r['cfg_id'] == c.id])
                        if sc and sc[0] == 1:
                            cand.append((sc[1], c))
                if not cand:
                    log(out, '%s %s: nothing passed the previous round, ruled out' % (label, m[0]))
                    continue
                best_fps = max(f for f, _ in cand)
                tied = sorted([c for f, c in cand if f == best_fps], key=lambda c: (len(factors_of(c)), c.id))
                keep = []
                for c in tied:
                    simpler = [k for k in keep if factors_of(k) < factors_of(c)]
                    if simpler:
                        log(out, '-- %s %s: %s ruled out, %s reached the same fps without %s (no difference)' % (
                            label, m[0], c.id, simpler[0].id, ','.join(sorted(factors_of(c) - factors_of(simpler[0])))))
                        continue
                    keep.append(c)
                for c in keep[:topn]:
                    log(out, '== %s %s: %s from %d fps, %s' % (label, m[0], c.id, best_fps, '%d s' % secs if secs else '30 min / drive full'))
                    bracket(c, best_fps, secs, label, rows_all)

    try:
        if 'N' in a.stages:
            stop['why'] = campaign_main(a, out)
            log(out, 'night %s over: %s' % (a.night, stop['why']))
            return
        if a.fix_budget:
            try:
                rec = set_storage_keys(HWCONF, {'buffer_ram_fraction': '0.9', 'buffer_ram_floor_mb': '256'}, out)
                log(out, 'set [storage] buffer_ram_fraction=0.9 buffer_ram_floor_mb=256 in %s (originals in %s, put back at the end)' % (HWCONF, rec))
            except OSError as e:
                log(out, 'WARNING: could not edit %s: %s' % (HWCONF, e))
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
        if 'c' in a.stages and not stop['now']:
            tier_stage()
        if 'F' in a.stages and not stop['now']:
            follow_log_stage()
        if 'm' in a.stages and not stop['now']:
            meter_stage()
        if 's' in a.stages and not stop['now']:
            split_stage()
        if 'L' in a.stages and not stop['now']:
            long_runs('long30', fps_arg=a.long_fps, factor=0.9)
        if 'M' in a.stages and not stop['now']:
            long_runs('mlv30', fmt='mlv', fps_arg=a.split_fps, factor=0.95)
        if 'k' in a.stages and not stop['now']:
            knob_stage()
        if 'S' in a.stages and not stop['now']:
            soak_stage()
    except Exception as e:
        stop['why'] = 'crashed: %r' % e
        import traceback
        log(out, 'ERROR: the runner crashed: %r\n%s' % (e, traceback.format_exc()))
        raise
    finally:
        release_lock()
        if CAMPAIGN['on']:
            join_ingest()       # the campaign restored its own list (restore_night) and writes DONE-<stage> markers
        else:
            try:
                if restore_storage_keys(HWCONF, out):
                    log(out, 'put the [storage] keys of %s back as they were' % HWCONF)
            except (OSError, ValueError) as e:
                log(out, 'WARNING: could not restore the [storage] keys of %s: %s' % (HWCONF, e))
            try:
                restore_knobs()
            except Exception as e:
                log(out, 'WARNING: could not restore the knobs: %s' % e)
            core('set_record_format', value=orig.get('recording_format') or 'cdng')
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
            if STOP['sig']:
                log(out, 'stopped by %s: no DONE marker, so a crontab @reboot resume continues this run' % STOP['sig'])
            else:
                why = stop['why'] or ('all stages done' if not stop['now'] else 'stopped, see runner.log')
                with open(out + '/DONE', 'w') as f:
                    f.write(time.strftime('%F %T ') + why + '\n')
                log(out, 'DONE marker written (%s): a resume will not restart this run; remove %s/DONE to run it again' % (why, out))


def collections_count(rows, cfg_id):
    d = {}
    for r in rows:
        if r['cfg_id'] == cfg_id and r.get('variant') and (r['outcome'].startswith('ab_') or r['outcome'] == 'buffer_full'):
            d[r['variant']] = d.get(r['variant'], 0) + 1
    return d


if __name__ == '__main__':
    main()
