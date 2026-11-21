# G8: numeric check of the 12-bit Clear HDR linearisation

Assignment G8 of the "12 bit clear HDR shows strange output" investigation. Programs and raw output live in
`/home/user/build/hdr12-numeric/` (`hdr12.cpp`, `hdr12.out`, copies of Cinemate's golden tables). Both are
reproduced below.

Refs: Core `cinemate-port` `01f170c`, libcamera `apertar` `6b0b49f`, driver `cinemate-port` `cd548ef` and
`origin/apertar` `e5b74d3`, cinepi-raw `63a08d5`.

## Result in one table

| # | Finding | Status | Symptom it would produce |
| --- | --- | --- | --- |
| F1 | Core's LinearizationTable equals libcamera's CcmpUnwrap LUT entry for entry (0 of 4096 differ) at the driver defaults, on both driver branches. `expansion[compressionLut[v]] == v` for every value libcamera emits. | confirmed (numeric) | none in 4K / 1x1 modes |
| F2 | The table and the libcamera LUT assume **no binning** (b=1). The cinemate-port driver and Core's H12 table offer **1920x1080 2x2 binned** 12-bit Clear HDR (origin/apertar offered 4K only). With b=4 the knees sit 4x lower; decoding with the b=1 table puts codes 326..871 at 0.058..0.13x their true level (-4.1 EV), then jumps back to ~1.0x at code 872. | probable (code confirmed; b=4 geometry from Cinemate measurement, not from the AppNote) | 1920x1080 H12 only: crushed, posterised mid-tones with a hard tonal step around code 872 (~17% of white), in the cDNG **and** in every preview (libcamera feeds the same wrong unwrap to the ISP and AE) |
| F3 | DNG reader result for 1x1 modes: black 0.000000, 18% grey 0.179365, clip 1.000000. Tags: BitsPerSample 12, LinearizationTable 4096, BlackLevel 3200, WhiteLevel 65520. | confirmed (numeric, from Core's own headers) | none |
| F4 | 12-bit vs 16-bit Clear HDR exposure scale differs by 0.98471 (-0.022 EV) at mid-grey. | confirmed (numeric) | not visible |
| F5 | Reconstruction uses the bottom of each quantisation bin: max error -63 codes (seg2, 64-LSB bins), worst ratio 0.886 (-0.17 EV) just above knee 1 (L=563). Against Cinemate's measured b=1 table: max 28.5 L, worst -0.076 EV. | confirmed (numeric; sensor truncation assumed) | not visible as "strange" |
| F6 | Log On in this mode (`cdngLogBits` = 12 when `cdngLog == Auto`): composed curve keeps black 0, grey 0.179284, clip 1.0. Max round-trip error -69 codes at lin 64192 (highlights); only 1413 of 4096 log codes used; footroom codes 0..31 never used. | confirmed (numeric) | no visible error; highlight steps ~70 LSB |
| F7 | If the libcamera unwrap does **not** run on a frame (Core receives `code<<4`), Core's compressionLut turns it into wrong codes: shadows lifted 16x (code 300 -> 0.026 instead of 0.0016, code 700 -> 0.129 instead of 0.0079), mids and whites almost right. | confirmed (numeric); whether it happens is unconfirmed | lifted, washed-out shadows in the cDNG only for frames where the unwrap was skipped (e.g. frames without a stats buffer) |
| F8 | Any mismatch between libcamera's live params and Core's hard-coded `Params{500,11500,6,4,200}` breaks the round trip: blc 0 -> 4042 entries differ (max 8133 codes); GRAD_TH {0,0} -> 3889 differ (max 7507); slope fallback idx 2/6 -> 3894 differ (max 38546). | confirmed (numeric); no evidence these params occur | wrong tone curve in cDNG and preview |

## (1) Core's table

Source: `src/cdng/ClearHdrCcmp.hpp:24-30@cinemate-port` (`knee1 = 500`, `knee2 = 11500`, `slope1 = 6`,
`slope2 = 4`, `black = 200`), build `:47-58`. The file is byte-identical to fork `origin/main`
(`git show origin/main:src/cdng/ClearHdrCcmp.hpp | diff - src/cdng/ClearHdrCcmp.hpp` prints nothing). The port did not change it.

| Item | Value |
| --- | --- |
| size | 4096 |
| [0..200] | 3200 (flat: everything at or below the pedestal is black) |
| [4095] | 65520 |
| monotonic | non-decreasing yes; strictly no (seg1 slope 0.98789 produces a repeat every ~82 codes, first at 283) |
| knee 1 | code 700 (3693 -> 3757) |
| knee 2 | code 871 (14505 -> 14576) |
| slopes | seg1 0.986 /code, seg2 63.23 /code, seg3 15.82 /code = 1, 64, 16 times the stretch 0.987889 |
| stretch | span 62320 / natural L(4095) 63084 = 0.987889 (-0.0176 EV) |

## (2) Core vs libcamera CcmpUnwrap

libcamera reads the params from the sensor at configure: `pisp.cpp:2950-3027@6b0b49f` (GRAD_TH array,
GRAD_COMP_L/H menus, `blc_u12 = BRIGHTNESS*4`, `:3023`). LUT formula `ccmp_unwrap.cpp:57-140`. It rewrites the
raw buffer in place (`ccmp_unwrap.cpp:146-165`, called from `pisp.cpp:825-829` and `:3100-3104`), so Core gets
linear 16-bit. Note the stale comment at `pisp.cpp:1825-1831` ("the raw buffer is NOT rewritten") contradicts the code.

Driver defaults are identical on both branches:

| Control / register | cinemate-port | origin/apertar |
| --- | --- | --- |
| GRAD_TH (CCMP1/2_EXP) | `{500, 11500}` `imx585.c:3688`, memcpy into p_cur/p_new `:3907-3908` | `{500, 11500}` `:1822`, `:2012-2013` |
| GRAD_COMP_L (ACMP1_EXP) | def 6 (1/64) `:3725` | def 6 `:1859` |
| GRAD_COMP_H (ACMP2_EXP) | def 4 (1/16) `:3736` | def 4 `:1870` |
| base table 0x36ec / 0x36ee | 0x04 / 0x06 `:557-558` | 0x04 / 0x06 `:517-518` |
| BLKLEVEL | 50, written at stream on `:4071` and via BRIGHTNESS `:3555-3561`; libcamera x4 = 200 | 50 |

Controls are re-applied by `__v4l2_ctrl_handler_setup` at stream on (`imx585.c:4186@cinemate-port`).
Core never writes them (`grep -rn "0x0098290\|GRAD\|BRIGHTNESS" src` finds nothing).

Result: 0 entries differ. Round trip `expansion[compressionLut[lc[c]]] == lc[c]` holds for all 4096 codes.

## (3) Forward curve and inverse

Forward model (KB `working/clearhdr-12bit-answer.md:48-53`, Cinemate measurement): `code = floor(ccmp(b*L)/b) + 200`.
Ideal decode in Core's domain: `3200 + L*0.987889`.

| Case | max abs error (16-bit codes) | where | worst ratio |
| --- | --- | --- | --- |
| b=1, T1=500 (register) | -63.2 | L=1715, code 718 | 0.8864 (-0.174 EV) at L=563 |
| b=1, T1=500.3389 (Cinemate measured) | -42.5 | L=1694, code 718 | 0.9207 (-0.119 EV) at L=542 |
| b=4, T1=500 | -7610.7 | L=8203, code 700 | 0.0577 (-4.11 EV) at L=2875 |
| b=4, T1=500.9431 (measured) | -7606.7 | L=8199, code 700 | 0.0579 (-4.11 EV) at L=2887 |

Both driver branches have the same register defaults, so the b=1 rows apply to both. The b=4 rows apply only to
cinemate-port: origin/apertar offers 12-bit Clear HDR only as 4K (`imx585.c:1430@origin/apertar`, `*mode_list =
&supported_modes[10]; /* 4K 12-bit only */`@origin/apertar). cinemate-port offers the binned 1920x1080 entry
(`imx585.c:1066-1068`, `.binning = 2`; range start `IMX585_MODE_1080P_12BIT` at `:3086-3091`), and Core lists it
first in H12 (`src/camera/Imx585Modes.hpp:79` `{ 1920, 1080, true }`). With module option
`clearhdr_windowed_binning=1` more binned crops become reachable (`imx585.c:3087-3091`, `:4680`).

Binned spot values (b=4, Core decode vs true):

| code | true L | Core L-equivalent ratio |
| --- | --- | --- |
| 325 | 125 | 0.996 |
| 340 | 1070 | 0.131 |
| 368 | 2862 | 0.058 |
| 700 | 8184 | 0.061 |
| 872 | 10936 | 1.053 |
| 4095 | 62504 | 1.009 |

Against Cinemate's golden tables (`cinepi-raw/resources/ccmp_luts`): fullres max 28.5 L (code 872), worst
-0.076 EV (code 216); binned max -7685 L (code 700), worst -4.10 EV (code 369).

## (4) DNG reader

Tags: `CameraController.cpp:4090-4096@cinemate-port` sets the table and black 3200 on container scale;
`CdngEncoder.cpp:1476-1491` writes BlackLevel via `encodedBlackLevel(3200, Bits12, true)` (clamp limit 4094, so
3200 survives) and WhiteLevel `table.back()` = 65520; tags at `:1703-1707`. Only the cDNG path gets the table
(`clearHdrStoresCodes12`, `CameraController.cpp:1640-1644`); MLV stays 16-bit linear.

| Pixel | code | lin | normalised |
| --- | --- | --- | --- |
| black | 200 | 3200 | 0.000000 |
| sub-black noise | 190 | 3200 | 0.000000 |
| 18% grey (L=11355) | 869 | 14378 | 0.179365 |
| clip | 4095 | 65520 | 1.000000 |
| 16-bit mode, same L (BlackLevel 3201, White 65535) | | | 0.182150 |

## (5) Log composed

`Types.hpp:364-370`: Clear HDR 12-bit cDNG with Log Auto stores 12 bits. `CameraController.cpp:4029-4034` builds
`buildComposed(makeParams(16,12,3200,65520), expansionTable())`; tags at `:5129-5133`.

| Item | Value |
| --- | --- |
| params | mu 10000, footroom 32 codes / 487 LSB, black 3200, white 65520 |
| BlackLevel / WhiteLevel | 3200 / 65520 |
| black / grey / clip | 0.000000 / 0.179284 / 1.000000 |
| max round-trip error | -69 codes at CCMP code 4011 (lin 64192) |
| log codes used | 1413 of 4096; footroom 0..31 unused (the CCMP table already flattens sub-black) |

## Open items

| Question | Settle with |
| --- | --- |
| Does the IMX585 compander really see the 2x2 binned sum (b=4)? | Pi: record 1920x1080 and 3840x2160 12-bit Clear HDR of the same grey ramp; plot stored code histograms; or diff a binned frame's decoded ramp against 16-bit binned |
| Does the sensor truncate or round in the compressed segments? | Pi: ramp capture; only changes F5 by half a bin |
| Can a frame reach Core without the unwrap (no stats buffer)? | `pisp.cpp:2133-2142`: unwrap runs only `if (rawStats_)` and the job has stats; Pi: log count of `process()` calls vs frames |
| Lossy DNG in 12-bit Clear HDR: `planCdngLog` uses source = rawBitDepth 12 (`CameraController.cpp:3988-3991`) while the samples are libcamera's 16-bit linear | read `LossyDngEncoder.cpp:450-470` with a 16-bit frame; out of G8 scope |

## Program source

```cpp
// G8 numeric check of the IMX585 12-bit Clear HDR linearisation.
// Builds against Apertar-Core@cinemate-port src/cdng/{ClearHdrCcmp,LogCurve,BlackLevel}.hpp.
// The libcamera LUT is a verbatim re-implementation of
// tiramisioux/libcamera@6b0b49f src/libcamera/pipeline/rpi/pisp/ccmp_unwrap.cpp:57-140 (setParams).
#include "cdng/ClearHdrCcmp.hpp"
#include "cdng/LogCurve.hpp"
#include "cdng/BlackLevel.hpp"

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <set>
#include <sstream>
#include <string>
#include <vector>

using namespace apertar;

// ---- libcamera CcmpUnwrap::setParams, scalar, copied formula by formula ----
struct LcParams { uint32_t thresh1, thresh2; uint8_t slope_l_idx, slope_h_idx; uint16_t blc_u12; };
static std::vector<uint16_t> libcameraLut(const LcParams &p)
{
    std::vector<uint16_t> lut(4096);
    const uint32_t T1 = std::min<uint32_t>(p.thresh1, 0x1FFFFu);
    const uint32_t T2 = std::min<uint32_t>(std::max<uint32_t>(p.thresh2, T1), 0x1FFFFu);
    const unsigned sL = std::min<unsigned>(p.slope_l_idx, 11);
    const unsigned sH = std::min<unsigned>(p.slope_h_idx, 11);
    const uint32_t O2 = T1 + ((T2 - T1) >> sL);
    const int32_t blc_u12 = std::min<uint32_t>(p.blc_u12, 4095);
    const int32_t blc_u16 = blc_u12 << 4;
    auto inverse = [&](uint32_t out) -> uint32_t {
        if (out <= T1) return out;
        if (out <= O2) return T1 + ((out - T1) << sL);
        return T2 + ((out - O2) << sH);
    };
    const uint32_t natural_max_postblc = (inverse(4095u - blc_u12) > 0) ? inverse(4095u - blc_u12) : 1u;
    const uint32_t target_max_postblc = 0xFFF0u - blc_u16;
    for (uint32_t out = 0; out < 4096; out++) {
        int32_t out_post_blc = static_cast<int32_t>(out) - blc_u12;
        uint64_t in = (out_post_blc <= 0) ? 0u : inverse(static_cast<uint32_t>(out_post_blc));
        uint64_t scaled = (in * target_max_postblc) / natural_max_postblc;
        int64_t val = static_cast<int64_t>(blc_u16) + static_cast<int64_t>(scaled);
        if (val < 0) val = 0;
        if (val > 0xFFFF) val = 0xFFFF;
        lut[out] = static_cast<uint16_t>(val);
    }
    return lut;
}

// ---- sensor forward curve (KB working/clearhdr-12bit-answer.md:48-53): code = ccmp(b*L)/b + P ----
struct Fwd { double T1, T2; int s1, s2; int P; int b; };
static double fwdCurve(double x, const Fwd &f)
{
    const double C2 = f.T1 + (f.T2 - f.T1) / double(1 << f.s1);
    if (x <= f.T1) return x;
    if (x <= f.T2) return f.T1 + (x - f.T1) / double(1 << f.s1);
    return C2 + (x - f.T2) / double(1 << f.s2);
}
static int sensorCode(double L, const Fwd &f)
{
    double c = std::floor(fwdCurve(f.b * L, f) / f.b) + f.P;   // sensor truncates
    return int(std::min(4095.0, std::max(0.0, c)));
}
// exact inverse (continuous) of the forward curve, black-referred L for a code
static double trueL(int code, const Fwd &f)
{
    double y = double(f.b) * (code - f.P);
    if (y <= 0) return 0;
    const double C2 = f.T1 + (f.T2 - f.T1) / double(1 << f.s1);
    double x = y <= f.T1 ? y : y <= C2 ? f.T1 + (y - f.T1) * (1 << f.s1) : f.T2 + (y - C2) * (1 << f.s2);
    return x / f.b;
}

static std::vector<int> readGolden(const std::string &path, int *white)
{
    std::ifstream in(path);
    std::vector<int> v;
    std::string line;
    while (std::getline(in, line)) {
        if (!line.empty() && line[0] == '#') {
            auto pos = line.find("WhiteLevel ");
            if (pos != std::string::npos) *white = std::atoi(line.c_str() + pos + 11);
            continue;
        }
        std::istringstream s(line);
        int x;
        while (s >> x) v.push_back(x);
    }
    return v;
}

int main(int argc, char **argv)
{
    const std::string dir = argc > 1 ? argv[1] : ".";
    const auto &T = ccmp::expansionTable();
    const ccmp::Params P{};
    const double span = 65520.0 - 3200.0;                       // Core output span above black
    const double top = ccmp::linearAboveBlack(4095 - 200, P);   // natural L at code 4095
    std::printf("== (1) Core LinearizationTable (ccmp::expansionTable) ==\n");
    std::printf("size %zu  first [0]=%u [1]=%u [199]=%u [200]=%u [201]=%u  last [4094]=%u [4095]=%u\n",
                T.size(), T[0], T[1], T[199], T[200], T[201], T[4094], T[4095]);
    bool nondec = true, strict = true; int firstFlat = -1;
    for (int c = 1; c < 4096; ++c) {
        if (T[c] < T[c - 1]) nondec = false;
        if (T[c] == T[c - 1]) { strict = false; if (firstFlat < 0) firstFlat = c; }
    }
    int flatAbove = -1;
    for (int c = 202; c < 4096; ++c) if (T[c] == T[c - 1]) { flatAbove = c; break; }
    std::printf("non-decreasing %s, strictly increasing %s (first repeat at code %d; first repeat above 201: %d)\n",
                nondec ? "yes" : "NO", strict ? "yes" : "no", firstFlat, flatAbove);
    std::printf("natural L(4095) = %.0f, stretch factor span/L = %.6f (%.4f EV)\n", top, span / top,
                std::log2(span / top));
    const int k1 = 200 + 500, k2 = 200 + 500 + ((11500 - 500) >> 6);
    std::printf("knee1 at code %d (T=%u, next %u), knee2 at code %d (T=%u, next %u)\n", k1, T[k1], T[k1 + 1], k2,
                T[k2], T[k2 + 1]);
    struct Seg { int a, b; const char *n; } segs[] = {{0, 200, "below/at black"}, {200, k1, "seg1 (1:1)"},
                                                     {k1, k2, "seg2 (x64)"}, {k2, 4095, "seg3 (x16)"}};
    for (auto s : segs)
        std::printf("  %-15s codes %4d..%4d  mean slope %.4f /code  (= %.4f x ideal %s)\n", s.n, s.a, s.b,
                    double(T[s.b] - T[s.a]) / (s.b - s.a),
                    double(T[s.b] - T[s.a]) / (s.b - s.a) / (s.a == 0 ? 1.0 : (s.a == 200 ? 1.0 : s.a == k1 ? 64.0 : 16.0)),
                    s.a == 0 ? "0" : s.a == 200 ? "1*0.98789" : s.a == k1 ? "64*0.98789" : "16*0.98789");

    // ---- (2) libcamera ----
    std::printf("\n== (2) Core table vs libcamera CcmpUnwrap LUT ==\n");
    struct Case { const char *name; LcParams p; } cases[] = {
        {"driver defaults (500,11500,idx6,idx4, BRIGHTNESS 50 -> blc 200)", {500, 11500, 6, 4, 200}},
        {"libcamera fallback if slope ctrls missing (idx2,idx6)", {500, 11500, 2, 6, 200}},
        {"GRAD_TH read as {0,0} (.def=0, if memcpy default lost)", {0, 0, 6, 4, 200}},
        {"BRIGHTNESS 0 -> blc 0", {500, 11500, 6, 4, 0}},
    };
    for (auto &cs : cases) {
        auto L = libcameraLut(cs.p);
        int diffs = 0, maxd = 0, at = -1;
        for (int c = 0; c < 4096; ++c) {
            int d = int(T[c]) - int(L[c]);
            if (d) ++diffs;
            if (std::abs(d) > std::abs(maxd)) { maxd = d; at = c; }
        }
        std::printf("%-66s entries differing %4d, max |core-lc| %6d at code %d (core %u, lc %u)\n", cs.name, diffs,
                    maxd, at, at >= 0 ? T[at] : 0, at >= 0 ? L[at] : 0);
    }
    // round trip on what libcamera emits
    {
        auto L = libcameraLut({500, 11500, 6, 4, 200});
        const auto &C = ccmp::compressionLut();
        int bad = 0, codeMismatch = 0;
        for (int c = 0; c < 4096; ++c) {
            if (T[C[L[c]]] != L[c]) ++bad;
            if (C[L[c]] != c && L[c] != (c ? L[c - 1] : 0xFFFF)) ++codeMismatch;
        }
        std::printf("round trip expansion[compressionLut[lc[c]]]==lc[c]: failures %d; stored code != sensor code (excluding duplicate entries): %d\n",
                    bad, codeMismatch);
        std::set<uint16_t> distinct(T.begin(), T.end());
        std::printf("distinct table values %zu of 4096 (codes 0..200 all map to 3200)\n", distinct.size());
    }

    // ---- (3) forward curve vs Core table ----
    std::printf("\n== (3) sensor forward curve (driver defaults) decoded with Core table ==\n");
    std::printf("(error in 16-bit code values of Core's output domain: ideal = 3200 + L*%.6f)\n", span / top);
    for (int b : {1, 4}) {
        for (double T1 : {500.0, 500.3389, 500.9431}) {
            if ((b == 1 && T1 == 500.9431) || (b == 4 && T1 == 500.3389)) continue;
            Fwd f{T1, 11500, 6, 4, 200, b};
            double maxErr = 0, at = 0, maxRel = 0, atRel = 0; int atCode = 0;
            const double Lmax = trueL(4095, f) + (b == 1 ? 15 : 4);
            for (double L = 0; L <= Lmax; L += 1.0) {
                int code = sensorCode(L, f);
                double ideal = 3200 + L * span / top;
                double err = double(T[code]) - ideal;
                if (std::fabs(err) > std::fabs(maxErr)) { maxErr = err; at = L; atCode = code; }
                if (L >= 16) {
                    double rel = (T[code] - 3200.0) / (ideal - 3200.0);
                    if (std::fabs(std::log2(rel)) > std::fabs(std::log2(maxRel ? maxRel : 1))) { maxRel = rel; atRel = L; }
                }
            }
            std::printf("b=%d T1=%.4f: Lmax %.0f; max abs err %.1f codes at L=%.0f (code %d); worst ratio %.4f (%.3f EV) at L=%.0f\n",
                        b, T1, Lmax, maxErr, at, atCode, maxRel, std::log2(maxRel), atRel);
        }
    }
    // spot values for b=4 (binned 1920x1080 H12 mode on cinemate-port)
    std::printf("binned (b=4) spot values, Core decode vs true linear (16-bit, Core domain):\n");
    {
        Fwd f{500.9431, 11500, 6, 4, 200, 4};
        for (int code : {300, 325, 340, 368, 400, 500, 700, 872, 1500, 3000, 4095}) {
            double tl = trueL(code, f);
            double ideal = 3200 + tl * span / top;
            std::printf("  code %4d  true L %8.1f  ideal %8.1f  Core %5u  ratio(above black) %.3f\n", code, tl, ideal,
                        T[code], (T[code] - 3200.0) / std::max(1e-9, ideal - 3200.0));
        }
    }

    // ---- golden Cinemate tables ----
    std::printf("\n== Core table vs Cinemate golden tables (cinepi-raw@63a08d5 resources/ccmp_luts) ==\n");
    for (const char *name : {"ccmp_decode_mode3_fullres.txt", "ccmp_decode_mode2_binned.txt"}) {
        int white = 0;
        auto G = readGolden(dir + "/" + name, &white);
        if (G.size() != 4096) { std::printf("%s: read %zu entries\n", name, G.size()); continue; }
        // put both in black-referred L units: Core (T-3200)*top/span ; golden G-200
        double maxE = 0; int at = 0; double maxRel = 1; int atRel = 0;
        for (int c = 201; c < 4096; ++c) {
            double lc = (T[c] - 3200.0) * top / span;
            double lg = G[c] - 200.0;
            double e = lc - lg;
            if (std::fabs(e) > std::fabs(maxE)) { maxE = e; at = c; }
            if (lg >= 16) {
                double r = lc / lg;
                if (std::fabs(std::log2(r)) > std::fabs(std::log2(maxRel))) { maxRel = r; atRel = c; }
            }
        }
        std::printf("%s: white %d, golden[200]=%d [700]=%d [872]=%d [4095]=%d; max |Core-golden| %.1f L at code %d; worst ratio %.4f (%.3f EV) at code %d\n",
                    name, white, G[200], G[700], G[872], G[4095], maxE, at, maxRel, std::log2(maxRel), atRel);
    }

    // ---- (4) DNG reader ----
    std::printf("\n== (4) DNG reader: lin = LUT[stored]; out = (lin - BlackLevel)/(WhiteLevel - BlackLevel) ==\n");
    const float black = blackLevelForSampleBits(float(ccmp::kBlack16), 12, true);
    const int32_t blackTag = encodedBlackLevel(float(ccmp::kBlack16), RawBitDepth::Bits12, true);
    const uint32_t whiteTag = T.back();
    std::printf("tags: BitsPerSample 12, LinearizationTable 4096 SHORT, BlackLevel %d (float %.1f), WhiteLevel %u\n",
                blackTag, black, whiteTag);
    auto dng = [&](int code) { return (double(T[code]) - blackTag) / (double(whiteTag) - blackTag); };
    Fwd f1{500, 11500, 6, 4, 200, 1};
    const double Lgrey = 0.18 * top;
    const int cg = sensorCode(Lgrey, f1);
    std::printf("black  code 200 -> lin %u -> %.6f\n", T[200], dng(200));
    std::printf("noise  code 190 -> lin %u -> %.6f (sub-black clipped to 0 by the table itself)\n", T[190], dng(190));
    std::printf("grey   L=%.0f (18%% of sensor max) -> code %d -> lin %u -> %.6f\n", Lgrey, cg, T[cg], dng(cg));
    std::printf("clip   code 4095 -> lin %u -> %.6f\n", T[4095], dng(4095));
    // 16-bit Clear HDR mode, same L, as Core writes it (black from SensorBlackLevels 3200/16 = 200 on 12-bit scale)
    const int32_t b16 = encodedBlackLevel(200.0f, RawBitDepth::Bits16, false);
    const uint32_t w16 = encodedWhiteLevel(RawBitDepth::Bits16);
    std::printf("16-bit mode for comparison: BlackLevel %d WhiteLevel %u; grey -> %.6f; ratio 12/16 = %.5f (%.4f EV)\n",
                b16, w16, (3200 + Lgrey - b16) / double(w16 - b16), dng(cg) / ((3200 + Lgrey - b16) / double(w16 - b16)),
                std::log2(dng(cg) / ((3200 + Lgrey - b16) / double(w16 - b16))));
    // what if libcamera did NOT unwrap (raw code<<4 reaches Core)
    std::printf("if the unwrap did not run (Core sees code<<4):\n");
    for (int code : {200, 300, 500, 700, 869, 1500, 2500, 4095}) {
        uint16_t stored = ccmp::compressionLut()[code << 4];
        std::printf("  sensor code %4d -> stored %4d -> %.5f (correct %.5f)\n", code, stored, dng(stored), dng(code));
    }

    // ---- (5) Log composed ----
    std::printf("\n== (5) CineMate Log composed (cdngLogBits=12 when cdngLog==Auto) ==\n");
    auto lp = cdnglog::makeParams(16, 12, ccmp::kBlack16, 65520);
    if (!lp) { std::printf("makeParams(16,12,3200,65520) invalid\n"); return 0; }
    std::printf("%s\n", lp->describe().c_str());
    auto tabs = cdnglog::buildComposed(*lp, std::span<const uint16_t>(T.data(), T.size()));
    std::printf("forward %zu, inverse %zu, inverse[0]=%u [31]=%u [32]=%u [4095]=%u\n", tabs.forward.size(),
                tabs.inverse.size(), tabs.inverse[0], tabs.inverse[31], tabs.inverse[32], tabs.inverse[4095]);
    // tags written at CameraController.cpp:5129-5133 + CdngEncoder.cpp:1478-1491
    const int32_t lblack = encodedBlackLevel(float(lp->blackLevel), RawBitDepth::Bits12, true);
    const uint32_t lwhite = tabs.inverse.back();
    std::printf("tags: BlackLevel %d WhiteLevel %u (blackLevelForSampleBits clamps to <= 4094 on 12 bits: %.1f)\n",
                lblack, lwhite, blackLevelForSampleBits(float(lp->blackLevel), 12, true));
    auto ldng = [&](int code) {
        uint16_t lc = tabs.forward[code];
        return (double(tabs.inverse[lc]) - lblack) / (double(lwhite) - lblack);
    };
    std::printf("black code 200 -> log %u -> %.6f; grey code %d -> log %u -> %.6f (linear path %.6f); clip 4095 -> log %u -> %.6f\n",
                tabs.forward[200], ldng(200), cg, tabs.forward[cg], ldng(cg), dng(cg), tabs.forward[4095], ldng(4095));
    double maxE = 0; int at = 0; double maxRel = 1; int atRel = 0;
    std::set<uint16_t> used;
    bool mono = true;
    for (int c = 0; c < 4096; ++c) {
        used.insert(tabs.forward[c]);
        if (c && tabs.forward[c] < tabs.forward[c - 1]) mono = false;
        double e = double(tabs.inverse[tabs.forward[c]]) - T[c];
        if (std::fabs(e) > std::fabs(maxE)) { maxE = e; at = c; }
        if (T[c] > 3200 + 16) {
            double r = (tabs.inverse[tabs.forward[c]] - 3200.0) / (T[c] - 3200.0);
            if (std::fabs(std::log2(r)) > std::fabs(std::log2(maxRel))) { maxRel = r; atRel = c; }
        }
    }
    std::printf("composed round trip vs linear table: max err %.0f codes at CCMP code %d (lin %u); worst ratio %.4f at code %d; forward monotone %s; distinct log codes used %zu of 4096; footroom codes 0..31 used: %s\n",
                maxE, at, T[at], maxRel, atRel, mono ? "yes" : "NO", used.size(),
                *used.begin() < 32 ? "yes" : "no");
    return 0;
}
```

Build: `g++ -std=c++20 -O1 -Wall -I/home/user/Apertar-Core/src -I/home/user/Apertar-Core/include hdr12.cpp -o hdr12 && ./hdr12 .`

## Program output

```
== (1) Core LinearizationTable (ccmp::expansionTable) ==
size 4096  first [0]=3200 [1]=3200 [199]=3200 [200]=3200 [201]=3200  last [4094]=65504 [4095]=65520
non-decreasing yes, strictly increasing no (first repeat at code 1; first repeat above 201: 283)
natural L(4095) = 63084, stretch factor span/L = 0.987889 (-0.0176 EV)
knee1 at code 700 (T=3693, next 3757), knee2 at code 871 (T=14505, next 14576)
  below/at black  codes    0.. 200  mean slope 0.0000 /code  (= 0.0000 x ideal 0)
  seg1 (1:1)      codes  200.. 700  mean slope 0.9860 /code  (= 0.9860 x ideal 1*0.98789)
  seg2 (x64)      codes  700.. 871  mean slope 63.2281 /code  (= 0.9879 x ideal 64*0.98789)
  seg3 (x16)      codes  871..4095  mean slope 15.8235 /code  (= 0.9890 x ideal 16*0.98789)

== (2) Core table vs libcamera CcmpUnwrap LUT ==
driver defaults (500,11500,idx6,idx4, BRIGHTNESS 50 -> blc 200)    entries differing    0, max |core-lc|      0 at code -1 (core 0, lc 0)
libcamera fallback if slope ctrls missing (idx2,idx6)              entries differing 3894, max |core-lc|  38546 at code 3450 (core 55324, lc 16778)
GRAD_TH read as {0,0} (.def=0, if memcpy default lost)             entries differing 3889, max |core-lc|  -7507 at code 700 (core 3693, lc 11200)
BRIGHTNESS 0 -> blc 0                                              entries differing 4042, max |core-lc|  -8133 at code 700 (core 3693, lc 11826)
round trip expansion[compressionLut[lc[c]]]==lc[c]: failures 0; stored code != sensor code (excluding duplicate entries): 0
distinct table values 3889 of 4096 (codes 0..200 all map to 3200)

== (3) sensor forward curve (driver defaults) decoded with Core table ==
(error in 16-bit code values of Core's output domain: ideal = 3200 + L*0.987889)
b=1 T1=500.0000: Lmax 63085; max abs err -63.2 codes at L=1715 (code 718); worst ratio 0.8864 (-0.174 EV) at L=563
b=1 T1=500.3389: Lmax 63080; max abs err -42.5 codes at L=1694 (code 718); worst ratio 0.9207 (-0.119 EV) at L=542
b=4 T1=500.0000: Lmax 62512; max abs err -7610.7 codes at L=8203 (code 700); worst ratio 0.0577 (-4.114 EV) at L=2875
b=4 T1=500.9431: Lmax 62508; max abs err -7606.7 codes at L=8199 (code 700); worst ratio 0.0579 (-4.111 EV) at L=2887
binned (b=4) spot values, Core decode vs true linear (16-bit, Core domain):
  code  300  true L    100.0  ideal   3298.8  Core  3298  ratio(above black) 0.992
  code  325  true L    125.0  ideal   3323.5  Core  3323  ratio(above black) 0.996
  code  340  true L   1070.1  ideal   4257.2  Core  3338  ratio(above black) 0.131
  code  368  true L   2862.1  ideal   6027.5  Core  3365  ratio(above black) 0.058
  code  400  true L   3383.8  ideal   6542.8  Core  3397  ratio(above black) 0.059
  code  500  true L   4983.8  ideal   8123.4  Core  3496  ratio(above black) 0.060
  code  700  true L   8183.8  ideal  11284.7  Core  3693  ratio(above black) 0.061
  code  872  true L  10935.8  ideal  14003.3  Core 14576  ratio(above black) 1.053
  code 1500  true L  20983.8  ideal  23929.7  Core 24502  ratio(above black) 1.028
  code 3000  true L  44983.8  ideal  47639.0  Core 48212  ratio(above black) 1.013
  code 4095  true L  62503.8  ideal  64946.8  Core 65520  ratio(above black) 1.009

== Core table vs Cinemate golden tables (cinepi-raw@63a08d5 resources/ccmp_luts) ==
ccmp_decode_mode3_fullres.txt: white 63265, golden[200]=200 [700]=700 [872]=11687 [4095]=63265; max |Core-golden| 28.5 L at code 872; worst ratio 0.9490 (-0.076 EV) at code 216
ccmp_decode_mode2_binned.txt: white 62704, golden[200]=200 [700]=8384 [872]=11136 [4095]=62704; max |Core-golden| -7685.0 L at code 700; worst ratio 0.0582 (-4.103 EV) at code 369

== (4) DNG reader: lin = LUT[stored]; out = (lin - BlackLevel)/(WhiteLevel - BlackLevel) ==
tags: BitsPerSample 12, LinearizationTable 4096 SHORT, BlackLevel 3200 (float 3200.0), WhiteLevel 65520
black  code 200 -> lin 3200 -> 0.000000
noise  code 190 -> lin 3200 -> 0.000000 (sub-black clipped to 0 by the table itself)
grey   L=11355 (18% of sensor max) -> code 869 -> lin 14378 -> 0.179365
clip   code 4095 -> lin 65520 -> 1.000000
16-bit mode for comparison: BlackLevel 3201 WhiteLevel 65535; grey -> 0.182150; ratio 12/16 = 0.98471 (-0.0222 EV)
if the unwrap did not run (Core sees code<<4):
  sensor code  200 -> stored    0 -> 0.00000 (correct 0.00000)
  sensor code  300 -> stored  718 -> 0.02617 (correct 0.00157)
  sensor code  500 -> stored  769 -> 0.07792 (correct 0.00475)
  sensor code  700 -> stored  819 -> 0.12864 (correct 0.00791)
  sensor code  869 -> stored  862 -> 0.17227 (correct 0.17936)
  sensor code 1500 -> stored 1469 -> 0.33395 (correct 0.34182)
  sensor code 2500 -> stored 2481 -> 0.59063 (correct 0.59546)
  sensor code 4095 -> stored 4095 -> 1.00000 (correct 1.00000)

== (5) CineMate Log composed (cdngLogBits=12 when cdngLog==Auto) ==
CineMate Log 16->12 mu=10000 black=3200 white=65520 footroom=32/487
forward 4096, inverse 4096, inverse[0]=2721 [31]=3192 [32]=3200 [4095]=65520
tags: BlackLevel 3200 WhiteLevel 65520 (blackLevelForSampleBits clamps to <= 4094 on 12 bits: 3200.0)
black code 200 -> log 32 -> 0.000000; grey code 869 -> log 3337 -> 0.179284 (linear path 0.179365); clip 4095 -> log 4095 -> 1.000000
composed round trip vs linear table: max err -69 codes at CCMP code 4011 (lin 64192); worst ratio 1.0022 at code 665; forward monotone yes; distinct log codes used 1413 of 4096; footroom codes 0..31 used: no
```
