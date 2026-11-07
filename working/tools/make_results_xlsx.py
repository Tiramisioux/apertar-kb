import sqlite3, json, collections, datetime
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.chart import BarChart, ScatterChart, Reference, Series
from openpyxl.chart.label import DataLabelList
from openpyxl.utils import get_column_letter as L

import sys
# usage: python3 make_results_xlsx.py LONGTAKES.DB SESSION.JSON OUT.xlsx  (copy the db from the Pi first; then open the file in Excel and
# let it recalculate, or run LibreOffice's recalc: the formulas have no cached values until then)
db = sqlite3.connect(sys.argv[1])
sess = json.load(open(sys.argv[2]))
OUT = sys.argv[3]

from openpyxl.chart.shapes import GraphicalProperties
PALETTE = ['1F3864', 'C00000', '2E75B6', 'ED7D31', '70AD47', '7030A0', '7F7F7F']
F = 'Arial'
f_norm = Font(name=F, size=10)
f_bold = Font(name=F, size=10, bold=True)
f_hdr = Font(name=F, size=10, bold=True, color='FFFFFF')
f_title = Font(name=F, size=16, bold=True, color='1F3864')
f_sub = Font(name=F, size=10, italic=True, color='595959')
f_input = Font(name=F, size=10, color='0000FF')
fill_hdr = PatternFill('solid', fgColor='1F3864')
fill_band = PatternFill('solid', fgColor='EEF3FA')
fill_note = PatternFill('solid', fgColor='FFF8E1')
thin = Side(style='thin', color='BFBFBF')
box = Border(left=thin, right=thin, top=thin, bottom=thin)

MODES = [('4kSDR12', '4K SDR 12-bit'), ('4kSDR10', '4K SDR 10-bit'), ('4kHDR12', '4K Clear HDR 12-bit'),
         ('2kSDR12', '2K SDR 12-bit'), ('2kSDR10', '2K SDR 10-bit'), ('2kHDR16', '2K Clear HDR 16-bit'),
         ('2kHDR12', '2K Clear HDR 12-bit')]


def config_label(comp, log, tdn, lock, trim, web):
    parts = ['lossless' if comp != 'none' else 'uncompressed']
    if log: parts.append('Log')
    if tdn: parts.append('TDN')
    if lock: parts.append('phase lock')
    if not trim: parts.append('trim off')
    if web: parts.append('WebUI client')
    return ' + '.join(parts)


rows = db.execute('''select take_id, mode, comp, log, tdn, lock, trim, web, fps, variant, outcome, seconds, dropped,
                            core_cpu_avg, core_cpu_max, core_top_thread, pi_c, fill_pct, started, drop_kinds, cfg_id,
                            files, gb_written
                     from takes order by started''').fetchall()
enq_peak = {}
for tid, k, v in db.execute("select take_id,k,v from stats where k in ('enqueued','peak_queue')"):
    enq_peak.setdefault(tid, {})[k] = v


def drain_est(tid, fps):
    d = enq_peak.get(tid, {})
    try:
        enq = int(d['enqueued']); pk = int(str(d['peak_queue']).split('/')[0])
        return round(fps * max(enq - pk, 0) / enq, 1) if enq >= 30 else None
    except (KeyError, ValueError, ZeroDivisionError):
        return None
peak = {}
for tid, k, v in db.execute("select take_id,k,v from stats where k in ('queue_bytes_peak','queue_budget')"):
    peak.setdefault(tid, {})[k] = v


def peak_pct(tid):
    d = peak.get(tid, {})
    try:
        return round(100.0 * float(d['queue_bytes_peak']) / float(d['queue_budget']), 1)
    except (KeyError, ValueError, ZeroDivisionError):
        return None


wb = Workbook()

# ------------------------------------------------------------------ Takes (data sheet)
wt = wb.active
wt.title = 'Takes'
hdr = ['Take', 'Mode', 'Config', 'Log', 'Fps', 'Round', 'Tier (min)', 'Variant', 'Outcome', 'Pass', 'Seconds', 'Dropped',
       'Queue peak %', 'Core CPU avg %', 'Core CPU max %', 'Busiest thread', 'Pi C', 'Drive fill %', 'Started', 'Baseline', 'Key',
       'Avg file (MB)', 'Drain est (fps)']
for j, h in enumerate(hdr, 1):
    c = wt.cell(row=1, column=j, value=h)
    c.font, c.fill, c.alignment, c.border = f_hdr, fill_hdr, Alignment(horizontal='center', vertical='center', wrap_text=True), box
ab_names = {'base', 'workers2', 'workers6', 'queue24', 'queue48', 'sync500', 'sync2000', 'kerneltune'}
for i, r in enumerate(rows, 2):
    (tid, mode, comp, log, tdn, lock, trim, web, fps, variant, outcome, secs, dropped, cavg, cmax, cthr, pic, fill, started,
     kinds, cfg, nfiles, gbw) = r
    variant = variant or ''
    rnd = ('A/B tuning' if variant in ab_names else
           {'tier10': '10 min', 'tier20': '20 min', 'tier30': '30 min', 'logt10': '10 min (Log)', 'logt20': '20 min (Log)',
            'logt30': '30 min (Log)'}.get(variant, '5 min walk'))
    vals = [tid, mode, config_label(comp, log, tdn, lock, trim, web), int(log), fps, rnd, None, variant, outcome, None, secs,
            dropped, peak_pct(tid), cavg, cmax, cthr, pic, fill, started, None, None,
            round(gbw * 1000.0 / nfiles, 2) if (nfiles and gbw) else None, drain_est(tid, fps) if outcome == 'buffer_full' else None]
    for j, v in enumerate(vals, 1):
        c = wt.cell(row=i, column=j, value=v)
        c.font = f_norm
    # formulas: tier, pass, baseline flag, lookup key
    wt.cell(row=i, column=7, value=f'=IF(OR(H{i}="tier10",H{i}="logt10"),10,IF(OR(H{i}="tier20",H{i}="logt20"),20,'
                                    f'IF(OR(H{i}="tier30",H{i}="logt30"),30,IF(H{i}="",5,0))))').font = f_norm
    wt.cell(row=i, column=10, value=f'=IF(OR(LEFT(I{i},4)="pass",I{i}="ab_clean"),1,0)').font = f_norm
    wt.cell(row=i, column=20, value=f'=IF(AND(C{i}="uncompressed",D{i}=0),1,0)').font = f_norm
    wt.cell(row=i, column=21, value=f'=B{i}&"|"&G{i}&"|"&E{i}&"|"&J{i}&"|"&D{i}').font = f_norm
    wt.cell(row=i, column=5).number_format = '0'
    wt.cell(row=i, column=11).number_format = '0'
    for col in (13, 14, 15, 17, 18, 22, 23):
        wt.cell(row=i, column=col).number_format = '0.0'
N = len(rows) + 1
for j, w in enumerate([34, 10, 30, 6, 6, 14, 9, 11, 20, 6, 9, 8, 10, 10, 10, 16, 7, 9, 19, 9, 26, 11, 11], 1):
    wt.column_dimensions[L(j)].width = w
wt.row_dimensions[1].height = 32
wt.freeze_panes = 'C2'
wt.auto_filter.ref = f'A1:{L(len(hdr))}{N}'


def rng(col):
    return f'Takes!${col}$2:${col}${N}'


MODE_COL, CFG_COL, LOG_COL, FPS_COL, TIER_COL, PASS_COL, SEC_COL, BASE_COL, KEY_COL, OUTC = (
    rng('B'), rng('C'), rng('D'), rng('E'), rng('G'), rng('J'), rng('K'), rng('T'), rng('U'), rng('I'))


def style_table(ws, r0, r1, c0, c1, band=True):
    for r in range(r0, r1 + 1):
        for c in range(c0, c1 + 1):
            cell = ws.cell(row=r, column=c)
            cell.border = box
            if not cell.font or cell.font.name != F:
                cell.font = f_norm
            if band and r > r0 and (r - r0) % 2 == 0:
                cell.fill = fill_band


def header_row(ws, r, c0, labels):
    for j, h in enumerate(labels):
        c = ws.cell(row=r, column=c0 + j, value=h)
        c.font, c.fill, c.border = f_hdr, fill_hdr, box
        c.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)


# ------------------------------------------------------------------ Summary
ws = wb.create_sheet('Summary', 0)
ws.sheet_view.showGridLines = False
ws['A1'] = 'Long-take campaign on the USB SSD: results so far'
ws['A1'].font = f_title
snap = db.execute('select max(started) from takes').fetchone()[0]
ws['A2'] = (f"Snapshot of {datetime.date(2026, 11, 7)} (last take {snap}); the Log follow-up is still running. "
            f"{sess['pi_model']} (rev {sess['pi_revision']}), {sess['drive']}, exFAT, 354 MB/s sustained write measured.")
ws['A2'].font = f_sub
ws['A4'] = 'Highest fps that stayed clean (no dropped frame, no buffer full) for a take of the given length, without Log. 0 / dash = none.'
ws['A4'].font = f_bold
header_row(ws, 5, 1, ['Mode', '5 min', '10 min', '20 min', '30 min', 'Winning config at 30 min'])
ws.row_dimensions[5].height = 22
for i, (key, label) in enumerate(MODES, 6):
    ws.cell(row=i, column=1, value=label)
    ws.cell(row=i, column=8, value=key).font = Font(name=F, size=8, color='BFBFBF')     # hidden key column H
    for j, t in enumerate((5, 10, 20, 30), 2):
        ws.cell(row=i, column=j,
                value=f'=_xlfn.MAXIFS({FPS_COL},{MODE_COL},$H{i},{TIER_COL},{t},{PASS_COL},1,{LOG_COL},0)')
        ws.cell(row=i, column=j).number_format = '0;-0;"–"'
        ws.cell(row=i, column=j).alignment = Alignment(horizontal='center')
    ws.cell(row=i, column=6, value=f'=IF(E{i}=0,"none",INDEX({CFG_COL},MATCH($H{i}&"|30|"&E{i}&"|1|0",{KEY_COL},0)))')
style_table(ws, 5, 12, 1, 6)
ws['A13'] = 'Same, with Log on (stored as 12-bit in Clear HDR 16-bit, 10-bit in 12-bit modes). Only Clear HDR modes accept Log in this Core.'
ws['A13'].font = f_bold
header_row(ws, 14, 1, ['Mode', '5 min', '10 min', '20 min', '30 min', 'Result'])
for i, (key, label) in enumerate(MODES, 15):
    ws.cell(row=i, column=1, value=label)
    ws.cell(row=i, column=8, value=key).font = Font(name=F, size=8, color='BFBFBF')
    for j, t in enumerate((5, 10, 20, 30), 2):
        ws.cell(row=i, column=j,
                value=f'=_xlfn.MAXIFS({FPS_COL},{MODE_COL},$H{i},{TIER_COL},{t},{PASS_COL},1,{LOG_COL},1)')
        ws.cell(row=i, column=j).number_format = '0;-0;"–"'
        ws.cell(row=i, column=j).alignment = Alignment(horizontal='center')
    ws.cell(row=i, column=6, value=(
        f'=IF(COUNTIFS({MODE_COL},$H{i},{LOG_COL},1,{OUTC},"skipped_unavailable")>0,"Log not applied by Core (packed raw stream)",'
        f'IF(COUNTIFS({MODE_COL},$H{i},{LOG_COL},1)=0,"not tested yet",'
        f'IF(SUM(B{i}:E{i})=0,"tried, no clean fps at 25 or above","clean: see fps")))'))
style_table(ws, 14, 21, 1, 6)
ws['A23'] = 'Reading it'
ws['A23'].font = f_bold
notes = [
    '4K does not work on this SSD: 12 MB frames fill Core\'s RAM write buffer within seconds at 25 fps. Lossless came closest (4K SDR 10-bit held 25 fps for 5 min, failed at 10); Log did not apply in SDR and did not rescue Clear HDR 12-bit. See the sheet 4K Log and lossless.',
    'The limit is per file as well as per MB/s: about 19 ms of overhead per frame plus the file size at 345 MB/s (see the Model sheet).',
    'Lossless wins where it is allowed because it makes files smaller. Log helps 2K Clear HDR 16-bit (30 fps vs 26 fps at 30 min, so far at 10 min).',
    'Results drift by about 3 fps over hours (the same fps passed 20 min and later failed after 20 s), so read each number as plus or minus 3.',
]
for k, t in enumerate(notes, 24):
    ws.cell(row=k, column=1, value='- ' + t).font = f_norm
for col, w in zip('ABCDEFGH', [26, 9, 9, 9, 9, 44, 4, 14]):
    ws.column_dimensions[col].width = w
ws.column_dimensions['H'].hidden = True

ch = BarChart()
ch.type, ch.grouping = 'col', 'clustered'
ch.title = 'Highest clean fps by mode and take length (no Log)'
ch.y_axis.title, ch.x_axis.title = 'fps', None
ch.y_axis.scaling.min = 0
data = Reference(ws, min_col=2, max_col=5, min_row=5, max_row=12)
ch.add_data(data, titles_from_data=True)
ch.set_categories(Reference(ws, min_col=1, min_row=6, max_row=12))
ch.height, ch.width = 9.5, 20
ch.legend.position = 'r'
ch.y_axis.delete = False
ch.x_axis.delete = False
ws.add_chart(ch, 'J4')

ch2 = BarChart()
ch2.type, ch2.grouping = 'col', 'clustered'
ch2.title = 'With Log: highest clean fps (Clear HDR modes)'
ch2.y_axis.scaling.min = 0
ch2.add_data(Reference(ws, min_col=2, max_col=5, min_row=14, max_row=21), titles_from_data=True)
ch2.set_categories(Reference(ws, min_col=1, min_row=15, max_row=21))
ch2.height, ch2.width = 9.5, 20
ch2.legend.position = 'r'
ch2.y_axis.delete = False
ch2.x_axis.delete = False
ws.add_chart(ch2, 'J24')

# ------------------------------------------------------------------ Edge (time to stop vs fps, baseline walks)
we = wb.create_sheet('Edge')
we.sheet_view.showGridLines = False
we['A1'] = 'How long the plain baseline lasts at each fps it was tried at (5-minute walk)'
we['A1'].font = f_title
we['A2'] = ('Seconds until the take stopped (first drop or buffer full); 300 s = passed the 5-minute round. Baseline = uncompressed, Log off, '
            'no other switches. Only the (mode, fps) pairs that were tried are listed; the walk skips fps it can rule out.')
we['A2'].font = f_sub
header_row(we, 4, 1, ['Mode', 'fps', 'Seconds until stop', 'key'])
pairs = db.execute("""select mode, fps from takes where variant='' and comp='none' and log=0 and tdn=0 and lock=0 and trim=1 and web=0
                      group by mode, fps""").fetchall()
order = {k: n for n, (k, _) in enumerate(MODES)}
pairs = sorted(pairs, key=lambda t: (order.get(t[0], 99), t[1]))
r = 5
blocks = {}
for mk, fp in pairs:
    lab = dict(MODES)[mk]
    we.cell(row=r, column=1, value=lab)
    we.cell(row=r, column=2, value=int(fp)).font = f_input
    we.cell(row=r, column=3, value=f'=_xlfn.MAXIFS({SEC_COL},{MODE_COL},$D{r},{FPS_COL},$B{r},{BASE_COL},1,{TIER_COL},5)')
    we.cell(row=r, column=3).number_format = '0'
    we.cell(row=r, column=4, value=mk).font = Font(name=F, size=8, color='7F7F7F')
    blocks.setdefault(mk, [r, r])[1] = r
    r += 1
style_table(we, 4, r - 1, 1, 3)
for col, w in zip('ABCD', [24, 8, 18, 10]):
    we.column_dimensions[col].width = w
sc2 = ScatterChart()
sc2.title = 'Seconds before the baseline stopped, by fps'
sc2.style = 13
sc2.x_axis.title, sc2.y_axis.title = 'fps', 'seconds (300 = passed 5 min)'
sc2.y_axis.scaling.min, sc2.y_axis.scaling.max = 0, 320
for mk, lab in MODES:
    if mk not in blocks:
        continue
    r0, r1 = blocks[mk]
    se = Series(Reference(we, min_col=3, min_row=r0, max_row=r1), Reference(we, min_col=2, min_row=r0, max_row=r1), title=lab)
    col = PALETTE[len(sc2.series) % len(PALETTE)]
    se.marker.symbol, se.marker.size = 'circle', 9
    se.marker.graphicalProperties = GraphicalProperties(solidFill=col)
    se.marker.graphicalProperties.line.solidFill = col
    se.graphicalProperties = GraphicalProperties()
    se.graphicalProperties.line.solidFill = col
    se.graphicalProperties.line.width = 9525
    sc2.series.append(se)
sc2.height, sc2.width = 12, 24
sc2.legend.position = 'r'
sc2.y_axis.delete = False
sc2.x_axis.delete = False
sc2.x_axis.scaling.min = 24
sc2.x_axis.scaling.max = 61
we.add_chart(sc2, 'F4')

# ------------------------------------------------------------------ 4K: Log and lossless
w4 = wb.create_sheet('4K Log and lossless')
w4.sheet_view.showGridLines = False
w4['A1'] = '4K on the SSD: lossless and Log, every combination'
w4['A1'].font = f_title
w4['A2'] = ('Does a smaller file (lossless, or Log: 12 -> 10 bit in Clear HDR 12-bit) make 4K possible at 25 fps or above? '
            'Longest take = seconds before the take stopped; 300 s = passed the 5-minute round.')
w4['A2'].font = f_sub
header_row(w4, 4, 1, ['Mode', 'Config', 'Takes', 'Best clean fps, 5 min', 'Longest take at 25 fps (s), any round',
                      'Best clean fps, 10 min', 'Longest 10-min take (s)', 'Avg file (MB)', 'Frames the drive wrote per second at the stop (fps)',
                      'Status', 'label'])
w4.row_dimensions[4].height = 44
combos = [('uncompressed', 'uncompressed'), ('lossless', 'lossless'), ('uncompressed + Log', 'uncompressed + Log'),
          ('lossless + Log', 'lossless + Log')]
r = 5
rows4 = []
for key, label in (('4kSDR12', '4K SDR 12-bit'), ('4kSDR10', '4K SDR 10-bit'), ('4kHDR12', '4K Clear HDR 12-bit')):
    for cfg, cl in combos:
        w4.cell(row=r, column=1, value=label)
        w4.cell(row=r, column=2, value=cl)
        w4.cell(row=r, column=12, value=key).font = Font(name=F, size=8, color='BFBFBF')
        k = f'$L{r}'
        crit = f'{MODE_COL},{k},{CFG_COL},$B{r}'
        w4.cell(row=r, column=3, value=f'=COUNTIFS({crit},{OUTC},"<>skipped_unavailable")')
        w4.cell(row=r, column=4, value=f'=_xlfn.MAXIFS({FPS_COL},{crit},{TIER_COL},5,{PASS_COL},1)')
        w4.cell(row=r, column=5, value=f'=_xlfn.MAXIFS({SEC_COL},{crit},{FPS_COL},25)')
        w4.cell(row=r, column=6, value=f'=_xlfn.MAXIFS({FPS_COL},{crit},{TIER_COL},10,{PASS_COL},1)')
        w4.cell(row=r, column=7, value=f'=_xlfn.MAXIFS({SEC_COL},{crit},{TIER_COL},10)')
        w4.cell(row=r, column=8, value=f'=IFERROR(AVERAGEIFS({rng("V")},{crit},{OUTC},"<>skipped_unavailable"),0)')
        w4.cell(row=r, column=9, value=f'=IFERROR(AVERAGEIFS({rng("W")},{crit}),0)')
        w4.cell(row=r, column=8).number_format = '0.0;-0.0;"–"'
        w4.cell(row=r, column=9).number_format = '0.0;-0.0;"–"'
        w4.cell(row=r, column=8).alignment = Alignment(horizontal='center')
        w4.cell(row=r, column=9).alignment = Alignment(horizontal='center')
        w4.cell(row=r, column=10, value=(
            f'=IF(COUNTIFS({crit},{OUTC},"skipped_unavailable")>0,"Log not applied by Core (SDR raw stream is packed)",'
            f'IF(C{r}=0,"not run (ruled out: the same file size failed in another 4K mode)",'
            f'IF(D{r}=0,"no clean fps at 25 or above: buffer full",'
            f'IF(F{r}=0,"clean 5 min only, failed at 10 min","clean 10 min or more"))))'))
        w4.cell(row=r, column=11, value=f'=A{r}&" - "&B{r}')
        for col in (3, 4, 5, 6, 7):
            w4.cell(row=r, column=col).number_format = '0;-0;"–"'
            w4.cell(row=r, column=col).alignment = Alignment(horizontal='center')
        rows4.append(r)
        r += 1
style_table(w4, 4, r - 1, 1, 11)
w4.column_dimensions['K'].hidden = True
w4.column_dimensions['L'].hidden = True
for col, w in zip('ABCDEFGHIJ', [22, 22, 8, 14, 16, 14, 16, 12, 22, 58]):
    w4.column_dimensions[col].width = w
w4.cell(row=r + 1, column=1, value='Reading it').font = f_bold
for k, t in enumerate([
    'Lossless is the only thing that came close in 4K: 4K SDR 10-bit lossless stayed clean for the whole 5-minute round at 25 fps, then failed at 10 min.',
    'Log does not apply in the SDR modes (Core records them linear). In 4K Clear HDR 12-bit Log did apply, but lossless, Log, and lossless + Log all filled the buffer in 6 to 8 s at 27, 26 and 25 fps.',
    'Log + lossless together is worse than lossless alone in 4K Clear HDR 12-bit: files 8.5 MB against 6.1 MB, and the drive wrote only 9-12 fps against 11-17. Log did not shrink the uncompressed files in this mode (12.6 MB against 12.4 MB). Lossless alone already halves the files, so the drain (11-17 fps) points at the lossless encoder (CPU), not the SSD.',
    '4K Clear HDR 12-bit uncompressed was not run: it has the same file size as 4K SDR 12-bit, which had already failed.',
    'Model (see the Model sheet): 25 fps needs files of about 7 MB or less; 4K 12-bit is 12.4 MB, 10.4 MB with Log, and lossless files are the only ones near that.'], r + 2):
    w4.cell(row=k, column=1, value='- ' + t).font = f_norm
bc4 = BarChart()
bc4.type, bc4.grouping = 'bar', 'clustered'
bc4.title = '4K at 25 fps: seconds before the take stopped (300 = passed 5 min)'
bc4.add_data(Reference(w4, min_col=5, min_row=4, max_row=r - 1), titles_from_data=True)
bc4.set_categories(Reference(w4, min_col=11, min_row=5, max_row=r - 1))
bc4.height, bc4.width = 14, 26
bc4.legend = None
bc4.visible_cells_only = False
bc4.y_axis.scaling.min = 0
bc4.y_axis.delete = False
bc4.x_axis.delete = False
w4.add_chart(bc4, f'A{r + 8}')

# ------------------------------------------------------------------ Storage A/B
wa = wb.create_sheet('Storage A-B')
wa.sheet_view.showGridLines = False
wa['A1'] = 'Storage tuning A/B: did anything change the result?'
wa['A1'].font = f_title
wa['A2'] = ('Three repeats per variant, 120 s cap, no stop at the first drop. Average seconds until Core stopped the take (buffer full); '
            '120 = ran the full time. Variants: writer threads, write queue, sync interval, kernel tuning (dirty pages, scheduler, queue).')
wa['A2'].font = f_sub
ab_cases = [('4K SDR 12-bit, uncompressed, 25 fps', '4kSDR12', 25, 'uncompressed'),
            ('4K SDR 10-bit, uncompressed, 25 fps', '4kSDR10', 25, 'uncompressed'),
            ('4K SDR 10-bit, lossless, 26 fps', '4kSDR10', 26, 'lossless')]
header_row(wa, 4, 1, ['Variant'] + [c[0] for c in ab_cases])
wa.row_dimensions[4].height = 44
variants = [('base', 'baseline (workers 4, queue 12, sync 1000 ms)'), ('workers2', 'workers 2'), ('workers6', 'workers 6'),
            ('queue24', 'queue 24'), ('queue48', 'queue 48'), ('sync500', 'sync every 500 ms'), ('sync2000', 'sync every 2000 ms'),
            ('kerneltune', 'kernel tuning on')]
VAR_COL = rng('H')
for i, (vk, vl) in enumerate(variants, 5):
    wa.cell(row=i, column=1, value=vl)
    wa.cell(row=i, column=9, value=vk).font = Font(name=F, size=8, color='BFBFBF')
    for j, (_, mk, fp, cfg) in enumerate(ab_cases, 2):
        wa.cell(row=i, column=j,
                value=(f'=IFERROR(AVERAGEIFS({SEC_COL},{VAR_COL},$I{i},{MODE_COL},"{mk}",{FPS_COL},{fp},{CFG_COL},"{cfg}"),0)'))
        wa.cell(row=i, column=j).number_format = '0'
style_table(wa, 4, 4 + len(variants), 1, 1 + len(ab_cases))
wa.column_dimensions['A'].width = 40
for col in 'BCD':
    wa.column_dimensions[col].width = 20
wa.column_dimensions['I'].hidden = True
wa['A14'] = ('Result: at 25 fps every variant filled the buffer in 7 to 20 s in both 4K modes (no pattern beyond noise); at 26 fps the lossless '
             '4K SDR 10-bit config stayed clean for the full 120 s in every variant. The tuning knobs made no difference.')
wa['A14'].font = f_norm
wa['A14'].alignment = Alignment(wrap_text=True, vertical='top')
wa.merge_cells('A14:D16')
bc2 = BarChart()
bc2.type, bc2.grouping = 'bar', 'clustered'
bc2.title = 'Average seconds until stop, by tuning variant'
bc2.add_data(Reference(wa, min_col=2, max_col=1 + len(ab_cases), min_row=4, max_row=4 + len(variants)), titles_from_data=True)
bc2.set_categories(Reference(wa, min_col=1, min_row=5, max_row=4 + len(variants)))
bc2.height, bc2.width = 11, 24
bc2.legend.position = 'r'
bc2.y_axis.delete = False
bc2.x_axis.delete = False
wa.add_chart(bc2, 'F4')

# ------------------------------------------------------------------ Model (file size vs fps)
wm = wb.create_sheet('Model')
wm.sheet_view.showGridLines = False
wm['A1'] = 'Why 4K fails: frame time = per-file overhead + size / write speed'
wm['A1'].font = f_title
wm['A2'] = ('Fitted by hand to two short-take limits (12.4 MB at about 18 fps, 3.1 MB at about 36 fps). Blue cells are inputs. '
            'Measured 30-minute limits sit below the model: the drive is slower over a long take.')
wm['A2'].font = f_sub
wm['A4'], wm['B4'] = 'Per-file overhead (ms)', 19
wm['A5'], wm['B5'] = 'Write speed (MB/s)', 345
wm['A6'], wm['B6'] = 'Lowest fps that counts', 25
for r in (4, 5, 6):
    wm.cell(row=r, column=1).font = f_bold
    wm.cell(row=r, column=2).font = f_input
    wm.cell(row=r, column=2).border = box
wm['C4'], wm['C5'], wm['C6'] = ('fitted (assumption)', 'close to the 354 MB/s measured with big direct writes', 'campaign floor')
for r in (4, 5, 6):
    wm.cell(row=r, column=3).font = f_sub
wm['A7'], wm['B7'] = 'Largest file for the floor fps (MB)', '=(1000/B6-B4)*B5/1000'
wm['B7'].number_format = '0.0'
wm['A7'].font = f_bold
header_row(wm, 9, 1, ['File size (MB)', 'Model fps', 'Measured 30-min fps', 'What it is'])
sizes = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17]
for i, sz in enumerate(sizes, 10):
    wm.cell(row=i, column=1, value=sz).font = f_input
    wm.cell(row=i, column=2, value=f'=1000/($B$4+A{i}/$B$5*1000)')
    wm.cell(row=i, column=2).number_format = '0.0'
style_table(wm, 9, 9 + len(sizes), 1, 4, band=False)
mr = 10 + len(sizes) + 1
wm.cell(row=mr, column=1, value='Measured points').font = f_bold
header_row(wm, mr + 1, 1, ['File size (MB)', 'Model fps', 'Measured 30-min fps', 'What it is'])
pts = [(2.59, 33, '2K SDR 10-bit uncompressed'), (3.11, 28, '2K Clear HDR 12-bit uncompressed'),
       (4.22, 26, '2K Clear HDR 16-bit uncompressed'), (12.44, 18, '4K 12-bit uncompressed (drain estimate, short take)')]
for k, (sz, fp, name) in enumerate(pts, mr + 2):
    wm.cell(row=k, column=1, value=sz).font = f_input
    wm.cell(row=k, column=2, value=f'=1000/($B$4+A{k}/$B$5*1000)').number_format = '0.0'
    wm.cell(row=k, column=3, value=fp).font = f_input
    wm.cell(row=k, column=4, value=name)
style_table(wm, mr + 1, mr + 1 + len(pts), 1, 4, band=False)
for k in range(mr + 2, mr + 2 + len(pts)):
    wm.cell(row=k, column=1).font = f_input
    wm.cell(row=k, column=3).font = f_input
wm.column_dimensions['A'].width = 36
wm.column_dimensions['B'].width = 14
wm.column_dimensions['C'].width = 22
wm.column_dimensions['D'].width = 48
sc = ScatterChart()
sc.title = 'Model vs measured: fps by file size'
sc.style = 13
sc.x_axis.title, sc.y_axis.title = 'file size (MB)', 'fps'
s1 = Series(Reference(wm, min_col=2, min_row=10, max_row=9 + len(sizes)), Reference(wm, min_col=1, min_row=10, max_row=9 + len(sizes)),
            title='model')
s1.marker.symbol = 'none'
s1.smooth = True
s1.graphicalProperties = GraphicalProperties()
s1.graphicalProperties.line.solidFill = '1F3864'
s1.graphicalProperties.line.width = 28575
s2 = Series(Reference(wm, min_col=3, min_row=mr + 2, max_row=mr + 1 + len(pts)),
            Reference(wm, min_col=1, min_row=mr + 2, max_row=mr + 1 + len(pts)), title='measured (30 min)')
s2.marker.symbol, s2.marker.size = 'circle', 11
s2.marker.graphicalProperties = GraphicalProperties(solidFill='C00000')
s2.marker.graphicalProperties.line.solidFill = 'C00000'
s2.graphicalProperties = GraphicalProperties()
s2.graphicalProperties.line.solidFill = 'C00000'
s2.graphicalProperties.line.width = 9525
s2.graphicalProperties.line.dashStyle = 'sysDot'
sc.series.append(s1)
sc.series.append(s2)
sc.height, sc.width = 10, 20
sc.legend.position = 'b'
sc.y_axis.scaling.min = 0
sc.x_axis.scaling.min = 0
sc.y_axis.delete = False
sc.x_axis.delete = False
wm.add_chart(sc, 'F4')

# ------------------------------------------------------------------ Method
wn = wb.create_sheet('Method')
wn.sheet_view.showGridLines = False
wn['A1'] = 'How the campaign worked'
wn['A1'].font = f_title
lines = [
    ('Rig', f"{sess['pi_model']}, revision {sess['pi_revision']} (the C0 type), IMX585 sensor. {sess['drive']}, exFAT, label USB-RAW. "
            f"Core {sess['core_commit']}. Raspberry Pi supply replaced after under-voltage resets; throttle flag 0x0 throughout."),
    ('Take end', 'A take ends at the first dropped frame, when Core\'s RAM write buffer reaches its 90 % safety stop (buffer full), or at the '
                 'target length (or when the 466 GB drive is full).'),
    ('Ladder', 'Every config is walked down from the fps the storage can theoretically carry, in a 5-minute take. Survivors go to 10, 20 and 30 minutes. '
               'After a failure the fps steps 3, 6, 12 down until a take passes, then the gap above it is bisected.'),
    ('Pass', 'Pass = the take reached its length with no dropped frame and no buffer full. Only 25 fps and above count.'),
    ('Ruling out', 'Options that cannot change the result were not tried: by cause (storage or capture limited), by result (a switch that did not '
                   'help alone is not combined), and by theory (e.g. a data rate far above what the drive wrote in an earlier take).'),
    ('Modes', '4K Clear HDR 16-bit was excluded (422 MB/s at 25 fps against 354 MB/s of drive). 4K Clear HDR 12-bit and the four 2K modes and both 4K SDR modes were run.'),
    ('Log', 'Log stores fewer bits per sample. Core applies it only to unpacked 16-bit raw streams (Clear HDR). In the SDR modes Core answered "pisp_comp1 raw '
            'stream cannot be mapped on the copy worker, recording linear", so those Log tests were skipped.'),
    ('Accuracy', 'Single takes per cell, except the storage A/B (three repeats). The same fps passed 20 min and later failed within 20 s, so numbers are good to about plus or minus 3 fps.'),
    ('Data', 'Sheet "Takes" holds every take from the campaign database (longtakes.db, snapshot above); Tier, Pass, Baseline and Key are formulas. The summary tables and charts read from it.'),
    ('Not covered', 'Core\'s CPU is logged per take only for the follow-up (since 19:30); the SSD has no temperature sensor Core can read.'),
]
for i, (k, t) in enumerate(lines, 3):
    wn.cell(row=i, column=1, value=k).font = f_bold
    wn.cell(row=i, column=1).alignment = Alignment(vertical='top')
    c = wn.cell(row=i, column=2, value=t)
    c.font = f_norm
    c.alignment = Alignment(wrap_text=True, vertical='top')
    wn.row_dimensions[i].height = 54
wn.column_dimensions['A'].width = 14
wn.column_dimensions['B'].width = 100

for _ws in wb.worksheets:
    for _c in _ws._charts:
        _c.visible_cells_only = False
        if _c.legend is not None:
            _c.legend.overlay = False
        if _c.title is not None and getattr(_c.title, 'overlay', None) is not False:
            _c.title.overlay = False
from openpyxl.worksheet.properties import PageSetupProperties
for _ws in wb.worksheets:
    _ws.page_setup.orientation = 'landscape'
    _ws.page_setup.fitToWidth = 1
    _ws.page_setup.fitToHeight = 0
    _ws.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)
wb.move_sheet('Takes', offset=len(wb.sheetnames))
wb.save(OUT)
print('saved', OUT, 'takes rows', len(rows))
