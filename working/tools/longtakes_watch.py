#!/usr/bin/env python3
"""longtakes_watch.py: the runner's independent watcher (NVMe campaign, build list H15). Runs on the Pi next to longtakes.py.

  python3 -I longtakes_watch.py ~/longtakes/<run>

Reads only <run>/heartbeat (the runner writes the epoch second every 60 s) and <run>/status.json. Opens Core's socket only when
the heartbeat is older than 180 s while <run>/ACTIVE exists AND status.json names a campaign take in progress: then it sends
record_stop once and writes why to <run>/watcher.log and <run>/decisions.log. It never touches a clip, never deletes, and a
recording Patrik starts himself (no campaign take in progress) is never stopped. It waits up to 10 min for ACTIVE to appear and
exits when ACTIVE is gone. (The plan's every-minute crontab relaunch is not possible: this Pi has no crontab, and the @reboot
line was refused on 2026-11-09; start-night.sh starts the watcher with the runner instead.)
"""
import json, os, socket, sys, time

SOCK = '/tmp/apertar-core.sock'


def core(cmd):
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.settimeout(20)
    try:
        s.connect(SOCK)
        s.sendall((json.dumps({'cmd': cmd}) + '\n').encode())
        buf = b''
        while b'\n' not in buf:
            ch = s.recv(1 << 20)
            if not ch:
                break
            buf += ch
        for line in buf.split(b'\n'):
            if line.startswith(b'{"ok"'):
                return json.loads(line)
    except (OSError, ValueError) as e:
        return {'ok': False, 'error': str(e)}
    finally:
        s.close()
    return {'ok': False}


def say(run, msg):
    line = time.strftime('%F %T ') + 'watcher: ' + msg
    for f in ('watcher.log', 'decisions.log'):
        with open(os.path.join(run, f), 'a') as fh:
            fh.write(line + '\n')
    print(line, flush=True)


def main():
    run = os.path.expanduser(sys.argv[1])
    t0 = time.time()
    while not os.path.exists(os.path.join(run, 'ACTIVE')):
        if time.time() - t0 > 600:
            say(run, 'no ACTIVE marker within 10 min: exiting')
            return
        time.sleep(10)
    say(run, 'watching (pid %d)' % os.getpid())
    stopped_for = None
    while os.path.exists(os.path.join(run, 'ACTIVE')):
        time.sleep(30)
        try:
            age = time.time() - float(open(os.path.join(run, 'heartbeat')).read().strip())
        except (OSError, ValueError):
            age = time.time() - t0
        if age <= 180:
            continue
        try:
            st = json.load(open(os.path.join(run, 'status.json')))
        except (OSError, ValueError):
            st = {}
        cur = st.get('current') or {}
        if not st.get('take_in_progress') or stopped_for == json.dumps(cur, sort_keys=True):
            continue
        gs = core('get_state')
        if gs.get('recording'):
            r = core('record_stop')
            say(run, 'heartbeat %.0f s old during the campaign take %s: record_stop sent (%s)' % (age, cur, r.get('ok')))
        else:
            say(run, 'heartbeat %.0f s old, take %s named in the status, Core not recording: nothing to stop' % (age, cur))
        stopped_for = json.dumps(cur, sort_keys=True)
    say(run, 'ACTIVE gone: exiting')


if __name__ == '__main__':
    main()
