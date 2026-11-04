// Scratch estimate (not part of any repo): Apertar's shipped FramePhaseLock (31d5418) driving an
// IMX585 4K model at 25 fps with a pipeline latency, two actuators, and two sensors.
#include "FramePhaseLock.hpp"
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <random>
#include <vector>

namespace {
constexpr double kClock = 74250000.0;   // IMX585 INCK ticks per second (driver IMX585_PIXEL_RATE)
constexpr long kMinH = 550;             // HMAX at 891 MHz link, 4K (driver HMAX table / Clear HDR floor)
constexpr long kCapH = kMinH + kMinH / 2;
constexpr long kHeight = 2200;          // Clear HDR 16-bit stream height (readback: VMAX 5400 = 2200 + 3200)

struct Realised { double periodUs; long h; long v; };

// Default CamHelper::getBlanking (frame length = floor(d / line), HMAX at minimum) + driver VMAX &= ~1.
Realised vblankOnly(int64_t reqUs)
{
    long fl = static_cast<long>((reqUs * 7425LL) / (kMinH * 100LL)); // floor(reqUs*74.25/550)
    long v = fl & ~1L;
    return { v * kMinH / kClock * 1e6, kMinH, v };
}

// qbc cam_helper_imx585.cpp getBlanking (4cff971) for a pinned {d,d}.
Realised lattice(int64_t reqUs)
{
    long defV = static_cast<long>((reqUs * 7425LL) / (kMinH * 100LL));
    long long target = std::llround(static_cast<double>(reqUs) * 74.25);
    const double reqD = static_cast<double>(reqUs);
    const long nominalFps = std::lround(kClock / static_cast<double>(target));
    if (nominalFps > 0 && std::fabs(1.0e6 / nominalFps - reqD) < 1.0) {
        const double exact = kClock / static_cast<double>(nominalFps);
        const long long exactTicks = std::llround(exact);
        if (exact == std::floor(exact) && (exactTicks & 1LL) == 0) target = exactTicks;
    }
    long bestH = kMinH;
    long long bestV = defV & ~1LL;
    long long bestErr = std::llabs(bestV * bestH - target);
    const long long halfUs = std::llround(kClock / 2.0e6);
    long lowH = -1; long long lowV = 0;
    for (long h = kMinH; h <= kCapH && bestErr; ++h) {
        long long vIdeal = (target + h / 2) / h;
        long long vEven = vIdeal & ~1LL;
        for (long long v : { vEven, vEven + 2 }) {
            if (v < 4500 || v > 0xfffff) continue;
            long long err = std::llabs(v * h - target);
            if (err < bestErr) { bestErr = err; bestV = v; bestH = h; }
            if (lowH < 0 && err <= halfUs) { lowH = h; lowV = v; }
        }
    }
    if (bestErr != 0 && lowH >= 0 && lowH < bestH) { bestH = lowH; bestV = lowV; }
    return { static_cast<double>(bestV * bestH) / kClock * 1e6, bestH, static_cast<long>(bestV) };
}

struct Cam {
    bool useLattice;
    double ppmSlow;      // + = sensor crystal slow vs the reference (longer periods)
    int latency;         // frames from a pin change to the first frame realised with it
    double jitterUs;     // timestamp jitter sigma
    bool locked;
    apertar::FramePhaseLock lock;
    std::vector<int64_t> pinHist; // pin in force for requests queued at frame j
    int64_t pin = 40000;
    double tUs = 0.0;
    long lastH = -1;
    uint64_t hmaxChanges = 0, pushes = 0;
    std::mt19937_64 rng;
    std::normal_distribution<double> n{0.0, 1.0};
    Cam(bool lat, double ppm, int L, double jit, bool lk, unsigned seed)
        : useLattice(lat), ppmSlow(ppm), latency(L), jitterUs(jit), locked(lk), rng(seed) {}
    // Advance one frame; returns the observed timestamp (us).
    double frame(size_t j)
    {
        int64_t applied = (j >= static_cast<size_t>(latency)) ? pinHist[j - latency] : 40000;
        Realised r = useLattice ? lattice(applied) : vblankOnly(applied);
        if (lastH >= 0 && r.h != lastH) ++hmaxChanges;
        lastH = r.h;
        tUs += r.periodUs * (1.0 + ppmSlow * 1e-6);
        return tUs + (jitterUs > 0 ? jitterUs * n(rng) : 0.0);
    }
    // Servo on the observed timestamp against its own datum (absolute grid if both start aligned).
    double servo(double obsUs)
    {
        auto d = lock.step(locked, true, 25.0, static_cast<int64_t>(std::llround(obsUs * 1000.0)));
        if (d.rearmed) pin = 40000;
        if (d.pushDuration) { pin = d.durationUs; ++pushes; }
        pinHist.push_back(pin);
        return d.servoRan ? d.phaseErrorUs : 0.0;
    }
};

struct Stat { double maxAbs = 0, p99 = 0, rms = 0; };
Stat stats(std::vector<double> v)
{
    Stat s; if (v.empty()) return s;
    for (double &x : v) { s.maxAbs = std::max(s.maxAbs, std::fabs(x)); s.rms += x * x; x = std::fabs(x); }
    s.rms = std::sqrt(s.rms / v.size());
    std::sort(v.begin(), v.end());
    s.p99 = v[static_cast<size_t>(0.99 * (v.size() - 1))];
    return s;
}

void single(const char *label, bool lat, double ppm, int L, double jit)
{
    const size_t N = 30000, settle = 5000;
    Cam c(lat, ppm, L, jit, true, 7);
    std::vector<double> err;
    double t0 = 0; uint64_t p0 = 0, h0 = 0;
    for (size_t j = 0; j < N; ++j) {
        double obs = c.frame(j);
        double e = c.servo(obs);
        if (j == settle) { t0 = c.tUs; p0 = c.pushes; h0 = c.hmaxChanges; }
        if (j > settle) err.push_back(e);
    }
    Stat s = stats(err);
    double frames = static_cast<double>(N - 1 - settle);
    double meanPpm = ((c.tUs - t0) / (frames * 40000.0) - 1.0) * 1e6;
    std::printf("%-44s max|err| %6.1f us  p99 %6.1f  rms %5.1f  push/100f %5.1f  HMAXchg/100f %5.1f  mean %+7.2f ppm\n",
                label, s.maxAbs, s.p99, s.rms, 100.0 * (c.pushes - p0) / frames,
                100.0 * (c.hmaxChanges - h0) / frames, meanPpm);
}

// Two sensors that start on the same grid instant (shared datum), each locked to the reference.
void pairGrid(const char *label, bool lat, double ppmA, double ppmB, int L, double jit)
{
    const size_t N = 30000, settle = 5000;
    Cam a(lat, ppmA, L, jit, true, 11), b(lat, ppmB, L, jit, true, 23);
    std::vector<double> rel;
    for (size_t j = 0; j < N; ++j) {
        double oa = a.frame(j), ob = b.frame(j);
        a.servo(oa); b.servo(ob);
        if (j > settle) rel.push_back(b.tUs - a.tUs);
    }
    Stat s = stats(rel);
    std::printf("%-44s |tB-tA| max %6.1f us  p99 %6.1f  rms %5.1f\n", label, s.maxAbs, s.p99, s.rms);
}

// Follower: A free-runs on Core's pin; B servos on (tB - tA) (relative lock, like rpi.sync's client).
void pairFollow(const char *label, bool lat, double ppmA, double ppmB, int L, double jit)
{
    const size_t N = 30000, settle = 5000;
    Cam a(lat, ppmA, L, jit, false, 31), b(lat, ppmB, L, jit, true, 37);
    std::vector<double> rel;
    for (size_t j = 0; j < N; ++j) {
        double oa = a.frame(j), ob = b.frame(j);
        a.servo(oa);
        // B's reference: its own time minus A's deviation from A's ideal grid -> error = tB - tA.
        double refB = ob - (oa - 40000.0 * static_cast<double>(j + 1));
        b.servo(refB);
        if (j > settle) rel.push_back(b.tUs - a.tUs);
    }
    Stat s = stats(rel);
    std::printf("%-44s |tB-tA| max %6.1f us  p99 %6.1f  rms %5.1f  B push/100f %5.1f  B HMAXchg/100f %5.1f  A HMAXchg %llu\n",
                label, s.maxAbs, s.p99, s.rms, 100.0 * b.pushes / N, 100.0 * b.hmaxChanges / N,
                static_cast<unsigned long long>(a.hmaxChanges));
}
} // namespace

int main()
{
    std::printf("lattice check: 40000->%ldx%ld %.3f  40001->%ldx%ld %.3f  40016->%ldx%ld %.3f  39999->%ldx%ld %.3f\n",
                lattice(40000).h, lattice(40000).v, lattice(40000).periodUs, lattice(40001).h, lattice(40001).v,
                lattice(40001).periodUs, lattice(40016).h, lattice(40016).v, lattice(40016).periodUs,
                lattice(39999).h, lattice(39999).v, lattice(39999).periodUs);
    std::printf("vblank-only steps: 39999->%.3f 40000->%.3f 40014->%.3f 40015->%.3f\n", vblankOnly(39999).periodUs,
                vblankOnly(40000).periodUs, vblankOnly(40014).periodUs, vblankOnly(40015).periodUs);
    std::printf("\n-- validation vs the T27 preview run (sensor appears ~+45 ppm fast vs slewed BOOTTIME)\n");
    for (int L : { 1, 6, 11 }) {
        char buf[96]; std::snprintf(buf, sizeof buf, "lattice  -45ppm L=%d jit=2", L);
        single(buf, true, -45.0, L, 2.0);
    }
    std::printf("\n-- one sensor at -1.5 ppm vs an unslewed reference (the measured offset; sign: slow)\n");
    for (bool lat : { true, false })
        for (int L : { 1, 6, 11 })
            for (double jit : { 0.0, 3.0 }) {
                char buf[96]; std::snprintf(buf, sizeof buf, "%s +1.5slow L=%d jit=%.0f", lat ? "lattice " : "vblank14.8", L, jit);
                single(buf, lat, 1.5, L, jit);
            }
    std::printf("\n-- one sensor with a larger offset (unknown second sensor), L=11 jit=3\n");
    for (bool lat : { true, false })
        for (double ppm : { -10.0, 30.0, -50.0 }) {
            char buf[96]; std::snprintf(buf, sizeof buf, "%s %+.0fppm L=11 jit=3", lat ? "lattice " : "vblank14.8", ppm);
            single(buf, lat, ppm, 11, 3.0);
        }
    std::printf("\n-- two locked sensors on one shared grid datum, L=11 jit=3\n");
    for (bool lat : { true, false })
        for (double ppmB : { -1.5, 10.0, -30.0 }) {
            char buf[96]; std::snprintf(buf, sizeof buf, "%s A+1.5 B%+.0f grid", lat ? "lattice " : "vblank14.8", ppmB);
            pairGrid(buf, lat, 1.5, ppmB, 11, 3.0);
        }
    std::printf("\n-- follower: A free (Core pin), B servos on tB-tA, L=11 jit=3\n");
    for (bool lat : { true, false })
        for (double ppmB : { -1.5, 10.0, -30.0 }) {
            char buf[96]; std::snprintf(buf, sizeof buf, "%s A+1.5 B%+.0f follow", lat ? "lattice " : "vblank14.8", ppmB);
            pairFollow(buf, lat, 1.5, ppmB, 11, 3.0);
        }
    return 0;
}
