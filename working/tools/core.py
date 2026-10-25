#!/usr/bin/env python3
"""Send one flat JSON command to Core: core.py set_clear_hdr value=true"""
import json, socket, sys

msg = {'cmd': sys.argv[1]}
for arg in sys.argv[2:]:
    k, v = arg.split('=', 1)
    msg[k] = {'true': True, 'false': False}.get(v, int(v) if v.lstrip('-').isdigit() else v)
s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
s.settimeout(15)
s.connect('/tmp/apertar-core.sock')
s.sendall((json.dumps(msg) + '\n').encode())
buf = b''
while b'\n' not in buf:
    chunk = s.recv(65536)
    if not chunk:
        break
    buf += chunk
print(buf.split(b'\n')[0].decode())
