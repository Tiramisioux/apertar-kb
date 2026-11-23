"""The two storage columns of the Core limits table as one infographic (figures/fig8-storage-limits.png).

Reads the cells straight from Apertar-Core src/camera/SustainedFps.hpp, so the picture is the table Core uses.
The fps axis starts at 25 (the lowest rate a take is shot at here); a limit under 25 is written in the left margin.
Usage: python storage_limits.py [path/to/SustainedFps.hpp]
"""
import math
import os
import re
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

HERE = os.path.dirname(os.path.abspath(__file__))
HPP = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser('~/Documents/Apertar/Apertar-Core/src/camera/SustainedFps.hpp')
OUT = os.path.join(HERE, '..', 'figures', 'fig8-storage-limits.png')

CELL = re.compile(r'\{\s*Kind::(Nvme|UsbSsd),\s*Board::Pi5,\s*(\d+),\s*(\d+),\s*(true|false),\s*(\d+),\s*(true|false),\s*'
                  r'"([a-z_]+)",\s*([\d.]+),\s*(\d+),\s*([\d.]+),\s*Label::(\w+)')
LABEL_COL = {'Measured': '#1f4e79', 'Derived': '#5b9bd5', 'Probable': '#a9c8e8', 'Unconfirmed': '#c9c9c9'}
COMP = {'none': 'uncompressed', 'lossless_jpeg': 'lossless'}
LO, HI = 25, 65

# The rows, best picture first (Dynamic resolution's order, with the Log rows beside their own mode).
ROWS = [((3840, 2160, True, 16, True), '4K Clear HDR 16-bit + Log'),
        ((3840, 2160, True, 16, False), '4K Clear HDR 16-bit'),
        ((3840, 2160, True, 12, False), '4K Clear HDR 12-bit'),
        ((3840, 2160, False, 12, False), '4K SDR 12-bit'),
        ((3840, 2160, False, 12, True), '4K SDR 12-bit + Log'),
        ((2880, 2160, False, 12, False), '2880x2160 SDR 12-bit'),
        ((3840, 2160, False, 10, False), '4K SDR 10-bit'),
        ((3840, 2160, False, 10, True), '4K SDR 10-bit + Log'),
        ((1920, 1080, True, 16, False), '2K Clear HDR 16-bit'),
        ((1920, 1080, False, 12, False), '2K SDR 12-bit'),
        ((1920, 1080, False, 10, False), '2K SDR 10-bit')]


def step_down(fps):
    f = fps + 1e-9
    if f < 25: return math.floor(f) if f > 0 else 0
    if f < 30: return 25
    if f < 33: return 30
    if f < 50: return 33
    if f < 60: return 50
    return math.floor(f / 10) * 10


def cells():
    out = {}
    for m in CELL.finditer(open(HPP).read()):
        kind, w, h, hdr, bits, log, comp, fps, mins, short, label = m.groups()
        out[(kind, (int(w), int(h), hdr == 'true', int(bits), log == 'true'))] = (float(fps), int(mins), float(short), label, comp)
    return out


def panel(ax, table, kind, title):
    ax.set_title(title, loc='left', fontsize=12, fontweight='bold', pad=10)
    ax.set_xlim(LO, HI)
    ax.set_ylim(len(ROWS) - 0.4, -0.6)
    ax.set_yticks(range(len(ROWS)))
    ax.set_yticklabels([name for _, name in ROWS], fontsize=9.5)
    ax.set_xticks([25, 30, 33, 40, 50, 60])
    ax.grid(axis='x', color='#e6e6e6', zorder=0)
    for side in ('top', 'right', 'left'):
        ax.spines[side].set_visible(False)
    ax.tick_params(axis='y', length=0)
    ax.set_xlabel('fps held clean (steps 25 / 30 / 33 / 50 / 60 marked)', fontsize=9)
    for y, (key, _) in enumerate(ROWS):
        cell = table.get((kind, key))
        if cell is None:
            ax.text(LO + 0.4, y, 'no cell: not measured on this drive', va='center', fontsize=8.5, color='#999999', style='italic')
            continue
        fps, mins, short, label, comp = cell
        col = LABEL_COL[label]
        what = COMP.get(comp, comp) if not key[4] else ''
        length = f'{mins} min' if label == 'Measured' else label.lower()
        if fps <= 0:
            ax.text(LO + 0.4, y, f'not used: drops frames at every fps tried (30-40){"" if label == "Measured" else ", " + label.lower()}',
                    va='center', fontsize=8.5, color='#b03a2e', fontweight='bold')
            continue
        if fps < LO:
            ax.text(LO + 0.4, y, f'under 25: {fps:g} fps, {length}' + (f', {what}' if what else ''),
                    va='center', fontsize=8.5, color=col if label != 'Unconfirmed' else '#666666', fontweight='bold')
            if short >= LO:
                ax.barh(y, short - LO, left=LO, height=0.18, color=col, alpha=0.35, zorder=2)
                ax.text(short + 0.4, y + 0.28, f'{short:g} fps up to 8 min', va='center', fontsize=7.5, color='#555555')
            continue
        shown = min(fps, HI)
        if shown - LO < 1:
            ax.plot([LO + 0.15], [y], marker='o', ms=11, color=col, zorder=3, clip_on=False)
            ax.text(LO + 0.9, y, f'{fps:g} fps, {length}' + (f', {what}' if what else ''), va='center', fontsize=8.5,
                    color='#222222')
            continue
        ax.barh(y, shown - LO, left=LO, height=0.6, color=col, zorder=2,
                hatch='//' if label == 'Unconfirmed' else None, edgecolor='white' if label != 'Unconfirmed' else '#999999')
        step = step_down(fps)
        if step < fps:
            ax.plot([step, step], [y - 0.3, y + 0.3], color='white', lw=2.2, zorder=3)
        txt = f'{fps:g} fps, {length}' + (f', {what}' if what else '') + (f'  (step {step:g})' if step != fps else '')
        inside = shown - LO > 22
        ax.text(shown - 0.5 if inside else shown + 0.5, y, txt, va='center', ha='right' if inside else 'left', fontsize=8.5,
                color='white' if inside and label in ('Measured', 'Derived') else '#222222', zorder=4)


def main():
    table = cells()
    assert table, 'no cells parsed from ' + HPP
    fig, axes = plt.subplots(1, 2, figsize=(15, 6.6), sharey=True)
    panel(axes[0], table, 'Nvme', 'NVMe card (Corsair MP600 Mini, CFexpress hat), hot drive')
    panel(axes[1], table, 'UsbSsd', 'USB SSD (Samsung T7, about 105 MB/s in takes)')
    fig.legend(handles=[Patch(color=c, label=l.lower()) for l, c in LABEL_COL.items()] +
               [Patch(facecolor='none', edgecolor='none', label='white line: the step Core rounds down to')],
               loc='lower center', ncol=5, frameon=False, fontsize=9)
    fig.suptitle('Sustained fps per mode and storage: the limits Core uses (IMX585, Pi 5, cDNG, reference levers, split on)',
                 fontsize=13, x=0.01, ha='left')
    fig.tight_layout(rect=(0, 0.06, 1, 0.95))
    fig.savefig(OUT, dpi=150)
    print('wrote', os.path.normpath(OUT), len(table), 'cells')


if __name__ == '__main__':
    main()
