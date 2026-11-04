#include <initializer_list>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstdint>
constexpr double kClock = 74250000.0; constexpr long kMinH = 550, kCapH = 825;
struct R { double us; long h; long long v; };
R lattice(int64_t reqUs, long long minV) {
    long defV = (long)((reqUs * 7425LL) / (kMinH * 100LL));
    long long target = std::llround((double)reqUs * 74.25);
    const long nominalFps = std::lround(kClock / (double)target);
    if (nominalFps > 0 && std::fabs(1.0e6 / nominalFps - (double)reqUs) < 1.0) {
        const double exact = kClock / (double)nominalFps; const long long et = std::llround(exact);
        if (exact == std::floor(exact) && (et & 1LL) == 0) target = et;
    }
    long bestH = kMinH; long long bestV = defV & ~1LL; long long bestErr = std::llabs(bestV * bestH - target);
    const long long halfUs = std::llround(kClock / 2.0e6); long lowH = -1; long long lowV = 0;
    for (long h = kMinH; h <= kCapH && bestErr; ++h) {
        long long vI = (target + h / 2) / h, vE = vI & ~1LL;
        for (long long v : { vE, vE + 2 }) { if (v < minV) continue; long long e = std::llabs(v * h - target);
            if (e < bestErr) { bestErr = e; bestV = v; bestH = h; } if (lowH < 0 && e <= halfUs) { lowH = h; lowV = v; } }
    }
    if (bestErr != 0 && lowH >= 0 && lowH < bestH) { bestH = lowH; bestV = lowV; }
    return { (double)(bestV * bestH) / kClock * 1e6, bestH, bestV };
}
int main() {
    for (double fps : { 24.0, 25.0, 30.0, 33.0, 50.0 }) {
        int64_t pin = (int64_t)(1000000.0 / fps); long long minV = fps > 30.5 ? 2250 : 4500;
        R l = lattice(pin, minV);
        long fl = (long)((pin * 7425LL) / (kMinH * 100LL)) & ~1L; double vb = fl * kMinH / kClock * 1e6;
        double ideal = 1e6 / fps;
        std::printf("fps %4.1f pin %lld: lattice HMAX %ld VMAX %lld = %.3f us (%+.1f ppm, H %.3f us); default helper VMAX %ld = %.3f us (%+.1f ppm period)\n",
            fps, (long long)pin, l.h, l.v, l.us, (l.us / ideal - 1) * 1e6, l.h / 74.25, fl, vb, (vb / ideal - 1) * 1e6);
    }
}
