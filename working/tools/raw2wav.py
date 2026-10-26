#!/usr/bin/env python3
"""raw2wav.py CLIP_FOLDER [--format s24] [--rate 48000] [--channels 2]

A take whose card was pulled keeps its audio as audio_capture.raw: headerless PCM,
little-endian, in the format Core logs at record start
("ApertarCore audio capture: format=s24 rate=48000 channels=2"). Core skips the WAV
on a dead medium. This wraps the raw file in a WAV header next to it, as
<clip>.recovered.wav. No resampling and no trimming to the picture: line it up in
the edit (the first sample is about audio_boot_us - video_boot_us after frame 0).
"""
import argparse
import os
import struct

BYTES = {'s16': 2, 's24': 3, 's32': 4, 'float32': 4}

ap = argparse.ArgumentParser()
ap.add_argument('clip')
ap.add_argument('--format', default='s24', choices=BYTES)
ap.add_argument('--rate', type=int, default=48000)
ap.add_argument('--channels', type=int, default=2)
a = ap.parse_args()

raw = os.path.join(a.clip, 'audio_capture.raw')
size = os.path.getsize(raw)
width = BYTES[a.format]
align = width * a.channels
size -= size % align                      # a pull can cut the last frame short
out = os.path.join(a.clip, os.path.basename(os.path.normpath(a.clip)) + '.recovered.wav')
fmt_tag = 3 if a.format == 'float32' else 1
with open(raw, 'rb') as src, open(out, 'wb') as dst:
    dst.write(b'RIFF' + struct.pack('<I', 36 + size) + b'WAVE')
    dst.write(b'fmt ' + struct.pack('<IHHIIHH', 16, fmt_tag, a.channels, a.rate,
                                    a.rate * align, align, width * 8))
    dst.write(b'data' + struct.pack('<I', size))
    left = size
    while left:
        chunk = src.read(min(left, 1 << 20))
        if not chunk:
            break
        dst.write(chunk)
        left -= len(chunk)
print(f"{out}: {size // align} frames, {size / align / a.rate:.2f} s")
