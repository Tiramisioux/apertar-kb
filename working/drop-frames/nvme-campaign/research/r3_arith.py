# R3: arithmetic from KB-measured file sizes (bytes), decimal GB
CORSAIR_B = 999_960_870_912            # measured df -B1 (night-2026-11-01.md:95; probe-exfat-dir.md:20)
KINGSTON_GIB = 477                      # KB "477 GB" (longtakes-campaign-plan.md:19); erased run samples free 475.9 at 0.2 % fill
KINGSTON_B = KINGSTON_GIB * 2**30       # if the runner's unit is GiB -> 512.1e9 B (derived, unconfirmed)
RESERVE = 10e9
usable = {"990 GB (Corsair 1 TB, 999.96 GB - 10 GB)": CORSAIR_B - RESERVE,
          "490 GB (draft's 500 GB card assumption)": 490e9,
          "502 GB (Kingston if 477 GiB volume - 10 GB)": KINGSTON_B - RESERVE}
arms = [
 ("HDR16 unc 3840x2160 (file)",   16_590_340, "measured file (HL:140)"),
 ("HDR16 unc, draft's 16.90",     16_897_540, "WRONG: raw buffer 3840x2200x2 + 1540"),
 ("HDR16 Log 16->12",             12_451_344, "measured one DNG (HL:820)"),
 ("SDR12 unc packed",             12_443_140, "derived 12,441,600 + 1,540 (V-F4 row 10)"),
 ("SDR12 lossless (one scene)",   5_982_609,  "measured 688 MB / 115 frames (HL:842-846)"),
 ("SDR10 unc packed",             10_369_540, "derived (F4 2.1)"),
 ("Crop 3840x2076 SDR12 unc",     11_959_300, "derived (F4 A')"),
 ("Crop 3840x2072 SDR12 unc",     int(3840*2072*1.5)+1540, "derived (mode exists at 10/12 bit, HL:901)"),
 ("Crop 3840x2072 HDR16-style",   3840*2072*2+1540, "unconfirmed: no 16-bit crop heights in KB"),
 ("Crop 3840x1608 SDR12 unc (2.39:1)", int(3840*1608*1.5)+1540, "derived (driver crop list, drivers.md:141)"),
 ("Crop 3840x1600 (draft)",       3840*1600*2+1540, "NOT A KB MODE"),
]
fps_list = [24,25,28,30,33,42,50]
mins = [3,5,15,30]
print("== per arm: MB/frame; MB/s per fps; GB per 3/5/15/30 min at 25 and 30 fps; files/30 min; fit; max minutes ==")
for name,b,lab in arms:
    print(f"\n## {name}: {b:,} B = {b/1e6:.2f} MB  [{lab}]")
    print("  MB/s: " + ", ".join(f"{f}fps {b*f/1e6:.0f}" for f in fps_list))
    for f in (25,28,30,33,42,50):
        gbs = [b*f*m*60/1e9 for m in mins]
        files30 = f*1800
        fits = []
        for uname,u in usable.items():
            maxmin = u/(b*f)/60
            fits.append(f"{uname.split(' ')[0]}: max {maxmin:.1f} min" + (" (30 fits)" if maxmin>=30 else f" (30-min take {gbs[3]:.0f} GB does NOT fit)"))
        print(f"  {f:>2} fps: GB 3/5/15/30 min = {gbs[0]:.0f}/{gbs[1]:.0f}/{gbs[2]:.0f}/{gbs[3]:.0f}; files/30min {files30:,}; " + "; ".join(fits))

print("\n== fill of the Corsair at the end of a 30-min take on an EMPTY drive (999.96 GB) ==")
for name,b,lab in arms[:6]:
    print(f"  {name}: " + ", ".join(f"{f}fps {b*f*1800/CORSAIR_B*100:.0f} %" for f in (25,28,30,33,42,50)))

print("\n== exFAT create cost from the measured fit median_ns = -183,673 + 316.64 x files (probe-exfat-dir.md:60) ==")
for N in (15000,22500,28500,29500,45000,50400,54000,59400,75600,90000):
    ms = (-183673 + 316.64*N)/1e6
    shares = " ".join(f"{f}fps {ms/(1000/f)*100:.0f} %" for f in (25,28,30,33,50))
    print(f"  {N:>6,} files: {ms:5.2f} ms  -> {shares}")
print("  25 % ceiling N = 0.25 x period / 316.64 ns (+ intercept): " + ", ".join(f"{f}fps {int((0.25*1e9/f + 183673)/316.64):,}" for f in (25,28,30,33,50)))

print("\n== fit-tier file counts on 490 / 502 GB usable (HDR16 unc 16.59 MB) ==")
for u in (490e9, 502e9, 989.96e9):
    for f in (25,28,30):
        n = int(u/16_590_340); print(f"  usable {u/1e9:.0f} GB @ {f} fps: {n:,} frames = {n/f/60:.1f} min; create at end {(-183673+316.64*n)/1e6:.1f} ms = {(-183673+316.64*n)/1e6/(1000/f)*100:.0f} % of period")

print("\n== wear ==")
duw = {"2026-11-02 18:5x B0 baseline": 49_380_871, "after evening 1 (11-02)": 51_995_905, "after evening 2 (11-03)": 53_634_400}
for k,v in duw.items(): print(f"  {k}: {v:,} DU x 512,000 B = {v*512000/1e12:.2f} TB")
print(f"  after evening 3 (11-04): 29.01 TB (handoff-drop-frames-tier1.md:185, '+1.55 TB tonight') -> implied DU {29.01e12/512000:,.0f}")
print(f"  evening 1 delta {(51995905-49380871)*512000/1e12:.2f} TB; evening 2 delta {(53634400-51995905)*512000/1e12:.2f} TB; evening 3 delta {29.01-53634400*512000/1e12:.2f} TB")
print(f"  implied endurance at 3 % used: 25.28/0.03 = {25.28/0.03:.0f} TB (2.5-3.5 %: {25.28/0.035:.0f}-{25.28/0.025:.0f} TB) -- derived; percentage_used is an integer")
print("\n== per-take bytes HDR16 unc (measured file) at 25 fps: " + ", ".join(f"{m} min {16_590_340*25*m*60/1e9:.0f} GB" for m in (1,3,5,10,15,30)))
print("== draft said 25 fps: 3 min 76, 5 min 127, 15 min 380, 30 min 760 GB (from 16.90) ==")
print("\n== thermal slopes (derived from measured endpoints) ==")
print(f"  A0: 34->54 C in 600 s at 415 MB/s = {20/10:.1f} C/min; t2b: 39->72 C in 600 s at 410 MB/s = {33/10:.1f} C/min; t2a: 39->65 C at 197 MB/s lossless = {26/10:.1f} C/min")
