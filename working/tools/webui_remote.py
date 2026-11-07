#!/usr/bin/env python3
"""webui_remote.py (Mac): the real WebUI client for longtakes.py --web-remote.

Follows <run>/web_flag on the Pi through ONE ssh connection (tail -F, no polling of the Pi) and runs
webui_client.py against the Pi while the last line is 1; stops it when the last line is 0.
  python3 -I webui_remote.py ~/longtakes/<run-dir> [--host apertar.local]
Keep the Mac awake:  caffeinate -i python3 -I webui_remote.py ...
"""
import argparse, os, subprocess, sys, time

ap = argparse.ArgumentParser()
ap.add_argument('rundir')
ap.add_argument('--host', default='apertar.local')
ap.add_argument('--ssh', default='apertar')
a = ap.parse_args()
here = os.path.dirname(os.path.abspath(__file__))
client = None
logdir = os.path.expanduser('~/Documents/Apertar/apertar-kb/working/drop-frames/tests-2026-11/webui-mac')
os.makedirs(logdir, exist_ok=True)


def want(on):
    global client
    if on and client is None:
        client = subprocess.Popen([sys.executable, '-I', os.path.join(here, 'webui_client.py'), '--host', a.host,
                                   '--port', '8000', '--log', '%s/%s.log' % (logdir, time.strftime('%Y%m%d-%H%M%S'))],
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(time.strftime('%T'), 'client started', flush=True)
    elif not on and client is not None:
        client.terminate(); client.wait(); client = None
        print(time.strftime('%T'), 'client stopped', flush=True)


while True:
    p = subprocess.Popen(['ssh', '-o', 'ServerAliveInterval=15', a.ssh,
                          'touch %s/web_flag; tail -n1 -F %s/web_flag' % (a.rundir, a.rundir)],
                         stdout=subprocess.PIPE, text=True)
    for line in p.stdout:
        want(line.strip() == '1')
    want(False)
    time.sleep(5)    # ssh dropped: reconnect
