// Scratch: steady-state phase error of a nearest-slot grid lock with and without dead-time compensation
// (predicted error = measured error + sum over requests in flight of (pin - nominal)).
#define main dual_main
#include "dual_model.cpp"
#undef main

static void run(bool lattice, double ppm, int D, bool comp, double jitter)
{
    Cam c(ppm, D, lattice, jitter, 1e12 + 0.3e6, 5);
    GridLock g; g.antiWindup = true;
    std::vector<double> errs; uint64_t pushes = 0;
    for (int i = 0; i < 30000; ++i) {
        const int64_t ts = c.frame();
        int64_t adj = 0;
        if (comp) for (int64_t p : c.pipe) adj += (p - 40000);          // us, requests already queued
        const auto o = g.step(ts + adj * 1000, 25.0);                     // feed the predicted arrival
        // the true (measured) error, for the statistics
        const int64_t rel = ts; const int64_t P = 40'000'000; const int64_t k = (rel + P / 2) / P;
        const double eTrue = (double)(rel - k * P) * 1e-3;
        if (o.push) { c.pin = o.dur; if (i >= 3000) ++pushes; }
        if (i >= 3000) errs.push_back(std::fabs(eTrue));
        c.queue();
        if (i == 3000) c.hmax.clear();
    }
    std::sort(errs.begin(), errs.end());
    std::printf("   %-7s %+6.1f %3d  %-4s jitter %.0f | max|e| %6.1f us  p99 %6.1f us  pushes/1000 %6.1f  HMAX values %zu\n",
                lattice ? "lattice" : "vblank", ppm, D, comp ? "comp" : "none", jitter, errs.back(), errs[size_t(errs.size() * 0.99)],
                pushes * 1000.0 / 27000.0, c.hmax.size());
}

int main()
{
    std::printf("E4 steady state, grid lock (anti-windup), 25 fps, frames 3000-30000\n");
    for (bool lat : { false, true })
        for (int D : { 7, 11 })
            for (bool comp : { false, true }) run(lat, -1.5, D, comp, 2.0);
    run(false, +42.0, 11, true, 2.0);
    run(false, -83.0, 11, true, 2.0);
    run(false, -1.5, 11, true, 10.0);
    return 0;
}
