#!/usr/bin/env python3
"""User-space IP sampler for one thread (perf_event_open, cpu-clock, exclude_kernel).

usage: python3 -I usample.py <pid> <tid> [seconds]
No perf/gdb on the image; this needs none (perf_event_paranoid=2 allows user-only sampling
of your own processes). Read-only: the target is not stopped. Find the tid with top -H -p <pid>.
Prints the top symbols (leaf) and the top callers seen in the user callchain.
"""
import collections, ctypes, mmap, os, select, struct, subprocess, sys, time

pid, tid = int(sys.argv[1]), int(sys.argv[2])
secs = float(sys.argv[3]) if len(sys.argv) > 3 else 5.0

PERF_TYPE_SOFTWARE, PERF_COUNT_SW_CPU_CLOCK = 1, 0
SAMPLE_IP, SAMPLE_TID, SAMPLE_CALLCHAIN = 1, 2, 1 << 5
attr = bytearray(112)
struct.pack_into('IIQQQQ', attr, 0, PERF_TYPE_SOFTWARE, 112, PERF_COUNT_SW_CPU_CLOCK,
                 1_000_000, SAMPLE_IP | SAMPLE_TID | SAMPLE_CALLCHAIN, 0)
# flags: exclude_kernel (bit 5), exclude_hv (bit 6), exclude_callchain_kernel (bit 21)
struct.pack_into('Q', attr, 40, (1 << 5) | (1 << 6) | (1 << 21))
struct.pack_into('H', attr, 108, 64)  # sample_max_stack

libc = ctypes.CDLL(None, use_errno=True)
buf = ctypes.create_string_buffer(bytes(attr), 112)
fd = libc.syscall(241, buf, tid, -1, -1, 8)
if fd < 0:
    sys.exit(f'perf_event_open: {os.strerror(ctypes.get_errno())}')

PAGE = mmap.PAGESIZE
NPAGES = 64
ring = mmap.mmap(fd, PAGE * (NPAGES + 1), mmap.MAP_SHARED, mmap.PROT_READ | mmap.PROT_WRITE)
DATA, SIZE = PAGE, PAGE * NPAGES

leaf = collections.Counter()
chains = []
lost = 0
deadline = time.time() + secs
while time.time() < deadline:
    select.select([fd], [], [], 0.02)
    head = struct.unpack_from('Q', ring, 1024)[0]
    tail = struct.unpack_from('Q', ring, 1032)[0]
    while tail < head:
        off = tail % SIZE
        hdr = bytes(ring[DATA + off:DATA + off + 8]) if off + 8 <= SIZE else \
            bytes(ring[DATA + off:DATA + SIZE]) + bytes(ring[DATA:DATA + (off + 8 - SIZE)])
        rtype, misc, rsize = struct.unpack('IHH', hdr)
        if off + rsize <= SIZE:
            rec = bytes(ring[DATA + off:DATA + off + rsize])
        else:
            rec = bytes(ring[DATA + off:DATA + SIZE]) + bytes(ring[DATA:DATA + (off + rsize - SIZE)])
        if rtype == 9:
            ip, = struct.unpack_from('Q', rec, 8)
            nr, = struct.unpack_from('Q', rec, 24)
            ips = list(struct.unpack_from(f'{nr}Q', rec, 32))
            ips = [a for a in ips if a < 0xfffffffffffff000]
            leaf[ip] += 1
            chains.append(ips)
        elif rtype == 2:
            lost += struct.unpack_from('Q', rec, 16)[0]
        tail += rsize
    struct.pack_into('Q', ring, 1032, tail)

maps = []
for line in open(f'/proc/{pid}/maps'):
    parts = line.split()
    if len(parts) >= 6 and 'x' in parts[1]:
        lo, hi = (int(x, 16) for x in parts[0].split('-'))
        maps.append((lo, hi, int(parts[2], 16), parts[5]))

def where(ip):
    for lo, hi, off, path in maps:
        if lo <= ip < hi:
            return path, ip - lo + off
    return None, ip

cache = {}
def sym(ip):
    if ip in cache:
        return cache[ip]
    path, rel = where(ip)
    name = '?'
    if path:
        try:
            out = subprocess.run(['addr2line', '-f', '-C', '-e', path, hex(rel)],
                                 capture_output=True, text=True, timeout=10).stdout.split('\n')
            name = out[0] if out and out[0] != '??' else f'?+{rel:#x}'
        except Exception:
            pass
        name = f'{os.path.basename(path)}: {name}'
    cache[ip] = name
    return name

total = sum(leaf.values())
print(f'samples={total} lost={lost} over {secs:.1f}s (1 sample/ms cpu)')
by_sym = collections.Counter()
for ip, n in leaf.items():
    by_sym[sym(ip)] += n
print('\n== leaf functions')
for name, n in by_sym.most_common(15):
    print(f'{100.0 * n / total:5.1f}%  {name[:150]}')

inclusive = collections.Counter()
for ips in chains:
    seen = set()
    for ip in ips[:40]:
        s = sym(ip)
        if s not in seen:
            seen.add(s)
            inclusive[s] += 1
print('\n== inclusive (on the callchain)')
for name, n in inclusive.most_common(25):
    print(f'{100.0 * n / total:5.1f}%  {name[:150]}')
