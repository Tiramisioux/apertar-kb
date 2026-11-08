# Capacity, data rate and wear arithmetic for the NVMe campaign (decimal GB; drive = 999.96 GB per df -B1 on 2026-11-02).
# Corrected 2026-11-08 afternoon after the R3 check: HDR16 file 16.59 MB (not the 16.90 MB raw buffer); crops are 12-bit modes.
# The 75 % column is the owner's former rule, removed 2026-11-08; kept only as a marker of the near-full regime.
DRIVE_B = 999_960_870_912
RULE = 0.75  # owner's rule: stay well below ~75 % full (hardware-log 2026-10-26: 77-81 % full lost frames)
DNG_OVERHEAD = 1540  # bytes per DNG (feasibility V-F4 row 10)
modes = {
    # name: bytes per frame (payload) + overhead
    "HDR16 uncompressed (2160-row file, measured 16,590,340 B)": 16_590_340,  # the raw buffer is 3840x2200x2 = 16,896,000; the FILE is 16.59 MB (hardware-log:140)
    "HDR16 Log 12 (16->12 stored)":      12_451_344,                           # measured one DNG 2026-10-31
    "HDR16 lossless JPEG (est. ~9 MB)":  9_000_000,                            # UNVERIFIED size; encoder ~17.5 fps so irrelevant above 17 fps
    "SDR12 uncompressed packed (3840x2160x1.5)": int(3840*2160*1.5) + DNG_OVERHEAD,  # 12,441,600 + overhead
    "SDR12 lossless JPEG (COMP1 in, ~5.98 MB measured one scene)": 5_980_000,
    "SDR10 uncompressed packed (x1.25)": int(3840*2160*1.25) + DNG_OVERHEAD,
    "HDR16 lossy 3:1 (16.9/3, est.)":    int((3840*2200*2)/3),
    "HDR16 lossy 5:1 (16.9/5, est.)":    int((3840*2200*2)/5),
    "4K crop 3840x2072 SDR12 unc (1.85:1, derived)": int(3840*2072*1.5) + DNG_OVERHEAD,
    "4K crop 3840x1608 SDR12 unc (2.39:1, derived)": int(3840*1608*1.5) + DNG_OVERHEAD,
}
fps_list = [24, 25, 28, 30, 33, 42, 50]
mins = [3, 5, 15, 30]
print(f"drive {DRIVE_B/1e9:.1f} GB; 75 % rule = {RULE*DRIVE_B/1e9:.0f} GB usable per take if the drive is empty\n")
for name, bpf in modes.items():
    print(f"== {name}: {bpf/1e6:.2f} MB/frame")
    print("   fps   MB/s   files/30min  | GB at 3 / 5 / 15 / 30 min   | 30-min fill %  (>75% = X)")
    for f in fps_list:
        rate = bpf * f
        gbs = [rate*m*60/1e9 for m in mins]
        fill = gbs[-1]/ (DRIVE_B/1e9) * 100
        flag = "X" if fill > RULE*100 else ("!" if fill > 60 else "")
        print(f"   {f:>3}  {rate/1e6:6.0f}   {f*1800:>9,}    | {gbs[0]:5.0f} / {gbs[1]:5.0f} / {gbs[2]:5.0f} / {gbs[3]:5.0f}      | {fill:5.1f} % {flag}")
    print()

# Wear: smart-log 2026-11-02: data_units_written 49,380,871 (x 512,000 B = 25.28 TB), percentage_used 3 %.
duw = 49_380_871 * 512_000
print(f"written so far: {duw/1e12:.2f} TB at percentage_used 3 % -> implied endurance ~{duw/0.03/1e12:.0f} TB (if 3.0 %; 2.5-3.5 % -> {duw/0.035/1e12:.0f}-{duw/0.025/1e12:.0f} TB)")
for tbw in (600, 450):
    print(f"  rated {tbw} TBW: used {duw/1e12/tbw*100:.1f} %; a 10 TB campaign = {10/tbw*100:.1f} % of rating; 1 TB = {1/tbw*100:.2f} %")
