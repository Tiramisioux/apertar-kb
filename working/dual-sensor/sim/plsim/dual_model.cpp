// Scratch model (not a repo file): the shipped FramePhaseLock (copied from
// Apertar-Core drop-frames 31d5418) plus a nearest-slot "grid" variant, run
// with a control delay D (requests in flight), a VBLANK-only or qbc-lattice
// realisation, per-sensor crystal error and timestamp jitter.
#include "FramePhaseLock.hpp"

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <deque>
#include <map>
#include <random>
#include <set>
#include <vector>

using apertar::FramePhaseLock;

constexpr double kClock = 74250000.0;
constexpr long kHmin = 550;               // 4K Clear HDR 25 fps: HMAX 550 x VMAX 5400 (hardware log)

// default CamHelper::getBlanking: frameLength = floor(d / minLine); driver: VMAX & ~1
double vblankRealised(int64_t reqUs, long &h)
{
    h = kHmin;
    const long double ticks = (long double)reqUs * 1e-6L * kClock;
    long long lines = (long long)std::floor(ticks / kHmin + 1e-9L);
    lines &= ~1LL;
    return (double)(lines * (long double)kHmin / kClock * 1e6L);
}

// qbc getBlanking lattice (same logic as apertar-kb working/tools/phase_lock_sim.cpp LatticeSensor)
double latticeRealised(int64_t request, long &hOut)
{
    const long minHmax = 550, capHmax = 825;
    const long long minFrameLength = 2200, maxFrameLength = (1LL << 20) - 1;
    long long target = std::llround((double)request * 1e-6 * kClock);
    const long nominalFps = std::lround(kClock / (double)target);
    if (nominalFps > 0 && std::fabs(1.0e6 / nominalFps - (double)request) < 1.0) {
        const double exact = kClock / (double)nominalFps;
        const long long exactTicks = std::llround(exact);
        if (exact == std::floor(exact) && (exactTicks & 1LL) == 0) target = exactTicks;
    }
    long bestH = minHmax;
    long long bestV = (target / minHmax) & ~1LL;
    long long bestErr = std::llabs(bestV * bestH - target);
    const long long halfUs = std::llround(kClock / 2.0e6);
    long lowH = -1; long long lowV = 0;
    for (long h = minHmax; h <= capHmax && bestErr; ++h) {
        const long long vIdeal = (target + h / 2) / h;
        const long long vEven = vIdeal & ~1LL;
        for (long long v : { vEven, vEven + 2 }) {
            if (v < minFrameLength || v > maxFrameLength) continue;
            const long long err = std::llabs(v * h - target);
            if (err < bestErr) { bestErr = err; bestV = v; bestH = h; }
            if (lowH < 0 && err <= halfUs) { lowH = h; lowV = v; }
        }
    }
    if (bestErr != 0 && lowH >= 0 && lowH < bestH) { bestH = lowH; bestV = lowV; }
    hOut = bestH;
    return (double)bestV * (double)bestH / kClock * 1e6;
}

// Same law as FramePhaseLock::step(), error to the nearest slot of an absolute grid.
struct GridLock {
    FramePhaseLock::Tuning t{};
    bool antiWindup = false;
    bool active = false;
    double nominalUs = 0, requestedUs = 0, integralUs = 0;
    int64_t lastPushedUs = -1, originNs = 0, periodNs = 40'000'000;
    uint64_t pushes = 0;
    struct Out { bool servo = false, push = false; int64_t dur = 0; double err = 0; };
    Out step(int64_t ts, double fps)
    {
        Out o;
        if (!active) {
            nominalUs = 1e6 / fps; requestedUs = nominalUs; integralUs = 0; lastPushedUs = -1; active = true;
            periodNs = std::llround(1e9 / fps);
            return o;
        }
        const int64_t rel = ts - originNs;
        const int64_t k = (rel + periodNs / 2) / periodNs;
        const double e = (double)(rel - k * periodNs) * 1e-3;
        if (std::fabs(e) > t.deadbandUs) {
            const double windup = t.clampUs / std::max(t.integral, 1e-9);
            const double candidateI = std::clamp(integralUs + e, -windup, windup);
            double req = nominalUs - (t.proportional * e + t.integral * candidateI);
            const bool sat = req < nominalUs - t.clampUs || req > nominalUs + t.clampUs;
            if (!antiWindup || !sat) integralUs = candidateI;
            req = nominalUs - (t.proportional * e + t.integral * integralUs);
            requestedUs = std::clamp(req, nominalUs - t.clampUs, nominalUs + t.clampUs);
        }
        o.servo = true; o.err = e; o.dur = std::llround(requestedUs);
        if (o.dur != lastPushedUs) { lastPushedUs = o.dur; ++pushes; o.push = true; }
        return o;
    }
};

struct Cam {
    double ppm;          // + = sensor fast
    int D;               // frames from decision to the first frame realised with it
    bool lattice;
    double jitterUs;
    double tTrueNs;
    std::deque<int64_t> pipe;
    int64_t pin;
    std::mt19937_64 rng;
    std::set<long> hmax;
    Cam(double p, int d, bool lat, double j, double t0, uint64_t seed)
        : ppm(p), D(d), lattice(lat), jitterUs(j), tTrueNs(t0), pin(40000), rng(seed)
    { for (int i = 0; i < D; ++i) pipe.push_back(40000); }
    // advance one frame with the request that reaches the sensor now; returns the measured timestamp
    int64_t frame()
    {
        const int64_t applied = pipe.front(); pipe.pop_front();
        long h = 0;
        const double r = lattice ? latticeRealised(applied, h) : vblankRealised(applied, h);
        hmax.insert(h);
        tTrueNs += r * 1000.0 * (1.0 - ppm * 1e-6);
        std::normal_distribution<double> n(0.0, jitterUs * 1000.0);
        const double j = jitterUs > 0 ? std::fabs(n(rng)) : 0.0;  // ISR latency only delays
        return (int64_t)std::llround(tTrueNs + j);
    }
    void queue() { pipe.push_back(pin); }
};

static void shippedLockTable()
{
    std::printf("E1 shipped FramePhaseLock (arm-anchored), 25 fps, 30000 frames, stats over frames 3000+\n");
    std::printf("   model    ppm     D  jitter | max|err| us  p99|err| us  pushes/1000fr  distinct HMAX\n");
    for (bool lat : { false, true })
        for (double ppm : { -1.5, +42.0, -83.0 })
            for (int D : { 1, 7, 11 }) {
                Cam c(ppm, D, lat, 2.0, 1e12, 7);
                FramePhaseLock lock;
                std::vector<double> errs; uint64_t pushes = 0;
                for (int i = 0; i < 30000; ++i) {
                    const int64_t ts = c.frame();
                    const auto d = lock.step(true, i > 500, 25.0, ts);
                    if (d.pushDuration) { c.pin = d.durationUs; if (i >= 3000) ++pushes; }
                    if (i >= 3000 && d.servoRan) errs.push_back(std::fabs(d.phaseErrorUs));
                    c.queue();
                    if (i == 3000) c.hmax.clear();
                }
                std::sort(errs.begin(), errs.end());
                std::printf("   %-7s %+6.1f %3d   2us   | %10.1f  %10.1f  %12.1f  %8zu\n", lat ? "lattice" : "vblank", ppm, D,
                            errs.back(), errs[size_t(errs.size() * 0.99)], pushes * 1000.0 / 27000.0, c.hmax.size());
            }
}

static void pullIn()
{
    std::printf("E2 grid lock pull-in from an initial phase offset, VBLANK model, ppm -1.5, jitter 2 us, 25 fps\n");
    std::printf("   offset ms  D  antiwindup | frames to |e|<50us for good  peak overshoot us  max dur dev us\n");
    for (double off : { +19.0, -19.0, +5.0 })
        for (int D : { 7, 11 })
            for (bool aw : { false, true }) {
                // t0 chosen so the first frame sits `off` ms after its grid slot
                Cam c(-1.5, D, false, 2.0, 1e12 + off * 1e6, 11);
                GridLock g; g.antiWindup = aw; g.originNs = 0;
                int lastBad = -1; double overshoot = 0; bool crossed = false; double firstSign = 0; double maxDev = 0;
                for (int i = 0; i < 6000; ++i) {
                    const int64_t ts = c.frame();
                    const auto o = g.step(ts, 25.0);
                    if (o.push) c.pin = o.dur;
                    maxDev = std::max(maxDev, std::fabs((double)c.pin - 40000.0));
                    if (o.servo) {
                        if (firstSign == 0) firstSign = (o.err > 0) ? 1 : -1;
                        if (!crossed && o.err * firstSign < 0) crossed = true;
                        if (crossed) overshoot = std::max(overshoot, -o.err * firstSign);
                        if (std::fabs(o.err) > 50.0) lastBad = i;
                    }
                    c.queue();
                }
                std::printf("   %+6.1f   %3d   %-5s     | %8d (%.1f s)            %10.0f          %6.0f\n", off, D, aw ? "yes" : "no",
                            lastBad + 1, (lastBad + 1) / 25.0, overshoot, maxDev);
            }
}

static void dualSkew()
{
    std::printf("E3 two sensors, both grid-locked to origin 0 on the shared clock, VBLANK model, jitter 2 us each\n");
    std::printf("   A ppm/D      B ppm/D      | true skew |tA-tB| over frames 5000-30000: max us  p99 us   (shipped lock: constant skew)\n");
    struct Case { double pa; int da; double pb; int db; };
    for (const Case cs : { Case{-1.5, 11, +20.0, 11}, Case{-1.5, 11, -50.0, 7}, Case{+30.0, 11, -30.0, 11} }) {
        Cam a(cs.pa, cs.da, false, 2.0, 1e12 + 3.1e6, 21), b(cs.pb, cs.db, false, 2.0, 1e12 + 27.9e6, 22);
        GridLock ga, gb; ga.antiWindup = gb.antiWindup = true;
        std::vector<double> skew;
        std::map<int64_t, double> bySlotB;
        const int64_t P = 40'000'000;
        int unmatched = 0;
        for (int i = 0; i < 30000; ++i) {
            const int64_t ta = a.frame(), tb = b.frame();
            const auto oa = ga.step(ta, 25.0), ob = gb.step(tb, 25.0);
            if (oa.push) a.pin = oa.dur;
            if (ob.push) b.pin = ob.dur;
            a.queue(); b.queue();
            if (i >= 5000) {
                // compare true frame starts of the same grid slot
                bySlotB[((int64_t)b.tTrueNs + P / 2) / P] = b.tTrueNs;
                const int64_t ka = ((int64_t)a.tTrueNs + P / 2) / P;
                if (auto it = bySlotB.find(ka); it != bySlotB.end()) skew.push_back(std::fabs(a.tTrueNs - it->second) * 1e-3);
                else ++unmatched;
                while (bySlotB.size() > 8) bySlotB.erase(bySlotB.begin());
            }
        }
        if (unmatched > 2) std::printf("   (unmatched slots: %d)\n", unmatched);
        std::sort(skew.begin(), skew.end());
        std::printf("   %+6.1f/%-3d    %+6.1f/%-3d    |            %8.1f  %7.1f\n", cs.pa, cs.da, cs.pb, cs.db, skew.back(),
                    skew[size_t(skew.size() * 0.99)]);
    }
}

int main()
{
    shippedLockTable();
    pullIn();
    dualSkew();
    return 0;
}
