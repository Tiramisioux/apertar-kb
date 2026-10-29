#!/usr/bin/env python3
"""Send one flat JSON command to Core: core.py set_clear_hdr value=true
   key@=path  sends the bytes of that file as a text field: core.py set_controls base=h... text@=/home/pi/apertar-hardware.conf dry_run=true
Core also sends events on this socket; the reply is the line that starts with {"ok"."""
import json, socket, sys

msg = {'cmd': sys.argv[1]}
for arg in sys.argv[2:]:
    k, v = arg.split('=', 1)
    if k.endswith('@'):
        with open(v, encoding='utf-8', newline='') as f:
            msg[k[:-1]] = f.read()
        continue
    msg[k] = {'true': True, 'false': False}.get(v, int(v) if v.lstrip('-').isdigit() else v)
s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
s.settimeout(15)
s.connect('/tmp/apertar-core.sock')
s.sendall((json.dumps(msg) + '\n').encode())
buf = b''
while True:
    while b'\n' in buf:
        line, buf = buf.split(b'\n', 1)
        if line.startswith(b'{"ok"'):
            print(line.decode())
            sys.exit(0)
    chunk = s.recv(65536)
    if not chunk:
        break
    buf += chunk
print(buf.decode().split('\n')[0])
