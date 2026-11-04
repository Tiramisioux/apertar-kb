// Scratch: VBLANK-only limit cycle vs gains/latency, and a Cinemate-like 11.11 us line case.
#include "FramePhaseLock.hpp"
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <random>
#include <vector>
static double quantised(int64_t reqUs, double qUs, bool evenRound, double lineUs)
{
    // frame length = floor(req / line); optional VMAX &= ~1; quantum = line (or 2 lines)
    long fl = static_cast<long>(std::floor(static_cast<double>(reqUs) / lineUs + 1e-9));
    if (evenRound) fl &= ~1L;
    (void)qUs;
    return fl * lineUs;
}
static void run(const char *label, double lineUs, bool evenRound, double ppmSlow, int L, double jit,
                double kp, double ki, double db)
{
    apertar::FramePhaseLock lock; lock.tuning.proportional = kp; lock.tuning.integral = ki; lock.tuning.deadbandUs = db;
    std::mt19937_64 rng(5); std::normal_distribution<double> n(0, 1);
    std::vector<int64_t> pins; int64_t pin = 40000; double t = 0; std::vector<double> err; uint64_t pushes = 0;
    std::vector<int64_t> lines; const size_t N = 40000, settle = 8000; std::vector<int64_t> distinct;
    for (size_t j = 0; j < N; ++j) {
        int64_t applied = j >= (size_t)L ? pins[j - L] : 40000;
        double per = quantised(applied, 0, evenRound, lineUs) * (1 + ppmSlow * 1e-6);
        t += per;
        double obs = t + (jit > 0 ? jit * n(rng) : 0);
        auto d = lock.step(true, true, 25.0, (int64_t)std::llround(obs * 1000));
        if (d.rearmed) pin = 40000;
        if (d.pushDuration) { pin = d.durationUs; if (j > settle) ++pushes; }
        pins.push_back(pin);
        if (j > settle && d.servoRan) { err.push_back(std::fabs(d.phaseErrorUs)); distinct.push_back((int64_t)std::llround(per)); }
    }
    std::sort(err.begin(), err.end()); std::sort(distinct.begin(), distinct.end());
    distinct.erase(std::unique(distinct.begin(), distinct.end()), distinct.end());
    std::printf("%-40s kp %.3f ki %.5f db %4.1f L %2d: max|err| %6.1f p99 %6.1f  push/100f %5.1f  distinct periods %zu\n",
                label, kp, ki, db, L, err.back(), err[(size_t)(0.99 * (err.size() - 1))], 100.0 * pushes / (N - settle), distinct.size());
}
int main()
{
    const double H = 550.0 / 74.25; // 7.4074 us
    std::printf("-- rig VBLANK-only (2H = 14.8 us steps), sensor +1.5 ppm slow, jitter 3 us\n");
    for (int L : { 6, 11 }) {
        run("rig vblank 2H", H, true, 1.5, L, 3, 0.06, 0.0015, 6);
        run("rig vblank 2H", H, true, 1.5, L, 3, 0.02, 0.0002, 6);
        run("rig vblank 2H", H, true, 1.5, L, 3, 0.01, 0.00005, 6);
        run("rig vblank 2H", H, true, 1.5, L, 3, 0.06, 0.0015, 15);
        run("rig vblank 2H", H, true, 1.5, L, 3, 0.02, 0.0002, 15);
    }
    std::printf("-- Cinemate-like: 11.11 us line, no even rounding, sensor ~1066 ppm fast, jitter 2 us\n");
    for (int L : { 1, 6, 10 }) run("cinemate-like 11.11us", 825.0 / 74.25, false, -1066, L, 2, 0.06, 0.0015, 6);
    return 0;
}
