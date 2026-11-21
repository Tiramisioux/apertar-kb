#!/usr/bin/env python3
"""figures.py: the pre-analysis figures, from the NVMe run folder's 1 Hz samples and the EST probes.

  <venv with matplotlib>/bin/python figures.py [--run ../../nvme-campaign/run-20261110] [--out ../figures]

fig1-pipeline.png   the recording path and its four walls (schematic)
fig2-warming.png    how fast each mode warms the drive, against its write rate (every NVMe take >= 50 s)
fig3-long-takes.png drive temperature and RAM buffer over the 10-15 min takes, with the first event marked
fig4-walls.png      per mode: frame size -> the fps where each wall stands; the lowest one sets the mode's limit
fig6-flow-and-hole.png  flow (MB/s) against the drive's hole over a take, and the headroom after a write pause
fig7-levers.png     what each lever does on the back-end, encoder and storage anchors (raw P2 means)
Also prints the per-take numbers as a markdown table (warming.md in --out).
"""
import argparse
import csv
import glob
import json
import os
import re
import statistics as st

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt                       # noqa: E402
from matplotlib.patches import FancyBboxPatch         # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
FAM_COL = {'4K uncompressed cDNG': '#c0392b', '4K uncompressed + Log': '#e67e22', '4K MLV': '#8e44ad',
           '4K lossless / lossy cDNG': '#2471a3', '4K ProRes / H.264': '#17a589', '2K (every format)': '#7f8c8d'}
NVME_COLD, NVME_WARM, NVME_PAUSING, T7 = 560, 465, 414, 105       # MB/s, measured (see pre-analysis 2c-0)


def parse_name(fn):
    b = os.path.basename(fn)[:-4]
    tok = b.split('_')
    mode, comp, log = tok[0], tok[1], tok[2] == 'log1'
    fmt = 'cdng'
    for t in tok:
        if t == 'mlv':
            fmt = 'mlv'
        elif t.startswith(('prores-', 'h264', 'lossydng-')):
            fmt = t
    fps = int(re.search(r'_fps(\d+)_', b).group(1))
    stamp = b.rsplit('_', 1)[1]
    return dict(name=b, mode=mode, comp=comp, log=log, fmt=fmt, fps=fps, stamp=stamp,
                tdn=tok[3] == 'tdn1')


def family(p):
    if p['mode'].startswith('2k'):
        return '2K (every format)'
    if p['fmt'].startswith(('prores', 'h264')):
        return '4K ProRes / H.264'
    if p['fmt'] == 'mlv':
        return '4K MLV'
    if p['fmt'].startswith('lossydng') or p['comp'] == 'lossless':
        return '4K lossless / lossy cDNG'
    return '4K uncompressed + Log' if p['log'] else '4K uncompressed cDNG'


def label(p):
    m = {'4kHDR16': '4K HDR16', '4kHDR12': '4K HDR12', '4kSDR12': '4K SDR12', '4kSDR10': '4K SDR10', '4kP': '4K',
         '2kHDR16': '2K HDR16', '2kSDR12': '2K SDR12', '2kP': '2K', 'crop4k3SDR12': '2880 crop SDR12'}.get(p['mode'], p['mode'])
    f = p['fmt']
    if f == 'cdng':
        f = {'unc': 'unc', 'none': 'unc', 'lossless': 'lossless'}.get(p['comp'], p['comp'])
    return '%s %s%s %d fps' % (m, f, ' Log' if p['log'] else '', p['fps'])


def load_samples(fn):
    rows = []
    with open(fn) as f:
        for r in csv.DictReader(f):
            try:
                cap = float(r.get('buffer_capacity') or 0)
                rows.append(dict(t=float(r['t_s']), nv=float(r['nvme_c']), pi=float(r['pi_c'] or 'nan'),
                                 sec=float(r['dev_w_sectors'] or 'nan'),
                                 buf=float(r['buffer_used'] or 0) / cap if cap > 0 else 0.0,
                                 drop=int(float(r['dropped'] or 0)), rec=r['state'] == 'rec'))
            except (ValueError, ZeroDivisionError, KeyError):
                continue
    return [r for r in rows if r['rec']]


def take_stats(fn):
    p = parse_name(fn)
    s = load_samples(fn)
    if len(s) < 50:
        return None
    dur = s[-1]['t'] - s[0]['t']
    mbps = (s[-1]['sec'] - s[0]['sec']) * 512 / 1e6 / dur if dur > 0 else float('nan')
    t0 = s[0]['nv']
    w = [r for r in s if r['t'] - s[0]['t'] <= 60]
    rise60 = w[-1]['nv'] - t0
    ev = next((r for r in s if r['buf'] > 0.5 or r['drop'] > 0), None)
    gb_ev = (ev['sec'] - s[0]['sec']) * 512 / 1e9 if ev else None
    return dict(p, fam=family(p), lab=label(p), dur=dur, mbps=mbps, t0=t0, tmax=max(r['nv'] for r in s),
                rise60=rise60, permin=(s[-1]['nv'] - t0) / (dur / 60), ev_t=ev['t'] if ev else None,
                ev_c=ev['nv'] if ev else None, gb_ev=gb_ev, gb=(s[-1]['sec'] - s[0]['sec']) * 512 / 1e9,
                pimax=max(r['pi'] for r in s), series=s)


def fig_pipeline(out):
    fig, ax = plt.subplots(figsize=(13, 5.2))
    ax.set_xlim(0, 13)
    ax.set_ylim(0, 5.2)
    ax.axis('off')
    boxes = [(0.2, 'Sensor\nIMX585', 'top fps per mode\n4K HDR 30, 4K SDR 60\n2K 30 / 60', '#7f8c8d'),
             (2.3, 'Back end\nISP + copy', 'every frame copied out\nof the camera buffers;\nTDN, Log, phase lock\nadd CPU here', '#c0392b'),
             (4.6, 'Encoder (CPU)', 'uncompressed: ~0\nlossless / lossy JPEG,\nProRes, H.264: the\n4 cores, up to ~340 %', '#2471a3'),
             (6.9, 'RAM buffer\n1.06 GB to\nsafety stop', 'absorbs pauses:\n1.06 GB / MB/s =\n2-3 s at 4K unc,\n10 s at 2K', '#8e44ad'),
             (9.0, 'Writer\nexFAT', 'one file per frame\n(cDNG): folder walk\ngrows per file;\nsplit take caps it', '#e67e22'),
             (11.1, 'Drive', 'NVMe ~560 cold, ~465\nwarm MB/s; pauses ~2 s\nafter 265-375 GB / 74 °C\nT7 SSD ~105 MB/s', '#17a589')]
    for x, title, body, col in boxes:
        ax.add_patch(FancyBboxPatch((x, 2.6), 1.75, 1.6, boxstyle='round,pad=0.05', fc=col, ec='none', alpha=0.9))
        ax.text(x + 0.875, 3.4, title, ha='center', va='center', color='white', fontsize=10.5, weight='bold')
        ax.text(x + 0.875, 2.3, body, ha='center', va='top', fontsize=8.6, color='#222')
    for x in (2.0, 4.3, 6.6, 8.7, 10.8):
        ax.annotate('', xy=(x + 0.25, 3.4), xytext=(x, 3.4), arrowprops=dict(arrowstyle='-|>', color='#444', lw=1.6))
    ax.text(6.5, 4.85, 'The recording path: a mode runs at the first wall it reaches',
            ha='center', fontsize=13, weight='bold')
    ax.text(6.5, 0.35, 'Bigger frames (resolution x bit depth, less compression) push on the drive. '
            'Compression moves the load to the CPU. HDR and Log load the back end.\n'
            'A drop shows as capture gaps (back end or encoder behind) or "buffer full" (the drive behind for longer than '
            'the buffer lasts).', ha='center', fontsize=9.3, color='#333')
    fig.savefig(out + '/fig1-pipeline.png', dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)


def fig_warming(takes, out):
    fig, (a, b) = plt.subplots(1, 2, figsize=(13, 5.4))
    for fam, col in FAM_COL.items():
        xs = [t for t in takes if t['fam'] == fam and t['dur'] >= 50]
        if not xs:
            continue
        a.scatter([t['mbps'] for t in xs], [t['rise60'] for t in xs], s=22, c=col, alpha=0.75, label=fam)
        ls = [t for t in xs if t['dur'] >= 170]
        b.scatter([t['mbps'] for t in ls], [t['tmax'] for t in ls], s=[12 + t['dur'] / 10 for t in ls], c=col, alpha=0.75,
                  label=fam)
    a.set_xlabel('write rate to the drive, MB/s (measured, device sectors)')
    a.set_ylabel('drive temperature rise in the first 60 s, °C')
    a.set_title('How fast a mode warms the drive: it follows the write rate')
    a.legend(fontsize=8, loc='upper left')
    a.grid(alpha=0.3)
    b.axhspan(73.5, 80, color='#c0392b', alpha=0.08)
    b.text(20, 77.3, 'every write pause came in here (74-79 °C, after 265 GB+)', fontsize=8.5, color='#c0392b')
    b.set_xlabel('write rate, MB/s')
    b.set_ylabel('highest drive temperature in the take, °C')
    b.set_title('Peak drive temperature, takes of 3 min or more (dot size = length)')
    b.grid(alpha=0.3)
    for ax in (a, b):
        for v, n in ((T7, 'T7 SSD limit'), (NVME_WARM, 'NVMe warm')):
            ax.axvline(v, color='#555', ls=':', lw=1)
            ax.text(v + 5, ax.get_ylim()[0] + 0.3, n, fontsize=7.5, color='#555', rotation=90, va='bottom')
    fig.tight_layout()
    fig.savefig(out + '/fig2-warming.png', dpi=150, facecolor='white')
    plt.close(fig)


def fig_long(takes, out):
    ls = sorted([t for t in takes if t['dur'] >= 600], key=lambda t: t['stamp'])
    fig, (a, b) = plt.subplots(2, 1, figsize=(12, 7.5), sharex=True, gridspec_kw=dict(height_ratios=[3, 1.4]))
    cm = plt.get_cmap('tab10')
    for i, t in enumerate(ls):
        s = t['series']
        x = [(r['t'] - s[0]['t']) / 60 for r in s]
        col = cm(i % 10)
        lab = '%s, %.0f MB/s' % (t['lab'], t['mbps'])
        if t['ev_t'] is not None:
            lab += ': %s at %.1f min, %.0f GB' % ('pause, drained, take passed' if t['dur'] >= 890 else 'event',
                                                 (t['ev_t'] - s[0]['t']) / 60, t['gb_ev'])
        else:
            lab += ': clean'
        a.plot(x, [r['nv'] for r in s], color=col, lw=1.4, label=lab)
        b.plot(x, [100 * r['buf'] for r in s], color=col, lw=1.1)
        if t['ev_t'] is not None:
            xe = (t['ev_t'] - s[0]['t']) / 60
            a.plot([xe], [t['ev_c']], 'X', color=col, ms=10, mec='black')
    a.axhspan(73.5, 80, color='#c0392b', alpha=0.08)
    a.set_ylabel('drive temperature, °C')
    a.set_title('The 10-15 min takes: the drive heats for ~10 min, then the first write pause (X)')
    a.legend(fontsize=7.6, loc='lower right')
    a.grid(alpha=0.3)
    b.set_ylabel('RAM buffer, %')
    b.set_xlabel('minutes into the take')
    b.axhline(50, color='#c0392b', ls=':', lw=1)
    b.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(out + '/fig3-long-takes.png', dpi=150, facecolor='white')
    plt.close(fig)


# measured compute walls (fps) from the pre-analysis table: (label, spec, wall, what)
WALLS = [('4K HDR16 unc', '4kHDR16:cdng:unc', 29, 'back end'),
         ('4K HDR16 unc + Log', '4kHDR16:cdng:unc:log', 26, 'back end'),
         ('4K HDR16 lossless', '4kHDR16:cdng:lj', 15, 'encoder'),
         ('4K HDR12 unc', '4kHDR12:cdng:unc', 26, 'back end'),
         ('4K SDR12 unc', '4kSDR12:cdng:unc', 50, 'back end (>= 50, not reached)'),
         ('4K SDR12 lossless', '4kSDR12:cdng:lj', 41.5, 'encoder'),
         ('4K SDR12 lossy 3:1', '4kSDR12:lossydng:3to1', 39.5, 'encoder'),
         ('4K SDR12 lossy 5:1', '4kSDR12:lossydng:5to1', 43, 'encoder'),
         ('4K SDR12 MLV', '4kSDR12:mlv', 26, 'MLV writer'),
         ('4K SDR10 unc', '4kSDR10:cdng:unc', 46, 'back end'),
         ('2880 crop SDR12 unc', 'crop4k3SDR12:cdng:unc', 60, 'not reached'),
         ('4K ProRes HQ', '4kP:prores:hq', 28.7, 'encoder'),
         ('4K ProRes 422', '4kP:prores:422', 41.5, 'encoder'),
         ('H.264 2560x1440', '4kP:h264:2560x1440', 47.3, 'encoder'),
         ('2K HDR16 unc', '2kHDR16:cdng:unc', 99, ''),
         ('2K SDR12 unc', '2kSDR12:cdng:unc', 99, '')]


# how long a take records clean (from the recipes, pre-analysis 5a): NVMe | T7
REC_TIME = {
    '4K HDR16 unc': 'NVMe 27: ~10-12 min (measured); 24: 15 min+ (derived)  |  T7: 6 fps',
    '4K HDR16 unc + Log': 'NVMe 24-25: 5 min measured, 30 min uncertain  |  T7: ~8 fps',
    '4K HDR16 lossless': 'NVMe 14: 30 min probable  |  T7 9: 30 min probable',
    '4K HDR12 unc': 'NVMe 25-30: dropped within 2-93 s (measured)  |  T7: ~8 fps',
    '4K SDR12 unc': 'NVMe 37: 15 min passed, 38: 13 min (measured)  |  T7: ~8 fps',
    '4K SDR12 lossless': 'NVMe 40: 30 min probable  |  T7 18: 30 min probable',
    '4K SDR12 lossy 3:1': 'NVMe 37: 30 min probable  |  T7 28: 30 min probable',
    '4K SDR12 lossy 5:1': 'NVMe 41: 30 min probable  |  T7 41: 30 min probable',
    '4K SDR12 MLV': 'NVMe 25: 30 min uncertain  |  T7: ~8 fps',
    '4K SDR10 unc': 'NVMe 43-45: ~10 min (derived)  |  T7: ~10 fps',
    '2880 crop SDR12 unc': 'NVMe 50: ~10 min (derived)  |  T7: ~11 fps',
    '4K ProRes HQ': 'NVMe 25: 30 min probable  |  T7 22: 30 min probable',
    '4K ProRes 422': 'NVMe and T7 40: 30 min probable',
    'H.264 2560x1440': 'NVMe and T7 45: 30 min probable',
    '2K HDR16 unc': 'NVMe 30: 30 min probable  |  T7 lossless 27: 30 min passed',
    '2K SDR12 unc': 'NVMe 60: 30 min probable  |  T7 32 (split): 30 min passed',
}


FRAME_MB = {'4kP:prores:hq': 4.47, '4kP:prores:422': 1.78, '4kP:h264:2560x1440': 0.02}   # measured, samples 2026-11-21


def rec_status(txt):
    """'passed' (a 30-min take passed), 'probable' (30 min probable), or None."""
    if '30 min passed' in txt:
        return 'passed'
    if '30 min probable' in txt:
        return 'probable'
    return None


def fig_walls(probes, out):
    by = {}
    for p in probes:
        if p.get('bpf') and p.get('spec'):
            by.setdefault(p['spec'], []).append((p['bpf'], p.get('top') or 60))
    for spec, mb in FRAME_MB.items():         # no bpf in the probe records: measured write rate / delivered fps
        by.setdefault(spec, [(mb * 1e6, 60)])
    rows = []
    for lab, spec, wall, what in WALLS:
        if spec not in by:
            continue
        bpf = st.median(b for b, _ in by[spec]) / 1e6
        top = st.median(t for _, t in by[spec])
        rows.append((lab, bpf, top, wall, what))
    fig, ax = plt.subplots(figsize=(17, 0.75 * len(rows) + 1.8))
    for i, (lab, bpf, top, wall, what) in enumerate(reversed(rows)):
        cands = {'sensor': top, 'NVMe warm': NVME_WARM / bpf, 'CPU: ' + (what or 'n/a'): wall}
        lim_n = min(cands, key=cands.get)
        lim = cands[lim_n]
        lo = min(T7 / bpf, lim)
        ax.plot([0, min(lim, 62)], [i, i], color='#ddd', lw=6, solid_capstyle='butt', zorder=1)
        ax.plot([lim], [i], 'o', color='black', ms=9, zorder=5)
        ax.text(64, i + 0.16, '%.0f fps: %s' % (lim, lim_n.replace('CPU: ', '')), va='bottom', fontsize=8.4, weight='bold')
        parts = REC_TIME.get(lab, '-').split('  |  ')
        if len(parts) == 1:
            parts = [parts[0].replace('NVMe and T7', 'NVMe'), parts[0].replace('NVMe and T7', 'T7')]
        ok_any = False
        for k, txt in enumerate(parts):
            ok = rec_status(txt)
            ok_any = ok_any or bool(ok)
            ax.text(64, i + 0.08 - 0.3 * k, txt, va='top', fontsize=7.8,
                    color={'passed': '#0b6e3c', 'probable': '#17a589'}.get(ok, '#666'),
                    weight='bold' if ok else 'normal')
        if ok_any:
            ax.axhspan(i - 0.46, i + 0.46, color='#17a589', alpha=0.08, zorder=0)
        ax.plot([min(T7 / bpf, 62)], [i], 's', color='#17a589', ms=7, zorder=4)
        ax.plot([min(NVME_COLD / bpf, 62)], [i], '|', color='#2471a3', ms=14, mew=2, zorder=3)
        ax.plot([min(NVME_WARM / bpf, 62)], [i], 'D', color='#2471a3', ms=7, zorder=4)
        ax.plot([min(NVME_PAUSING / bpf, 62)], [i], 'v', color='#c0392b', ms=7, zorder=4)
        if wall < 90:
            ax.plot([min(wall, 62)], [i], '^', color='#e67e22', ms=8, zorder=4)
        ax.plot([min(top, 62)], [i], '*', color='#7f8c8d', ms=10, zorder=4)
        ax.text(-1, i, '%s  (%s MB/frame)' % (lab, '%.1f' % bpf if bpf >= 0.1 else '< 0.1'), ha='right', va='center', fontsize=8.8)
        if lo < lim:
            ax.text(min(T7 / bpf, 62), i + 0.33, 'T7 %.0f' % (T7 / bpf), ha='center', fontsize=7, color='#17a589')
    ax.axvline(62.5, color='#999', lw=0.8)
    ax.text(62.3, len(rows) - 0.45, 'beyond 62: off scale', fontsize=7, color='#777', ha='right')
    ax.set_xlim(0, 118)
    ax.set_xticks(range(0, 61, 10))
    ax.set_ylim(-0.8, len(rows) - 0.2)
    ax.set_yticks([])
    ax.set_xlabel('frames per second')
    ax.set_title('Where each mode hits a wall, and how long it records: storage walls = drive MB/s / frame size; CPU walls measured', fontsize=12)
    from matplotlib.lines import Line2D
    h = [Line2D([], [], marker='*', color='#7f8c8d', ls='', ms=10, label='sensor top'),
         Line2D([], [], marker='|', color='#2471a3', ls='', ms=12, mew=2, label='NVMe cold (%d MB/s)' % NVME_COLD),
         Line2D([], [], marker='D', color='#2471a3', ls='', label='NVMe warm (%d MB/s)' % NVME_WARM),
         Line2D([], [], marker='v', color='#c0392b', ls='', label='NVMe after 10 min (~%d MB/s, pauses)' % NVME_PAUSING),
         Line2D([], [], marker='s', color='#17a589', ls='', label='T7 SSD (%d MB/s)' % T7),
         Line2D([], [], marker='^', color='#e67e22', ls='', label='CPU wall: back end / encoder (measured)'),
         Line2D([], [], marker='o', color='black', ls='', label='the limit on NVMe (lowest wall)'),
         plt.Rectangle((0, 0), 1, 1, fc='#17a589', alpha=0.25, label='30 min probable (green) or passed (dark green, measured)')]
    ax.legend(handles=h, fontsize=8, loc='upper center', bbox_to_anchor=(0.45, -0.06), ncol=4, framealpha=0.95)
    ax.grid(axis='x', alpha=0.3)
    fig.subplots_adjust(left=0.27)
    fig.savefig(out + '/fig4-walls.png', dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)


def fig_survival(takes, out):
    fig, ax = plt.subplots(figsize=(11, 5))
    for mode, comp, col, name in (('4kHDR16', 'unc', '#c0392b', '4K HDR16 uncompressed'),
                                  ('4kSDR12', 'unc', '#2471a3', '4K SDR12 uncompressed')):
        xs = [t for t in takes if t['mode'] == mode and t['comp'] == comp and not t['log'] and t['fmt'] == 'cdng'
              and t['dur'] >= 150 and not t['tdn']]
        for t in xs:
            if t['ev_t'] is None:
                ax.plot(t['fps'], t['dur'] / 60, '^', color=col, ms=9, mfc='white', mew=2)
            else:
                ax.plot(t['fps'], (t['ev_t'] - t['series'][0]['t']) / 60, 'X', color=col, ms=9)
        ax.plot([], [], 's', color=col, label=name)
    ax.plot([], [], '^', color='#444', mfc='white', mew=2, label='clean for the whole take (open = could have gone on)')
    ax.plot([], [], 'X', color='#444', label='first event (buffer > 50 % or a drop)')
    ax.axhline(30, color='#555', ls=':')
    ax.text(23.2, 30.5, '30-min target', fontsize=8.5, color='#555')
    ax.set_xlabel('frames per second')
    ax.set_ylabel('minutes until the first event')
    ax.set_title('How long a 4K uncompressed take lasts on the NVMe: the cliff is about 1 fps wide')
    ax.legend(fontsize=8.5, loc='upper right')
    ax.grid(alpha=0.3)
    ax.set_ylim(0, 32)
    fig.tight_layout()
    fig.savefig(out + '/fig5-survival.png', dpi=150, facecolor='white')
    plt.close(fig)


# flows at the recommended fps (MB/s; measured on the NVMe unless marked derived)
FLOWS = [('4K SDR12 unc 37', 459, ''), ('4K HDR16 unc 27', 447, ''), ('4K HDR16 unc 25', 414, ''),
         ('4K HDR16 unc + Log 25', 307, ''), ('4K SDR12 lossless 40', 230, ' (derived)'),
         ('2K SDR12 unc 60', 187, ''), ('4K SDR12 lossy 3:1 37', 130, ' (derived)'), ('4K ProRes HQ 27', 122, '')]
BUF_MB, PAUSE_S = 1060, 2.0


def fig_flow(out):
    fig, (a, b) = plt.subplots(1, 2, figsize=(14, 5.8), gridspec_kw=dict(width_ratios=[1.35, 1]))
    m = [x / 10 for x in range(0, 301)]
    hole = [NVME_COLD - (NVME_COLD - NVME_WARM) * min(t / 3, 1) for t in m]
    a.fill_between(m, hole, 620, color='#2471a3', alpha=0.07)
    a.plot(m, hole, color='#2471a3', lw=2.2, label='NVMe hole: what the drive takes, cold -> warm')
    a.axhline(T7, color='#17a589', lw=2.2, label='T7 SSD hole (~%d MB/s)' % T7)
    cm = plt.get_cmap('tab10')
    for i, (lab, f, note) in enumerate(FLOWS):
        col = cm(i)
        t265, t375 = 265e3 / f / 60, 375e3 / f / 60
        a.plot([0, 30], [f, f], color=col, lw=1.6)
        a.plot([min(t265, 30), min(t375, 30)], [f, f], color='#c0392b', lw=5, alpha=0.55, solid_capstyle='butt')
        a.text(30.3, f, '%s%s: %d MB/s' % (lab, note, f), va='center', fontsize=7.8, color=col)
    a.plot([], [], color='#c0392b', lw=5, alpha=0.55, label='265-375 GB written: where the pauses began at 414-472 MB/s\n(at lower flows unconfirmed: the drive may stay cool enough)')
    a.set_xlim(0, 30)
    a.set_ylim(0, 620)
    a.set_xlabel('minutes into the take')
    a.set_ylabel('MB/s')
    a.set_title('Flow (fps x frame size) against the hole (what the drive takes)')
    a.legend(fontsize=7.8, loc='lower left', framealpha=0.95)
    a.grid(alpha=0.3)
    fl = list(range(20, 465, 5))
    drain = [f * PAUSE_S / (NVME_WARM - f) for f in fl]
    b.plot(fl, drain, color='#2471a3', lw=2)
    b.set_yscale('log')
    b.set_xlabel('flow, MB/s (warm NVMe hole %d MB/s)' % NVME_WARM)
    b.set_ylabel('seconds to drain one 2-s pause from the buffer')
    b.set_title('Headroom: a 2-s pause parks flow x 2 s in RAM;\nhole - flow has to empty it before the next pause', fontsize=11)
    for lab, f, _n in FLOWS:
        if f < NVME_WARM:
            d = f * PAUSE_S / (NVME_WARM - f)
            b.plot([f], [d], 'o', color='black', ms=5)
            b.text(f - 6, d * 1.15, lab, fontsize=7.2, ha='right')
    b.axvline(BUF_MB / PAUSE_S, color='#c0392b', ls=':')
    b.text(BUF_MB / PAUSE_S - 4, 0.3, 'above %d MB/s one 2-s pause\nalone overfills the 1.06 GB' % (BUF_MB / PAUSE_S),
           fontsize=7.5, color='#c0392b', ha='right')
    b.grid(alpha=0.3, which='both')
    fig.tight_layout()
    fig.savefig(out + '/fig6-flow-and-hole.png', dpi=150, facecolor='white')
    plt.close(fig)


ANCHORS = [('4kHDR16:cdng:unc', 28, 'back end: 4K HDR16 unc at 28 fps', 'delivered_fps'),
           ('4kHDR16:cdng:lj', 25, 'encoder: 4K HDR16 lossless at 25 fps', 'delivered_fps'),
           ('4kSDR12:cdng:unc', 60, 'storage: 4K SDR12 unc at 60 fps', 'delivered_fps')]
LEVERS = [('tdn', 'TDN on'), ('lock', 'phase lock on'), ('web', 'WebUI client on'), ('audio', 'audio on'),
          ('aids', 'preview aids on')]


def fig_levers(probes, out):
    import ast
    fig, axs = plt.subplots(1, 3, figsize=(14, 4.6), sharey=False)
    rows = []
    for ax, (spec, fps, title, key) in zip(axs, ANCHORS):
        ps = [p for p in probes if p.get('block') == 'P2' and p['spec'] == spec and p['fps'] == fps and p.get(key) is not None]
        for p in ps:
            if isinstance(p['levers'], str):
                p['levers'] = ast.literal_eval(p['levers'])
        effs = []
        for lv, name in LEVERS:
            on = [p[key] for p in ps if p['levers'].get(lv)]
            off = [p[key] for p in ps if not p['levers'].get(lv)]
            g_on = [p.get('gaps_per_min') or 0 for p in ps if p['levers'].get(lv)]
            g_off = [p.get('gaps_per_min') or 0 for p in ps if not p['levers'].get(lv)]
            if on and off:
                effs.append((name, st.mean(on) - st.mean(off), st.mean(g_on) - st.mean(g_off)))
                rows.append((title, name, st.mean(on) - st.mean(off), st.mean(g_on) - st.mean(g_off), len(on), len(off)))
        y = range(len(effs))
        ax.barh(list(y), [e[1] for e in effs], color=['#c0392b' if e[1] < 0 else '#17a589' for e in effs])
        ax.set_yticks(list(y))
        ax.set_yticklabels([e[0] for e in effs], fontsize=9)
        ax.invert_yaxis()
        ax.axvline(0, color='#333', lw=0.8)
        for i, e in enumerate(effs):
            ax.text(0.98, i, '%+.1f fps\n%+.0f gaps/min' % (e[1], e[2]), va='center', fontsize=7.6, ha='right',
                    transform=ax.get_yaxis_transform())
        lim = max(abs(e[1]) for e in effs) * 1.25 + 0.3
        ax.set_xlim(-lim, lim * 1.9)
        ax.set_title(title + '\n(%d probes, n on = n off)' % len(ps), fontsize=9.5)
        ax.set_xlabel('delivered fps, lever on minus off')
        ax.grid(axis='x', alpha=0.3)
    fig.suptitle('What each lever does to the three walls (P2, raw means of the 60-s probes)', fontsize=12)
    fig.tight_layout()
    fig.savefig(out + '/fig7-levers.png', dpi=150, facecolor='white')
    plt.close(fig)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--run', default=os.path.join(HERE, '../../nvme-campaign/run-20261110'))
    ap.add_argument('--out', default=os.path.join(HERE, '../figures'))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    takes = [t for t in (take_stats(f) for f in sorted(glob.glob(a.run + '/samples/*.csv'))) if t]
    probes = []
    for f in glob.glob(a.run + '/est*/probes.jsonl') + glob.glob(a.run + '/est*/validation.jsonl'):
        probes += [json.loads(line) for line in open(f) if line.strip()]
    fig_pipeline(a.out)
    fig_warming(takes, a.out)
    fig_long(takes, a.out)
    fig_walls(probes, a.out)
    fig_flow(a.out)
    lev = fig_levers(probes, a.out)
    # per-family warming numbers
    lines = ['| Mode group | Takes | Write rate MB/s | Rise in first 60 s °C | Peak °C (takes >= 3 min) |', '| --- | --- | --- | --- | --- |']
    for fam in FAM_COL:
        xs = [t for t in takes if t['fam'] == fam]
        if not xs:
            continue
        lg = [t['tmax'] for t in xs if t['dur'] >= 170]
        lines.append('| %s | %d | %.0f-%.0f | %.1f (median) | %s |' % (
            fam, len(xs), min(t['mbps'] for t in xs), max(t['mbps'] for t in xs), st.median(t['rise60'] for t in xs),
            ('%.0f-%.0f' % (min(lg), max(lg))) if lg else '-'))
    lines += ['', '| Anchor | Lever | fps on - off | gaps/min on - off | n on / off |', '| --- | --- | --- | --- | --- |']
    lines += ['| %s | %s | %+.2f | %+.0f | %d / %d |' % r for r in lev]
    open(a.out + '/warming.md', 'w').write('\n'.join(lines) + '\n')
    print('\n'.join(lines))
    print(len(takes), 'takes')


if __name__ == '__main__':
    main()
