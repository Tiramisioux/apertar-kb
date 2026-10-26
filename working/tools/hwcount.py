#!/usr/bin/env python3
"""Cortex-A76 PMU counters for one thread, user space only: hwcount.py <pid> <tid> [seconds]

Read-only (perf_event_open, perf_event_paranoid=2 allows user-only counting of your own processes).
Prints IPC, backend-stall share and memory-side refills per second. A drop in IPC with the same code
running, and a rise in stall_backend, means the thread waits on memory.
"""
import ctypes, os, struct, sys, time

pid, tid = int(sys.argv[1]), int(sys.argv[2])
secs = float(sys.argv[3]) if len(sys.argv) > 3 else 5.0
PMU_TYPE = int(open('/sys/bus/event_source/devices/armv8_cortex_a76/type').read())
EVENTS = [('cycles', 0x11), ('instructions', 0x08), ('stall_backend', 0x24),
          ('l3d_refill', 0x2a), ('ll_miss_rd', 0x37), ('bus_access', 0x19)]
READ_FORMAT = 1 | 2  # TOTAL_TIME_ENABLED | TOTAL_TIME_RUNNING (multiplexing scale)

libc = ctypes.CDLL(None, use_errno=True)
fds = []
for name, code in EVENTS:
    attr = bytearray(112)
    struct.pack_into('IIQQQQ', attr, 0, PMU_TYPE, 112, code, 0, 0, READ_FORMAT)
    struct.pack_into('Q', attr, 40, (1 << 5) | (1 << 6))  # exclude_kernel, exclude_hv
    buf = ctypes.create_string_buffer(bytes(attr), 112)
    fd = libc.syscall(241, buf, tid, -1, -1, 8)
    if fd < 0:
        sys.exit(f'perf_event_open {name}: {os.strerror(ctypes.get_errno())}')
    fds.append((name, fd))

def read_all():
    out = {}
    for name, fd in fds:
        value, enabled, running = struct.unpack('QQQ', os.read(fd, 24))
        out[name] = value * enabled / running if running else 0.0
    return out

a = read_all(); time.sleep(secs); b = read_all()
d = {k: (b[k] - a[k]) / secs for k in a}
ipc = d['instructions'] / d['cycles'] if d['cycles'] else 0
stall = d['stall_backend'] / d['cycles'] if d['cycles'] else 0
print(f"tid={tid} over {secs:.0f}s: user cycles={d['cycles']/1e6:.0f}M/s ipc={ipc:.2f} stall_backend={stall*100:.0f}% "
      f"l3d_refill={d['l3d_refill']/1e6:.1f}M/s ll_miss_rd={d['ll_miss_rd']/1e6:.1f}M/s bus_access={d['bus_access']/1e6:.1f}M/s")
