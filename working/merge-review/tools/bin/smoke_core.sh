#!/bin/bash
# Starts an apertar-core binary in --simulate mode and prints the shape of its main replies, so two builds can be
# compared (a field that vanished or changed type shows up in a diff).
#   smoke_core.sh <apertar-core binary> <port> [outfile]
BIN=${1:?binary}; PORT=${2:?port}; OUT=${3:-/dev/stdout}
# A fresh folder per run, and its own hardware-file path, so a run never reads or writes /home/pi/apertar-hardware.conf.
DIR=/home/user/build/sim/smoke-$PORT; rm -rf "$DIR"; mkdir -p "$DIR/media"
HOME=$DIR APERTAR_HARDWARE_CONFIG=$DIR/apertar-hardware.conf timeout 60 "$BIN" --simulate --socket "$DIR/core.sock" --media "$DIR/media" --web-bind 127.0.0.1 --web-port "$PORT" > "$DIR/core.log" 2>&1 &
PID=$!
for i in $(seq 1 40); do curl -s -m 1 "http://127.0.0.1:$PORT/api/state" > /dev/null 2>&1 && break; python3 -c "import time; time.sleep(0.25)"; done
python3 - "$PORT" > "$OUT" <<'PY'
import json, sys, urllib.request
port = sys.argv[1]
def shape(v, depth=0):
    if isinstance(v, dict):
        return {k: shape(x, depth + 1) for k, x in sorted(v.items())} if depth < 3 else 'object'
    if isinstance(v, list):
        return ['%d x %s' % (len(v), type(v[0]).__name__ if v else 'empty')]
    return type(v).__name__
def call(method, path, body=None):
    try:
        req = urllib.request.Request('http://127.0.0.1:%s%s' % (port, path), data=body.encode() if body else None, method=method)
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, r.read().decode('utf-8', 'replace')
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode('utf-8', 'replace')
    except Exception as e:
        return 0, str(e)
def show(title, status, text):
    print('== %s -> %s' % (title, status))
    try:
        print(json.dumps(shape(json.loads(text)), indent=1))
    except ValueError:
        print('  (not JSON, %d bytes) %s' % (len(text), text[:120].replace('\n', ' ')))
show('GET /api/state', *call('GET', '/api/state'))
for cmd in ['get_state', 'ping', 'help', 'list_sensor_modes', 'get_controls', 'list_actions', 'get_mode_ladder', 'get_boot_config',
            'audio_capabilities', 'get_media_test_state', 'controls_history', 'preview_clip_name']:
    show('command ' + cmd, *call('POST', '/api/command', json.dumps({'cmd': cmd})))
for path in ['/api/media', '/api/config', '/api/presets', '/api/buffer', '/api/boot-config']:
    show('GET ' + path, *call('GET', path))
s, page = call('GET', '/')
print('== GET / -> %s, %d bytes, %d lines' % (s, len(page), page.count('\n')))
PY
kill $PID 2>/dev/null; wait $PID 2>/dev/null
grep -c . "$DIR/core.log" > /dev/null
