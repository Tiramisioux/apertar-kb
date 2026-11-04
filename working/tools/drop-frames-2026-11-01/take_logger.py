#!/usr/bin/env python3
"""take_logger.py CORE_PID UI_PID OUT [KEY ...]: the 1 Hz log of a take (M5 of inspection-2026-11-02.md), in one process.

Every second, one line to OUT (put it in /run/apertar-media, never on /media/RAW):
  t=<epoch> vm k=v ... | mem MemFree= Dirty= Writeback= (kB) | nvme writes= ticks_ms= | psi <memory some/full> |
  dropped=<recording_dropped_frames> | thr tid:comm:run_ns:wait_ns:majflt ... | temp nvme_mC= soc_mC= (milli-degrees C, n/a if unreadable)
for every thread of Core and of the UI. It reads only /proc and /sys, and asks Core for get_state over its socket
(the same request core.py sends), so the logger costs one process and no spawns per second. Read-only, no sudo.
Stops on SIGTERM or when Core's process is gone.
"""
import glob
import json
import os
import signal
import socket
import sys
import time

core, ui, out = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
keys = set(sys.argv[4:])
stop = False
signal.signal(signal.SIGTERM, lambda *_: globals().__setitem__('stop', True))


def read(path):
    try:
        with open(path) as f:
            return f.read()
    except OSError:
        return ''


def vmstat():
    parts = []
    for line in read('/proc/vmstat').splitlines():
        k, _, v = line.partition(' ')
        if k in keys:
            parts.append(f'{k}={v}')
    return ' '.join(parts)


def meminfo():
    want = ('MemFree', 'Dirty', 'Writeback')
    parts = []
    for line in read('/proc/meminfo').splitlines():
        k, _, v = line.partition(':')
        if k in want:
            parts.append(f'{k}={v.split()[0]}')
    return ' '.join(parts)


def nvme():
    f = read('/sys/block/nvme0n1/stat').split()
    return f'writes={f[4]} ticks_ms={f[7]}' if len(f) > 7 else 'n/a'


def psi():
    text = read('/proc/pressure/memory')
    return ' '.join(text.split()) if text else 'off'


CSI2 = next(iter(sorted(glob.glob('/sys/kernel/debug/rp1-cfe*/csi2_errors'))), '')


def csi2():
    # rp1-cfe CSI-2 receiver discards since the previous read (the file is cleared on read: the logger must be its only
    # reader during a take): Overflows, then OVLF/LEN/UNMATCHED/INACTIVE per virtual channel with any non-zero
    parts = []
    for line in read(CSI2).splitlines():
        w = line.split()
        if w[:1] == ['Overflows'] and len(w) == 2:
            parts.append(f'ovf={w[1]}')
        elif len(w) == 5 and w[0].isdigit() and any(x != '0' for x in w[1:]):
            parts.append(f'vc{w[0]}=' + '/'.join(w[1:]))
    return ' '.join(parts) if CSI2 else 'n/a'


def boost():
    # watermark boost per node and zone, in pages: the sum, then only the non-zero ones (n<node>z<zone>=<pages>)
    parts, total, node, zone = [], 0, '?', '?'
    for line in read('/proc/zoneinfo').splitlines():
        w = line.split()
        if line.startswith('Node') and len(w) >= 4:
            node, zone = w[1].rstrip(','), w[3]
        elif len(w) == 2 and w[0] == 'boost' and w[1].isdigit():
            total += int(w[1])
            if w[1] != '0':
                parts.append(f'n{node}z{zone}={w[1]}')
    return ' '.join([f'sum={total}'] + parts)


NVME_TEMP = next(iter(sorted(glob.glob('/sys/class/nvme/nvme0/hwmon*/temp1_input'))), '')
SOC_TEMP = '/sys/class/thermal/thermal_zone0/temp'


def temps():
    # NVMe (first hwmon, path resolved once) and SoC temperature, milli-degrees C, re-read each second
    parts = []
    for name, path in (('nvme_mC', NVME_TEMP), ('soc_mC', SOC_TEMP)):
        v = read(path).strip() if path else ''
        parts.append(f'{name}={v if v.lstrip("-").isdigit() else "n/a"}')
    return ' '.join(parts)


def threads(pid):
    parts = []
    base = f'/proc/{pid}/task'
    try:
        tids = os.listdir(base)
    except OSError:
        return parts
    for tid in tids:
        sched = read(f'{base}/{tid}/schedstat').split()
        stat = read(f'{base}/{tid}/stat')
        comm = read(f'{base}/{tid}/comm').strip().replace(' ', '_')
        if len(sched) < 2 or not stat:
            continue
        # comm in stat is in parentheses and may contain spaces: split after the last ')'
        fields = stat.rsplit(')', 1)[-1].split()
        majflt = fields[9] if len(fields) > 9 else '?'   # field 12 of stat = index 9 after pid and comm
        parts.append(f'{tid}:{comm}:{sched[0]}:{sched[1]}:{majflt}')
    return parts


def dropped():
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(0.5)
        s.connect('/tmp/apertar-core.sock')
        s.sendall(b'{"cmd": "get_state"}\n')
        buf = b''
        deadline = time.monotonic() + 0.5
        while time.monotonic() < deadline:
            while b'\n' in buf:
                line, buf = buf.split(b'\n', 1)
                if line.startswith(b'{"ok"'):
                    s.close()
                    return json.loads(line).get('recording_dropped_frames')
            chunk = s.recv(65536)
            if not chunk:
                break
            buf += chunk
        s.close()
    except (OSError, ValueError):
        pass
    return None


with open(out, 'w', buffering=1) as f:
    nxt = time.monotonic()
    while not stop and os.path.exists(f'/proc/{core}'):
        f.write(f't={time.time():.2f} vm {vmstat()} | mem {meminfo()} | nvme {nvme()} | boost {boost()} | csi2 {csi2()} | psi {psi()} | '
                f'dropped={dropped()} | thr {" ".join(threads(core) + threads(ui))} | temp {temps()}\n')
        nxt += 1.0
        time.sleep(max(0.0, nxt - time.monotonic()))
