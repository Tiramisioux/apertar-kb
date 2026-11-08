# Emits the markdown tables for R3 (deliverables 1 and 2). Decimal GB/MB. Sources in the report text.
CORSAIR_B = 999_960_870_912
KINGSTON_B = 477 * 2**30          # 512.1e9 B: runner samples 475.9 GiB free at 0.2 % fill (erased run, git 242c0be); KB page says "477 GB"
RES = 10e9
U990 = CORSAIR_B - RES; U490 = 490e9; U502 = KINGSTON_B - RES
arms = [
 # name, bytes, label, source, fps list that the KB makes reachable/relevant
 ("HDR16 unc 4K (3840x2200 raw, 2160-row file)", 16_590_340, "measured", "HL:140 (file 16,590,340 B); V-F4 row 10", [24,25,28,30]),
 ("HDR16 Log 16->12 4K", 12_451_344, "measured (one DNG)", "HL:820; V-F4 row 10", [24,25,28,30]),
 ("SDR12 unc 4K (packed)", 12_443_140, "derived", "12,441,600 + 1,540; V-F4 row 10, F4 2.1", [25,28,30,33,42,50]),
 ("SDR12 lossless 4K (COMP1 in)", 5_982_609, "measured, one scene", "HL:842-846 pre-roll 688 MB / 115 frames", [25,30,33,42,50]),
 ("SDR10 unc 4K (packed)", 10_369_540, "derived", "F4 2.1 (10,368,000 + 1,540)", [25,30,33,42,50]),
 ("Crop 3840x2076 SDR12 unc", 11_959_300, "derived", "F4 A'; mode measured at 50 fps (HL:582-596)", [25,30,33,42,50]),
 ("Crop 3840x2072 SDR12 unc (1.85:1)", int(3840*2072*1.5)+1540, "derived", "mode probed 2026-11-01 (HL:901), no take", [25,30,33,42,50]),
 ("Crop 3840x1608 SDR12 unc (2.39:1)", int(3840*1608*1.5)+1540, "derived", "driver crop list drivers.md:141; no take", [25,30,33,42,50]),
 ("HDR16 height crop (heights unknown)", None, "unconfirmed", "fork-log 31d5418: 16-bit crops at 31.9-42.4 fps; no height in KB", []),
]
fps_all = [24,25,28,30,33,42,50]
out = []
out.append("| Arm | bytes/frame | MB/frame | label | source | " + " | ".join(f"MB/s @{f}" for f in fps_all) + " |")
out.append("|---|---:|---:|---|---|" + "---:|"*len(fps_all))
for name,b,lab,src,_ in arms:
    if b is None:
        out.append(f"| {name} | - | - | {lab} | {src} | " + " | ".join("-" for _ in fps_all) + " |"); continue
    out.append(f"| {name} | {b:,} | {b/1e6:.2f} | {lab} | {src} | " + " | ".join(f"{b*f/1e6:.0f}" for f in fps_all) + " |")
out.append("")
out.append("| Arm | fps | GB 3 min | GB 5 min | GB 15 min | GB 30 min | files / 30 min | fill of empty Corsair after 30 min | 990 GB usable: max min | 490 GB (draft): max min | 502 GB (Kingston 477 GiB - 10 GB): max min | create cost at the 30-min file count (share of period) |")
out.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
for name,b,lab,src,fl in arms:
    if b is None: continue
    for f in fl:
        gb = [b*f*m*60/1e9 for m in (3,5,15,30)]
        n30 = f*1800
        ms = (-183673 + 316.64*n30)/1e6
        def mm(u):
            m = u/(b*f)/60
            return f"{m:.1f}" + (" (fits)" if m >= 30 else "")
        out.append(f"| {name} | {f} | {gb[0]:.0f} | {gb[1]:.0f} | {gb[2]:.0f} | {gb[3]:.0f} | {n30:,} | {gb[3]*1e9/CORSAIR_B*100:.0f} % | {mm(U990)} | {mm(U490)} | {mm(U502)} | {ms:.1f} ms ({ms/(1000/f)*100:.0f} %) |")
out.append("")
out.append("| files in the folder | create ms (fit) | 25 fps (40.0 ms) | 28 fps (35.7 ms) | 30 fps (33.3 ms) | 33 fps (30.3 ms) | 50 fps (20.0 ms) |")
out.append("|---:|---:|---:|---:|---:|---:|---:|")
for N in (15000,22500,28500,29535,30258,45000,50400,54000,59400,90000):
    ms = (-183673 + 316.64*N)/1e6
    note = {28500:" (draft's fit tier)",29535:" (fit tier, 490 GB, HDR16 unc)",30258:" (fit tier, 502 GB, HDR16 unc)",45000:" (30 min at 25)",50400:" (30 min at 28)",54000:" (30 min at 30)",59400:" (30 min at 33)",90000:" (30 min at 50)",15000:" (10 min at 25; A0/A1/#80 measured clean)",22500:" (15 min at 25)"}.get(N,"")
    out.append(f"| {N:,}{note} | {ms:.2f} | " + " | ".join(f"{ms/(1000/f)*100:.0f} %" for f in (25,28,30,33,50)) + " |")
out.append("")
out.append("25 % ceiling (create alone <= 0.25 x period), from the fit: " + ", ".join(f"{int((0.25*1e9/f + 183673)/316.64):,} files at {f} fps" for f in (25,28,30,33,50)) + " (the probe page rounds these to 31,600 / 26,300 / 23,900 / 15,800 using c = 63.3 ns without the intercept).")
open('/tmp/claude-0/-home-user-apertar-kb/ec7a80a5-e5d5-5e70-b1fc-fab0c6782e18/scratchpad/calc/r3_tables.md','w').write("\n".join(out)+"\n")
print("\n".join(out))
