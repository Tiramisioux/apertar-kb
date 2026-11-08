#!/usr/bin/env python3
"""Simple results workbook for a long-take campaign: max fps per mode, compression and Log.

Usage: python3 make_results_xlsx.py LONGTAKES.DB OUT.xlsx

Sheets: Max fps (table + two charts), Minutes (longest clean take per fps, heat map), Takes (every take), Notes.
Values only, no formulas: nothing to recalculate. The full data stays in LONGTAKES.DB.
"""
import sqlite3
import sys

from openpyxl import Workbook
from openpyxl.chart import BarChart, Reference
from openpyxl.formatting.rule import ColorScaleRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

MODES = [('4kSDR12', '4K SDR 12-bit'), ('4kSDR10', '4K SDR 10-bit'), ('4kHDR12', '4K Clear HDR 12-bit'),
         ('2kSDR12', '2K SDR 12-bit'), ('2kSDR10', '2K SDR 10-bit'), ('2kHDR16', '2K Clear HDR 16-bit'),
         ('2kHDR12', '2K Clear HDR 12-bit')]
TIERS = [(5, 295), (10, 595), (20, 1195), (30, 1795)]
CLEAN = ('pass_5min', 'pass_10min', 'pass_20min', 'pass_30min', 'pass_drive_full', 'ab_clean')

HEAD = PatternFill('solid', fgColor='1F3A5F')
BAND = PatternFill('solid', fgColor='F2F5F9')
THIN = Side(style='thin', color='C9D1DC')
BOX = Border(top=THIN, bottom=THIN, left=THIN, right=THIN)


def variant_label(comp, log):
    c = 'lossless' if comp == 'lossless_jpeg' else 'uncompressed'
    return c + (' + Log' if log else '')


def load(db):
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    takes = [dict(r) for r in con.execute('select * from takes order by started')]
    stats = {}
    for r in con.execute("select take_id, k, v from stats where k in ('enqueued','peak_queue')"):
        stats.setdefault(r['take_id'], {})[r['k']] = float(str(r['v']).split('/')[0])
    return takes, stats


def drain(t, stats):
    s = stats.get(t['take_id'], {})
    enq, peak = s.get('enqueued'), s.get('peak_queue')
    if t['outcome'] != 'buffer_full' or not enq or peak is None or not t['fps']:
        return None
    return round(t['fps'] * (enq - peak) / enq, 1)


def file_mb(t):
    return round(t['gb_written'] * 1000.0 / t['files'], 2) if t['files'] and t['gb_written'] else None


def variants(takes):
    out = []
    for mode, mname in MODES:
        for comp in ('none', 'lossless_jpeg'):
            for log in (0, 1):
                rows = [t for t in takes if t['mode'] == mode and t['comp'] == comp and int(t['log']) == log
                        and t['outcome'] != 'skipped_unavailable']
                if rows:
                    out.append((mode, mname, comp, log, rows))
    return out


def summarise(mode, mname, comp, log, rows, stats):
    sizes = [file_mb(t) for t in rows if file_mb(t)]
    best = {}
    for minutes, secs in TIERS:
        ok = [t['fps'] for t in rows if t['seconds'] and ((t['outcome'] in CLEAN and t['seconds'] >= secs)
              or (t['outcome'] == 'buffer_full' and t['seconds'] >= minutes * 60))]
        best[minutes] = int(max(ok)) if ok else None
    tried = sorted({int(t['fps']) for t in rows if t['fps']})
    longest = max((t['seconds'] or 0) for t in rows)
    drains = [d for d in (drain(t, stats) for t in rows) if d]
    cpu = [t['core_cpu_avg'] for t in rows if t.get('core_cpu_avg')]
    return dict(mode=mode, mname=mname, variant=variant_label(comp, log), file=round(sum(sizes) / len(sizes), 2) if sizes else None,
                best=best, tried=tried, longest=longest, drain=(min(drains), max(drains)) if drains else None,
                cpu=round(sum(cpu) / len(cpu)) if cpu else None, takes=len(rows))


def note_for(s):
    if s['best'][5] is None:
        if s['longest'] < 60:
            n = 'stops within %d s at %d fps' % (round(s['longest']), min(s['tried']))
        else:
            n = 'longest clean %.1f min' % (s['longest'] / 60)
        if s['drain']:
            lo, hi = s['drain']
            n += '; the drive kept up with only %s fps' % ('%.0f' % lo if round(lo) == round(hi) else '%.0f-%.0f' % (lo, hi))
        return n
    if s['best'][30] is None and s['best'][10] is None:
        return 'held 5 min, not 10 min'
    return ''


def style_header(ws, row, ncol):
    for c in range(1, ncol + 1):
        cell = ws.cell(row=row, column=c)
        cell.font = Font(bold=True, color='FFFFFF')
        cell.fill = HEAD
        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        cell.border = BOX


def build(db, out):
    takes, stats = load(db)
    summ = [summarise(*v, stats) for v in variants(takes)]
    extra_notes = {
        ('2kSDR12', 'uncompressed'): 'only the 5-min round (35 fps trim on, 37 trim off): lossless did better and went on',
        ('4kSDR10', 'lossless'): 'unreliable: 25 fps held 5 min once, then stopped after 4.3 min and after 12 s; 26 fps held 2 min in all 24 A/B takes',
        ('2kHDR16', 'uncompressed'): '27 fps held 5 min once, then stopped after 59 s',
        ('2kHDR16', 'uncompressed + Log'): 'Log stores 16-bit as 12: files 25% smaller',
        ('2kHDR12', 'uncompressed + Log'): 'Log does not shrink 12-bit files: same result as without',
    }

    wb = Workbook()
    ws = wb.active
    ws.title = 'Max fps'
    ws['A1'] = 'Highest clean fps per mode, compression and Log (USB SSD, 30-min target, floor 25 fps)'
    ws['A1'].font = Font(bold=True, size=14)
    ws['A2'] = 'Clean = no dropped frame and no buffer full for at least that long. Empty = not reached at 25 fps or more.'
    ws['A2'].font = Font(italic=True, color='555555')
    hdr = ['Mode', 'Variant', 'File MB', '5 min', '10 min', '20 min', '30 min', 'Takes', 'Note']
    for i, h in enumerate(hdr, 1):
        ws.cell(row=4, column=i, value=h)
    style_header(ws, 4, len(hdr))
    r = 5
    for s in summ:
        vals = [s['mname'], s['variant'], s['file'], s['best'][5], s['best'][10], s['best'][20], s['best'][30], s['takes'],
                extra_notes.get((s['mode'], s['variant'])) or note_for(s)]
        for i, v in enumerate(vals, 1):
            c = ws.cell(row=r, column=i, value=v)
            c.border = BOX
            if (r % 2) == 0:
                c.fill = BAND
            if 3 <= i <= 8:
                c.alignment = Alignment(horizontal='center')
        ws.cell(row=r, column=7).font = Font(bold=True)
        r += 1
    last = r - 1
    ws.cell(row=r, column=1, value='4K Clear HDR 16-bit').border = BOX
    ws.cell(row=r, column=2, value='all').border = BOX
    ws.cell(row=r, column=9, value='not run: 16.6 MB files, beyond what the SSD can write at 25 fps').border = BOX
    r += 1
    ws.cell(row=r, column=1, value='4K Clear HDR 12-bit').border = BOX
    ws.cell(row=r, column=2, value='uncompressed').border = BOX
    ws.cell(row=r, column=9, value='not run: 12.4 MB files, beyond the SSD (4K SDR 12-bit with the same size stopped in 20 s)').border = BOX
    for col, w in zip('ABCDEFGHI', (20, 22, 9, 7, 7, 7, 7, 7, 90)):
        ws.column_dimensions[col].width = w
    ws.freeze_panes = 'C5'

    # label column for charts: "mode · variant"
    for i in range(5, last + 1):
        ws.cell(row=i, column=11, value='%s · %s' % (ws.cell(row=i, column=1).value, ws.cell(row=i, column=2).value))
    ws.column_dimensions['K'].hidden = True

    ch = BarChart()
    ch.type = 'bar'
    ch.title = 'Highest clean fps: 5 min and 30 min'
    ch.y_axis.title = 'fps'
    ch.y_axis.scaling.min = 0
    ch.y_axis.scaling.max = 65
    ch.add_data(Reference(ws, min_col=4, min_row=4, max_row=last), titles_from_data=True)
    ch.add_data(Reference(ws, min_col=7, min_row=4, max_row=last), titles_from_data=True)
    ch.set_categories(Reference(ws, min_col=11, min_row=5, max_row=last))
    ch.series[0].graphicalProperties.solidFill = '9DB7D5'
    ch.series[1].graphicalProperties.solidFill = '1F3A5F'
    ch.x_axis.scaling.orientation = 'maxMin'
    ch.height, ch.width = 11, 22
    ch.gapWidth = 60
    ws.add_chart(ch, 'A%d' % (r + 3))

    ch2 = BarChart()
    ch2.type = 'bar'
    ch2.title = 'File size per frame (MB)'
    ch2.add_data(Reference(ws, min_col=3, min_row=4, max_row=last), titles_from_data=True)
    ch2.set_categories(Reference(ws, min_col=11, min_row=5, max_row=last))
    ch2.series[0].graphicalProperties.solidFill = 'C8873A'
    ch2.x_axis.scaling.orientation = 'maxMin'
    ch2.legend = None
    ch2.height, ch2.width = 11, 16
    ch2.gapWidth = 60
    ws.add_chart(ch2, 'H%d' % (r + 3))

    # Minutes: longest clean take per variant and fps
    wm = wb.create_sheet('Minutes')
    wm['A1'] = 'Longest clean take (minutes) per fps'
    wm['A1'].font = Font(bold=True, size=14)
    wm['A2'] = 'Bold = the take ended at the round\'s time limit (the true limit is longer). Others ended at buffer full.'
    wm['A2'].font = Font(italic=True, color='555555')
    fps_all = sorted({int(t['fps']) for t in takes if t['fps'] and t['outcome'] != 'skipped_unavailable'})
    wm.cell(row=4, column=1, value='Mode')
    wm.cell(row=4, column=2, value='Variant')
    for j, f in enumerate(fps_all):
        wm.cell(row=4, column=3 + j, value=f)
    style_header(wm, 4, 2 + len(fps_all))
    rr = 5
    for mode, mname, comp, log, rows in variants(takes):
        wm.cell(row=rr, column=1, value=mname)
        wm.cell(row=rr, column=2, value=variant_label(comp, log))
        for j, f in enumerate(fps_all):
            at = [t for t in rows if t['fps'] and int(t['fps']) == f and t['seconds']]
            if not at:
                continue
            t = max(at, key=lambda x: x['seconds'])
            c = wm.cell(row=rr, column=3 + j, value=round(t['seconds'] / 60.0, 1))
            c.alignment = Alignment(horizontal='center')
            c.number_format = '0.0'
            if t['outcome'] in CLEAN:
                c.font = Font(bold=True)
        for c in range(1, 3 + len(fps_all)):
            wm.cell(row=rr, column=c).border = BOX
        rr += 1
    end_col = wm.cell(row=4, column=2 + len(fps_all)).column_letter
    wm.conditional_formatting.add('C5:%s%d' % (end_col, rr - 1),
                                  ColorScaleRule(start_type='num', start_value=0, start_color='F4CCCC',
                                                 mid_type='num', mid_value=10, mid_color='FFF2CC',
                                                 end_type='num', end_value=30, end_color='B6D7A8'))
    wm.column_dimensions['A'].width = 20
    wm.column_dimensions['B'].width = 22
    for j in range(len(fps_all)):
        wm.column_dimensions[wm.cell(row=4, column=3 + j).column_letter].width = 5.5
    wm.freeze_panes = 'C5'

    # Takes
    wt = wb.create_sheet('Takes')
    th = ['Started', 'Mode', 'Variant', 'fps', 'Outcome', 'Minutes', 'File MB', 'Drive kept up (fps)', 'Round', 'Pi max C',
          'Core CPU avg %', 'Take id']
    for i, h in enumerate(th, 1):
        wt.cell(row=1, column=i, value=h)
    style_header(wt, 1, len(th))
    mname = dict(MODES)
    for i, t in enumerate(takes, 2):
        vals = [t['started'], mname.get(t['mode'], t['mode']), variant_label(t['comp'], int(t['log'])), t['fps'], t['outcome'],
                round(t['seconds'] / 60.0, 1) if t['seconds'] else None, file_mb(t), drain(t, stats), t['variant'] or 'edge',
                t['pi_c_max'], round(t['core_cpu_avg']) if t.get('core_cpu_avg') else None, t['take_id']]
        for j, v in enumerate(vals, 1):
            wt.cell(row=i, column=j, value=v)
    for col, w in zip('ABCDEFGHIJKL', (18, 20, 22, 6, 18, 8, 8, 10, 11, 8, 10, 58)):
        wt.column_dimensions[col].width = w
    wt.auto_filter.ref = 'A1:L%d' % (len(takes) + 1)
    wt.freeze_panes = 'A2'

    # Notes
    wn = wb.create_sheet('Notes')
    lines = [
        ('How to read', True),
        ('Max fps: the highest fps that stayed clean for 5, 10, 20 and 30 minutes. A take stops at the first dropped frame, at buffer full (Core\'s 90% RAM safety stop) or at the round\'s limit.', False),
        ('Minutes: for each fps the longest take seen. Use it to answer "how long can I record at this fps".', False),
        ('Round: edge = first 5-min search; tier10/20/30 = survivors re-run longer; logt* = the Log follow-up; base, workers2 ... kerneltune = storage-tuning A/B (2 min).', False),
        ('', False),
        ('What else was found', True),
        ('Storage tuning A/B (workers 2/6, queue 24/48, sync 500/2000 ms, CineMate kernel dirty tuning): no variant changed any result.', False),
        ('Preview TDN, phase lock and WebUI were ruled out in theory: every limit was the drive, and these do not change what is written. Trim off: 2 takes, no visible effect.', False),
        ('Log is applied only to 16-bit Clear HDR streams. In SDR modes Core records linear ("cannot be mapped on the copy worker").', False),
        ('No take stopped on a dropped frame (two passes are one file short of 45,000 and 30,000, no Core drop counter moved): every stop was buffer full, so the drive (or the lossless encoder at 4K) was the limit. No throttling, Pi at most 62 C.', False),
        ('', False),
        ('Data', True),
        ('Every take, the per-second samples, drop events, Core counters and journal lines: tests-2026-11/longtakes-ssd-2026-11-07/longtakes.db (SQLite).', False),
    ]
    for i, (txt, bold) in enumerate(lines, 1):
        c = wn.cell(row=i, column=1, value=txt)
        c.font = Font(bold=bold, size=12 if bold else 11)
        c.alignment = Alignment(wrap_text=True, vertical='top')
    wn.column_dimensions['A'].width = 130

    from openpyxl.worksheet.properties import PageSetupProperties
    for w in wb.worksheets:
        w.page_setup.orientation = 'landscape'
        w.page_setup.fitToWidth, w.page_setup.fitToHeight = 1, 0
        w.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)
    wb.save(out)


if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    build(sys.argv[1], sys.argv[2])
