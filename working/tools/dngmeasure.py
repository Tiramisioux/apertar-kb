#!/usr/bin/env python3
"""dngmeasure.py CLIP...: (25 fps assumed for the WAV figure) per clip, frame count, index holes, WAV length vs frames, and the frame-to-frame
level of a centre band (rows 1040-1104 of the raw image) to show flicker."""
import os, re, struct, sys, statistics, wave


def raw_layout(path):
    """(offset, width, height, bits, endian) of the full-resolution uncompressed raw image."""
    with open(path, 'rb') as f:
        head = f.read(2)
        e = '<' if head == b'II' else '>'
        f.seek(4)
        first = struct.unpack(e + 'I', f.read(4))[0]
        sizes = {1: 1, 2: 1, 3: 2, 4: 4, 5: 8, 7: 1, 9: 4, 10: 8, 11: 4, 12: 8, 13: 4, 16: 8}
        todo, seen, found = [first], set(), []
        while todo:
            off = todo.pop()
            if off in seen or off == 0:
                continue
            seen.add(off)
            f.seek(off)
            n = struct.unpack(e + 'H', f.read(2))[0]
            tags = {}
            for _ in range(n):
                tag, typ, cnt = struct.unpack(e + 'HHI', f.read(8))
                val = f.read(4)
                size = sizes.get(typ, 1) * cnt
                if size <= 4:
                    data = val
                else:
                    pos = f.tell()
                    f.seek(struct.unpack(e + 'I', val)[0])
                    data = f.read(size)
                    f.seek(pos)
                fmt = {3: 'H', 4: 'I', 13: 'I'}.get(typ)
                tags[tag] = list(struct.unpack(e + fmt * cnt, data[:struct.calcsize(fmt) * cnt])) if fmt else None
            nxt = struct.unpack(e + 'I', f.read(4))[0]
            todo.append(nxt)
            for sub in tags.get(330) or []:
                todo.append(sub)
            if tags.get(254, [1])[0] == 0 and 273 in tags and tags.get(259, [1])[0] == 1:
                found.append((tags[273][0], tags[256][0], tags[257][0], tags[258][0], e))
        return found[0]


def band_mean(path, layout, row0=1040, rows=64, step=4):
    off, w, h, bits, e = layout
    bpp = bits // 8
    with open(path, 'rb') as f:
        f.seek(off + row0 * w * bpp)
        data = f.read(rows * w * bpp)
    vals = struct.unpack(e + ('H' if bpp == 2 else 'B') * (len(data) // bpp), data)
    return statistics.fmean(vals[::step])


for clip in sys.argv[1:]:
    files = sorted(f for f in os.listdir(clip) if f.endswith('.dng'))
    idx = [int(re.search(r'_(\d{6,})\.dng$', f).group(1)) for f in files]
    holes = [b for a, b in zip(idx, idx[1:]) if b != a + 1]
    layout = raw_layout(os.path.join(clip, files[0]))
    means = [band_mean(os.path.join(clip, f), layout) for f in files]
    steps = [abs(b - a) / a * 100 for a, b in zip(means, means[1:]) if a > 0]
    wavs = [f for f in os.listdir(clip) if f.endswith('.wav')]
    wav_frames = None
    if wavs:
        with wave.open(os.path.join(clip, wavs[0])) as w:
            wav_frames = w.getnframes() / w.getframerate() * 25
    print(f"{os.path.basename(clip)}: frames {len(files)} holes {len(holes)} raw {layout[1]}x{layout[2]} {layout[3]}-bit"
          f" | wav {wav_frames:.2f} frames" if wav_frames is not None else "", end='')
    print(f" | band mean {statistics.fmean(means):.1f} sd {statistics.pstdev(means):.2f}"
          f" | frame-to-frame step % mean {statistics.fmean(steps):.4f} p99 {sorted(steps)[int(len(steps)*0.99)]:.4f} max {max(steps):.4f}")
